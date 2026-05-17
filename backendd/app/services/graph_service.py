from ..database import supabase


def build_graph():

    edges_res = supabase.table("citations").select("citing_id,cited_id").execute()
    nodes_res = supabase.table("scholar_articles").select("id,title,year,citations").execute()

    edges = [
        {"source": e["citing_id"], "target": e["cited_id"]}
        for e in (edges_res.data or [])
    ]

    return {
        "nodes": nodes_res.data or [],
        "edges": edges
    }
