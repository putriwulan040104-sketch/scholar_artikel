import networkx as nx
from app.db import supabase
from app.services.doi_lookup_service import load_doi_by_publication_id

PUBLICATIONS_TABLE = "cleaned_papers_results"
RELATIONS_TABLE = "article_relations"

def _load_publications():
    all_rows = []
    page_size = 500
    offset = 0

    while True:
        response = (
            supabase
            .table(PUBLICATIONS_TABLE)
            .select("id,title,year,authors,reference_list")
            .order("id", desc=False)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        batch = response.data or []
        if not batch:
            break

        all_rows.extend(batch)
        offset += page_size

        if len(batch) < page_size:
            break

    return all_rows

def _reference_count(reference_value):
    if reference_value is None:
        return 0

    if isinstance(reference_value, list):
        return sum(
            1 for item in reference_value
            if isinstance(item, str) and item.strip()
        )

    if isinstance(reference_value, str):
        val = reference_value.strip()
        if not val:
            return 0

        # string JSON array
        if val.startswith("[") and val.endswith("]"):
            try:
                import json
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return sum(
                        1 for item in parsed
                        if isinstance(item, str) and item.strip()
                    )
            except Exception:
                pass

        # fallback: multi-line string
        return sum(1 for line in val.splitlines() if line.strip())

    return 0

def _load_relations(relation_type="bibliographic_coupling"):
    try:
        response = (
            supabase
            .table(RELATIONS_TABLE)
            .select(
                "source_id,target_id,weight,relation_type,details"
            )
            .eq("relation_type", relation_type)
            .execute()
        )
    except Exception:
        response = (
            supabase
            .table(RELATIONS_TABLE)
            .select("source_id, target_id, relation_type")
            .eq("relation_type", relation_type)
            .execute()
        )
    return response.data or []

def _build_graph(publications, relations):
    node_ids = [int(p["id"]) for p in publications if p.get("id") is not None]
    node_set = set(node_ids)
    adjacency = {node_id: set() for node_id in node_ids}

    edge_weights = {}
    for row in relations:
        left_id = row.get("source_id")
        right_id = row.get("target_id")
        if left_id is None or right_id is None:
            continue

        c1 = int(left_id)
        c2 = int(right_id)
        if c1 not in node_set or c2 not in node_set:
            continue

        adjacency[c1].add(c2)
        adjacency[c2].add(c1)

        edge = (c1, c2)
        weight = int(row.get("weight") or 1)
        edge_weights[edge] = edge_weights.get(edge, 0) + weight

    edges = [(src, dst, wt) for (src, dst), wt in edge_weights.items()]

    return node_ids, edges, adjacency

def _weak_component_stats(node_ids, adjacency):
    visited = set()
    component_sizes = []

    for node_id in node_ids:
        if node_id in visited:
            continue

        stack = [node_id]
        visited.add(node_id)
        size = 0

        while stack:
            current = stack.pop()
            size += 1
            for nxt in adjacency[current]:
                if nxt in visited:
                    continue
                visited.add(nxt)
                stack.append(nxt)

        component_sizes.append(size)

    component_count = len(component_sizes)
    largest_component_size = max(component_sizes) if component_sizes else 0

    return component_count, largest_component_size

def build_sna_metrics(
    top_n=10,
    relation_type="bibliographic_coupling",
):
    publications = _load_publications()
    relations = _load_relations(relation_type)
    pub_map = {int(p["id"]): p for p in publications if p.get("id") is not None}
    doi_by_id = load_doi_by_publication_id(pub_map.keys())

    node_ids, edges, adjacency = _build_graph(
        publications,
        relations,
    )

    graph = nx.Graph()
    graph.add_nodes_from(node_ids)
    graph.add_edges_from((source, target) for source, target, _weight in edges)
    betweenness = nx.betweenness_centrality(graph)
    degree_centrality_map = nx.degree_centrality(graph)

    node_count = len(node_ids)
    edge_count = len(edges)
    total_edge_weight = sum(weight for _src, _dst, weight in edges)
    density = 0.0
    if node_count > 1:
        density = (2 * edge_count) / (node_count * (node_count - 1))

    isolated_nodes = sum(
        1 for node in graph.nodes if graph.degree(node) == 0
    )

    component_count, largest_component_size = _weak_component_stats(node_ids, adjacency)

    metrics_rows = []
    for node_id in node_ids:
        metrics_rows.append({
            "id": node_id,
            "title": pub_map[node_id].get("title"),
            "year": pub_map[node_id].get("year"),
            "doi": doi_by_id.get(node_id),
            "degree_centrality": round(float(degree_centrality_map.get(node_id, 0.0)), 8),
            "betweenness": round(float(betweenness.get(node_id, 0.0)), 8),
        })

    top_by_degree = sorted(
        metrics_rows,
        key=lambda x: (x["degree_centrality"], x["betweenness"]),
        reverse=True
    )[:top_n]

    top_by_betweenness = sorted(
        metrics_rows,
        key=lambda x: x["betweenness"],
        reverse=True
    )[:top_n]

    summary = {
        "node_count": node_count,
        "edge_count": edge_count,
        "density": round(float(density), 8),
        "total_edge_weight": total_edge_weight,
        "isolated_nodes": isolated_nodes,
        "component_count": component_count,
        "largest_component_size": largest_component_size,
        "average_degree": round(float(2 * edge_count / node_count), 8) if node_count else 0.0,
        "relation_type": relation_type,
    }

    return {
        "summary": summary,
        "top_degree_centrality": top_by_degree,
        "top_connected": top_by_degree,
        "top_betweenness": top_by_betweenness,
        "node_metrics": metrics_rows,
    }

def build_graph_payload(
    article_ids=None,
    relation_type="bibliographic_coupling",
):
    publications = _load_publications()
    citations = _load_relations(relation_type)
    requested_ids = set()
    if article_ids:
        for raw_id in article_ids:
            try:
                requested_ids.add(int(raw_id))
            except Exception:
                continue

    if requested_ids:
        filtered_publications = []
        for row in publications:
            pub_id = row.get("id")
            keep = False
            if pub_id is not None:
                try:
                    keep = int(pub_id) in requested_ids
                except Exception:
                    keep = False

            if keep:
                filtered_publications.append(row)

        publications = filtered_publications

    pub_map = {int(p["id"]): p for p in publications if p.get("id") is not None}
    doi_by_id = load_doi_by_publication_id(pub_map.keys())
    node_ids, edges, _adjacency = _build_graph(
        publications,
        citations,
    )

    graph = nx.Graph()
    graph.add_nodes_from(node_ids)
    graph.add_edges_from((source, target) for source, target, _weight in edges)

    degree_cent = nx.degree_centrality(graph)
    edge_betweenness = nx.edge_betweenness_centrality(graph)

    nodes = []
    for node_id in node_ids:
        data = pub_map[node_id]
        nodes.append({
            "id": node_id,
            "article_id": node_id,
            "title": data.get("title"),
            "year": data.get("year"),
            "doi": doi_by_id.get(node_id),
            "authors": data.get("authors"),
            "reference_count": _reference_count(data.get("reference_list")),
            "degree_centrality": round(float(degree_cent.get(node_id, 0.0)), 8),
        })

    edge_payload = []
    relation_details = {
        (int(row["source_id"]), int(row["target_id"])): (
            row.get("details") or {}
        )
        for row in citations
        if row.get("source_id") is not None
        and row.get("target_id") is not None
    }
    for c1, c2, weight in edges:
        edge_betweenness_val = edge_betweenness.get(
            (c1, c2),
            edge_betweenness.get((c2, c1), 0.0),
        )
        edge_payload.append({
            "source": c1,
            "target": c2,
            "weight": weight,
            "edge_betweenness": round(float(edge_betweenness_val), 8),
            "relation_type": relation_type,
            "details": relation_details.get((c1, c2), {}),
        })

    return {
        "nodes": nodes,
        "edges": edge_payload,
        "relation_type": relation_type,
    }
