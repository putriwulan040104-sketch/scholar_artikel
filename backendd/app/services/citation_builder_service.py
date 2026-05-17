from rapidfuzz import fuzz
from ..database import supabase
from .pdf_parser_service import extract_references_from_pdf
from ..utils.text_utils import normalize

SIMILARITY_THRESHOLD = 60


def build_citations_from_pdfs(limit: int = 0, insert_to_db=True):

    query = supabase.table("scholar_articles").select("id,title,pdf_url")

    if limit > 0:
        query = query.limit(limit)

    articles = query.execute().data or []

    print("articles loaded:", len(articles))

    title_map = {
        normalize(a["title"]): a["id"]
        for a in articles
    }

    edges = set()

    for article in articles:

        refs = extract_references_from_pdf(article["pdf_url"])
        print("refs for", article["title"], ":", len(refs))

        for ref in refs:
            ref_norm = normalize(ref)

            for title_norm, target_id in title_map.items():

                score = fuzz.token_set_ratio(title_norm, ref_norm)

                if score >= SIMILARITY_THRESHOLD:
                    edges.add((article["id"], target_id))

    edges_list = [
        {"citing_id": s, "cited_id": t}
        for s, t in edges
    ]

    print("edges found:", len(edges_list))

    if insert_to_db and edges_list:
        supabase.table("citations").upsert(edges_list).execute()

    return {
        "edges_found": len(edges_list),
        "edges": edges_list
    }
