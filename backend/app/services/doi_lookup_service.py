from app.db import supabase


DOI_TABLE = "scholar_article_doi"
DOI_LOOKUP_BATCH_SIZE = 500


def _chunks(values, size):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def load_doi_by_publication_id(publication_ids):
    if not publication_ids:
        return {}

    normalized_ids = []
    for raw_id in publication_ids:
        try:
            normalized_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue

    if not normalized_ids:
        return {}

    doi_by_id = {}
    for batch_ids in _chunks(sorted(set(normalized_ids)), DOI_LOOKUP_BATCH_SIZE):
        response = (
            supabase
            .table(DOI_TABLE)
            .select("id,doi")
            .in_("id", batch_ids)
            .execute()
        )

        doi_by_id.update({
            int(item["id"]): item.get("doi")
            for item in (response.data or [])
            if item.get("id") is not None
        })

    return doi_by_id


def load_doi_for_publication(publication_id):
    return load_doi_by_publication_id([publication_id]).get(int(publication_id))
