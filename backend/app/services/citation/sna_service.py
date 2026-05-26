from app.db import supabase

PUBLICATIONS_TABLE = "publications"
CITATIONS_TABLE = "citations"

def _load_publications():
    all_rows = []
    page_size = 500
    offset = 0

    while True:
        response = (
            supabase
            .table(PUBLICATIONS_TABLE)
            .select("id, title, year, doi")
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


def _load_citations():
    try:
        response = (
            supabase
            .table(CITATIONS_TABLE)
            .select("citing_id, cited_id, weight")
            .execute()
        )
    except Exception:
        response = (
            supabase
            .table(CITATIONS_TABLE)
            .select("citing_id, cited_id")
            .execute()
        )
    return response.data or []


def _build_graph(publications, citations):
    node_ids = [int(p["id"]) for p in publications if p.get("id") is not None]
    node_set = set(node_ids)
    out_adj = {node_id: set() for node_id in node_ids}
    in_adj = {node_id: set() for node_id in node_ids}

    edge_weights = {}
    for row in citations:
        citing_id = row.get("citing_id")
        cited_id = row.get("cited_id")
        if citing_id is None or cited_id is None:
            continue

        c1 = int(citing_id)
        c2 = int(cited_id)
        if c1 not in node_set or c2 not in node_set:
            continue

        out_adj[c1].add(c2)
        in_adj[c2].add(c1)

        edge = (c1, c2)
        weight = int(row.get("weight") or 1)
        edge_weights[edge] = edge_weights.get(edge, 0) + weight

    edges = [(src, dst, wt) for (src, dst), wt in edge_weights.items()]

    return node_ids, edges, out_adj, in_adj


def _compute_pagerank(node_ids, out_adj, damping=0.85, max_iter=50, tol=1e-6):
    n = len(node_ids)
    if n == 0:
        return {}

    base = (1.0 - damping) / n
    ranks = {node_id: 1.0 / n for node_id in node_ids}

    for _ in range(max_iter):
        sink_sum = sum(ranks[node_id] for node_id in node_ids if len(out_adj[node_id]) == 0)
        next_ranks = {node_id: base + damping * sink_sum / n for node_id in node_ids}

        for src in node_ids:
            out_neighbors = out_adj[src]
            if not out_neighbors:
                continue
            share = damping * ranks[src] / len(out_neighbors)
            for dst in out_neighbors:
                next_ranks[dst] += share

        delta = sum(abs(next_ranks[node_id] - ranks[node_id]) for node_id in node_ids)
        ranks = next_ranks
        if delta < tol:
            break

    return ranks


def _weak_component_stats(node_ids, out_adj, in_adj):
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
            neighbors = out_adj[current] | in_adj[current]
            for nxt in neighbors:
                if nxt in visited:
                    continue
                visited.add(nxt)
                stack.append(nxt)

        component_sizes.append(size)

    component_count = len(component_sizes)
    largest_component_size = max(component_sizes) if component_sizes else 0

    return component_count, largest_component_size


def build_sna_metrics(top_n=10):
    publications = _load_publications()
    citations = _load_citations()
    pub_map = {int(p["id"]): p for p in publications if p.get("id") is not None}

    node_ids, edges, out_adj, in_adj = _build_graph(publications, citations)
    pagerank = _compute_pagerank(node_ids, out_adj)

    node_count = len(node_ids)
    edge_count = len(edges)
    total_edge_weight = sum(weight for _src, _dst, weight in edges)
    density = 0.0
    if node_count > 1:
        density = edge_count / (node_count * (node_count - 1))

    isolated_nodes = sum(
        1 for node_id in node_ids
        if len(out_adj[node_id]) == 0 and len(in_adj[node_id]) == 0
    )

    component_count, largest_component_size = _weak_component_stats(node_ids, out_adj, in_adj)

    metrics_rows = []
    for node_id in node_ids:
        metrics_rows.append({
            "id": node_id,
            "title": pub_map[node_id].get("title"),
            "year": pub_map[node_id].get("year"),
            "doi": pub_map[node_id].get("doi"),
            "in_degree": len(in_adj[node_id]),
            "out_degree": len(out_adj[node_id]),
            "pagerank": round(float(pagerank.get(node_id, 0.0)), 8),
        })

    top_by_in_degree = sorted(
        metrics_rows,
        key=lambda x: (x["in_degree"], x["pagerank"]),
        reverse=True
    )[:top_n]

    top_by_pagerank = sorted(
        metrics_rows,
        key=lambda x: x["pagerank"],
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
        "average_in_degree": round(float(edge_count / node_count), 8) if node_count else 0.0,
        "average_out_degree": round(float(edge_count / node_count), 8) if node_count else 0.0,
    }

    return {
        "summary": summary,
        "top_cited": top_by_in_degree,
        "top_pagerank": top_by_pagerank,
        "node_metrics": metrics_rows,
    }


def build_graph_payload():
    publications = _load_publications()
    citations = _load_citations()
    pub_map = {int(p["id"]): p for p in publications if p.get("id") is not None}
    node_ids, edges, _out_adj, _in_adj = _build_graph(publications, citations)

    nodes = []
    for node_id in node_ids:
        data = pub_map[node_id]
        nodes.append({
            "id": node_id,
            "title": data.get("title"),
            "year": data.get("year"),
            "doi": data.get("doi"),
        })

    edge_payload = []
    for c1, c2, weight in edges:
        edge_payload.append({
            "source": c1,
            "target": c2,
            "weight": weight,
        })

    return {
        "nodes": nodes,
        "edges": edge_payload,
    }
