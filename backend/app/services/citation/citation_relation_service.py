import re
from difflib import SequenceMatcher
from app.db import supabase


PUBLICATIONS_TABLE = "publications"
CITATIONS_TABLE = "citations"

DOI_PATTERN = re.compile(
    r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
    re.I
)
YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")


def _normalize_text(text):
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r"https?://doi\.org/", "", text, flags=re.I)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_doi(text):
    if not text:
        return None
    match = DOI_PATTERN.search(text)
    if not match:
        return None
    return match.group(1).lower().strip(" .,;)")


def _extract_year(text):
    if not text:
        return None
    match = YEAR_PATTERN.search(text)
    if not match:
        return None
    try:
        return int(match.group(0))
    except Exception:
        return None


def _title_similarity(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _get_publications():
    all_rows = []
    page_size = 100
    offset = 0

    while True:
        response = (
            supabase
            .table(PUBLICATIONS_TABLE)
            .select("id, title, doi, year, reference_list")
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


def _build_lookup(publications):
    doi_to_id = {}
    title_entries = []

    for pub in publications:
        pub_id = pub.get("id")
        doi = (pub.get("doi") or "").strip().lower()
        title = _normalize_text(pub.get("title") or "")
        year = pub.get("year")

        if doi:
            doi_to_id[doi] = pub_id

        if title:
            title_entries.append({
                "id": pub_id,
                "title": title,
                "year": year
            })

    return doi_to_id, title_entries


def _match_reference_to_publication(ref_text, doi_to_id, title_entries):
    doi = _extract_doi(ref_text)
    if doi and doi in doi_to_id:
        return doi_to_id[doi], "doi_exact"

    ref_norm = _normalize_text(ref_text)
    if not ref_norm:
        return None, "no_signal"

    ref_year = _extract_year(ref_text)
    best_id = None
    best_score = 0.0

    for entry in title_entries:
        score = _title_similarity(ref_norm, entry["title"])
        if ref_year and entry.get("year"):
            if abs(int(entry["year"]) - int(ref_year)) <= 1:
                score += 0.03

        if score > best_score:
            best_score = score
            best_id = entry["id"]

    if best_score >= 0.75:
        return best_id, f"title_fuzzy_{best_score:.2f}"

    return None, f"no_match_{best_score:.2f}"


def _get_existing_edges():
    has_weight = True
    try:
        response = (
            supabase
            .table(CITATIONS_TABLE)
            .select("id, citing_id, cited_id, weight")
            .execute()
        )
    except Exception:
        has_weight = False
        response = (
            supabase
            .table(CITATIONS_TABLE)
            .select("id, citing_id, cited_id")
            .execute()
        )

    edges = {}
    for row in (response.data or []):
        c1 = row.get("citing_id")
        c2 = row.get("cited_id")
        if c1 is None or c2 is None:
            continue
        edge = (int(c1), int(c2))
        edges[edge] = {
            "id": row.get("id"),
            "weight": int(row.get("weight") or 1),
        }

    return edges, has_weight


def build_citation_relations(limit=None):
    publications = _get_publications()
    if limit:
        publications = publications[:int(limit)]

    total_publications = len(publications)
    print(
        f"[CITATION] Start building relations: total_publications={total_publications}"
    )

    doi_to_id, title_entries = _build_lookup(publications)
    existing_edges, has_weight = _get_existing_edges()

    inserted = 0
    updated_weights = 0
    skipped_existing = 0
    unmatched = 0
    errors = 0

    for idx, pub in enumerate(publications, start=1):
        citing_id = pub.get("id")
        ref_list = pub.get("reference_list") or []
        print(
            f"[CITATION] [{idx}/{total_publications}] "
            f"citing_id={citing_id} refs={len(ref_list) if isinstance(ref_list, list) else 0}"
        )

        if not isinstance(ref_list, list):
            continue

        for ref in ref_list:
            if not ref:
                continue

            cited_id, _reason = _match_reference_to_publication(
                ref,
                doi_to_id,
                title_entries
            )

            if not cited_id:
                unmatched += 1
                continue

            if int(citing_id) == int(cited_id):
                continue

            edge = (int(citing_id), int(cited_id))
            if edge in existing_edges:
                if has_weight:
                    row_id = existing_edges[edge].get("id")
                    current_weight = int(existing_edges[edge].get("weight") or 1)
                    if row_id is None:
                        skipped_existing += 1
                        continue
                    try:
                        (
                            supabase
                            .table(CITATIONS_TABLE)
                            .update({"weight": current_weight + 1})
                            .eq("id", row_id)
                            .execute()
                        )
                        existing_edges[edge]["weight"] = current_weight + 1
                        updated_weights += 1
                    except Exception as e:
                        errors += 1
                        print(
                            f"[CITATION][WARN] weight update failed "
                            f"citing_id={citing_id} cited_id={cited_id}: {e}"
                        )
                else:
                    skipped_existing += 1
                continue

            try:
                payload = {
                    "citing_id": int(citing_id),
                    "cited_id": int(cited_id),
                }
                if has_weight:
                    payload["weight"] = 1

                result = (
                    supabase
                    .table(CITATIONS_TABLE)
                    .insert(payload)
                    .execute()
                )

                inserted_row_id = None
                data = result.data or []
                if data:
                    inserted_row_id = data[0].get("id")

                existing_edges[edge] = {
                    "id": inserted_row_id,
                    "weight": 1,
                }
                inserted += 1
            except Exception as e:
                errors += 1
                print(
                    f"[CITATION][WARN] insert failed "
                    f"citing_id={citing_id} cited_id={cited_id}: {e}"
                )

        if idx % 10 == 0 or idx == total_publications:
            print(
                f"[CITATION] Progress {idx}/{total_publications} | "
                f"inserted={inserted} updated_weights={updated_weights} "
                f"skipped={skipped_existing} unmatched={unmatched} errors={errors}"
            )

    print(
        f"[CITATION] Done | processed={total_publications} inserted={inserted} "
        f"updated_weights={updated_weights} skipped={skipped_existing} "
        f"unmatched={unmatched} errors={errors}"
    )

    return {
        "processed_publications": total_publications,
        "inserted_edges": inserted,
        "updated_weighted_edges": updated_weights,
        "skipped_existing_edges": skipped_existing,
        "unmatched_references": unmatched,
        "insert_errors": errors,
        "weight_enabled": has_weight,
    }
