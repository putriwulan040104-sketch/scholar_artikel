import re
import threading
from collections import defaultdict
from itertools import combinations
from app.db import supabase


PUBLICATIONS_TABLE = "cleaned_papers_results"
RELATIONS_TABLE = "article_relations"
RELATION_TYPE = "bibliographic_coupling"
DOI_PATTERN = re.compile(
    r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
    re.I,
)
_BUILD_LOCK = threading.Lock()


class BibliographicBuildInProgressError(RuntimeError):
    pass


def _log(message):
    print(f"[BIBLIOGRAPHIC] {message}", flush=True)


def _get_publications(limit=None):
    rows = []
    page_size = 100
    offset = 0

    while True:
        response = (
            supabase
            .table(PUBLICATIONS_TABLE)
            .select("id,reference_list")
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = response.data or []
        if not batch:
            break
        rows.extend(batch)
        offset += page_size
        if len(batch) < page_size:
            break

    if limit:
        return rows[:int(limit)]
    return rows


def _reference_identity(reference):
    if not reference:
        return None

    value = str(reference).strip()
    doi_match = DOI_PATTERN.search(value)
    if doi_match:
        doi = doi_match.group(1).lower().rstrip(".,;:)]}")
        return f"doi:{doi}"

    normalized = value.lower()
    normalized = re.sub(r"https?://\S+", " ", normalized)
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if len(normalized) < 30:
        return None

    return f"text:{normalized}"

def _load_existing_relations():
    rows = []
    page_size = 1000
    offset = 0

    while True:
        response = (
            supabase
            .table(RELATIONS_TABLE)
            .select("id,source_id,target_id,weight")
            .eq("relation_type", RELATION_TYPE)
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = response.data or []
        if not batch:
            break
        rows.extend(batch)
        offset += page_size
        if len(batch) < page_size:
            break

    return {
        (int(row["source_id"]), int(row["target_id"])): row
        for row in rows
    }


def _is_unique_conflict(error):
    message = str(error).lower()
    return (
        getattr(error, "code", None) == "23505"
        or "'code': '23505'" in message
        or "duplicate key value" in message
    )


def _build_bibliographic_coupling(limit=None, min_shared=1):
    _log(
        "Starting build "
        f"(limit={limit or 'all'}, min_shared={min_shared})"
    )
    publications = _get_publications(limit=limit)
    _log(f"Loaded {len(publications)} publications")

    reference_index = defaultdict(set)
    reference_labels = {}

    for index, publication in enumerate(publications, start=1):
        publication_id = publication.get("id")
        references = publication.get("reference_list") or []
        if publication_id is None or not isinstance(references, list):
            continue

        for reference in references:
            identity = _reference_identity(reference)
            if not identity:
                continue
            reference_index[identity].add(int(publication_id))
            reference_labels.setdefault(identity, str(reference).strip())

        if index % 10 == 0 or index == len(publications):
            _log(
                "Indexing references "
                f"{index}/{len(publications)} | "
                f"unique_references={len(reference_index)}"
            )

    _log(
        "Reference index completed | "
        f"unique_references={len(reference_index)}"
    )

    shared_by_pair = defaultdict(list)
    indexed_references = list(reference_index.items())
    total_references = len(indexed_references)
    for index, (identity, publication_ids) in enumerate(
        indexed_references,
        start=1,
    ):
        if len(publication_ids) < 2:
            pass
        else:
            for source_id, target_id in combinations(
                sorted(publication_ids),
                2,
            ):
                shared_by_pair[(source_id, target_id)].append(identity)

        if index % 250 == 0 or index == total_references:
            _log(
                "Matching shared references "
                f"{index}/{total_references} | "
                f"candidate_pairs={len(shared_by_pair)}"
            )

    relations = {
        pair: identities
        for pair, identities in shared_by_pair.items()
        if len(identities) >= int(min_shared)
    }
    _log(
        "Matching completed | "
        f"candidate_pairs={len(shared_by_pair)} "
        f"qualified_relations={len(relations)}"
    )

    existing = _load_existing_relations()
    _log(f"Loaded {len(existing)} existing relations")

    inserted = 0
    updated = 0
    skipped = 0
    errors = 0
    total_relations = len(relations)

    for index, ((source_id, target_id), identities) in enumerate(
        relations.items(),
        start=1,
    ):
        weight = len(identities)
        shared_references = [
            reference_labels[identity]
            for identity in identities
        ]
        details = {
            "shared_references": shared_references,
        }
        current = existing.get((source_id, target_id))

        try:
            if current:
                current_weight = int(current.get("weight") or 1)
                if current_weight == weight:
                    skipped += 1
                    continue
                (
                    supabase
                    .table(RELATIONS_TABLE)
                    .update({
                        "weight": weight,
                        "details": details,
                    })
                    .eq("id", current["id"])
                    .execute()
                )
                updated += 1
                continue

            (
                supabase
                .table(RELATIONS_TABLE)
                .insert({
                    "source_id": source_id,
                    "target_id": target_id,
                    "relation_type": RELATION_TYPE,
                    "weight": weight,
                    "details": details,
                })
                .execute()
            )
            inserted += 1
        except Exception as error:
            if _is_unique_conflict(error):
                skipped += 1
            else:
                errors += 1
                print(
                    "[BIBLIOGRAPHIC][WARN] save failed "
                    f"source_id={source_id} target_id={target_id}: {error}",
                    flush=True,
                )

        if index % 10 == 0 or index == total_relations:
            _log(
                "Saving relations "
                f"{index}/{total_relations} | "
                f"inserted={inserted} updated={updated} "
                f"skipped={skipped} errors={errors}"
            )

    _log(
        "Done | "
        f"publications={len(publications)} relations={len(relations)} "
        f"inserted={inserted} updated={updated} "
        f"skipped={skipped} errors={errors}"
    )
    return {
        "processed_publications": len(publications),
        "matched_relations": len(relations),
        "inserted_edges": inserted,
        "updated_edges": updated,
        "skipped_existing_edges": skipped,
        "errors": errors,
        "relation_type": RELATION_TYPE,
        "minimum_shared_references": int(min_shared),
    }


def build_bibliographic_coupling(limit=None, min_shared=1):
    if not _BUILD_LOCK.acquire(blocking=False):
        raise BibliographicBuildInProgressError(
            "Proses bibliographic coupling sedang berjalan"
        )

    try:
        return _build_bibliographic_coupling(
            limit=limit,
            min_shared=min_shared,
        )
    finally:
        _BUILD_LOCK.release()
