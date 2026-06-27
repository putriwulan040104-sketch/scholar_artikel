import json
import re
import threading
import unicodedata
from collections import defaultdict
from itertools import combinations

from app.db import supabase


PUBLICATIONS_TABLE = "cleaned_papers_results"
RELATIONS_TABLE = "article_relations"
RELATION_TYPE = "keyword_cooccurrence"
_BUILD_LOCK = threading.Lock()

GENERIC_KEYWORDS = {
    "artificial intelligence",
    "business",
    "computer science",
    "engineering",
    "world wide web",
}


class KeywordCooccurrenceBuildInProgressError(RuntimeError):
    pass


def _log(message):
    print(f"[KEYWORD COOCCURRENCE] {message}", flush=True)


def _get_publications(limit=None):
    rows = []
    page_size = 100
    offset = 0

    while True:
        response = (
            supabase
            .table(PUBLICATIONS_TABLE)
            .select("id,keywords")
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


def _as_keyword_list(value):
    if isinstance(value, list):
        return value

    if not isinstance(value, str):
        return []

    value = value.strip()
    if not value:
        return []

    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except (TypeError, ValueError):
            pass

    return re.split(r"[;,\n|]+", value)


def _normalize_keyword_text(value):
    if value is None:
        return None

    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[_/\\-]+", " ", normalized)
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _normalize_keyword(value):
    normalized = _normalize_keyword_text(value)
    if normalized is None:
        return None

    if (
        len(normalized) < 2
        or len(normalized) > 120
        or len(normalized.split()) > 12
        or normalized in GENERIC_KEYWORDS
    ):
        return None

    return normalized


def _load_existing_relations():
    rows = []
    page_size = 1000
    offset = 0

    while True:
        response = (
            supabase
            .table(RELATIONS_TABLE)
            .select("id,source_id,target_id,weight,details")
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


def _delete_stale_relations(existing, current_pairs):
    stale_rows = [
        row
        for pair, row in existing.items()
        if pair not in current_pairs
    ]
    deleted = 0
    errors = 0

    for row in stale_rows:
        try:
            (
                supabase
                .table(RELATIONS_TABLE)
                .delete()
                .eq("id", row["id"])
                .execute()
            )
            deleted += 1
        except Exception as error:
            errors += 1
            print(
                "[KEYWORD COOCCURRENCE][WARN] stale delete failed "
                f"id={row.get('id')}: {error}",
                flush=True,
            )

    return deleted, errors


def _build_keyword_cooccurrence(limit=None, min_shared=2):
    _log(
        "Starting build "
        f"(limit={limit or 'all'}, min_shared={min_shared})"
    )
    publications = _get_publications(limit=limit)
    _log(f"Loaded {len(publications)} publications")

    keyword_index = defaultdict(set)
    keyword_labels = {}
    publications_with_keywords = 0
    ignored_generic_keywords = 0

    for index, publication in enumerate(publications, start=1):
        publication_id = publication.get("id")
        if publication_id is None:
            continue

        publication_keywords = set()
        for raw_keyword in _as_keyword_list(publication.get("keywords")):
            keyword = _normalize_keyword(raw_keyword)
            if not keyword:
                raw_normalized = _normalize_keyword_text(raw_keyword)
                if raw_normalized in GENERIC_KEYWORDS:
                    ignored_generic_keywords += 1
                continue

            publication_keywords.add(keyword)
            keyword_labels.setdefault(keyword, str(raw_keyword).strip())

        if publication_keywords:
            publications_with_keywords += 1

        for keyword in publication_keywords:
            keyword_index[keyword].add(int(publication_id))

        if index % 10 == 0 or index == len(publications):
            _log(
                "Indexing keywords "
                f"{index}/{len(publications)} | "
                f"unique_keywords={len(keyword_index)}"
            )

    _log(
        "Keyword index completed | "
        f"publications_with_keywords={publications_with_keywords} "
        f"unique_keywords={len(keyword_index)} "
        f"ignored_generic={ignored_generic_keywords}"
    )

    shared_by_pair = defaultdict(set)
    indexed_keywords = list(keyword_index.items())
    total_keywords = len(indexed_keywords)

    for index, (keyword, publication_ids) in enumerate(
        indexed_keywords,
        start=1,
    ):
        if len(publication_ids) >= 2:
            for source_id, target_id in combinations(
                sorted(publication_ids),
                2,
            ):
                shared_by_pair[(source_id, target_id)].add(keyword)

        if index % 100 == 0 or index == total_keywords:
            _log(
                "Matching shared keywords "
                f"{index}/{total_keywords} | "
                f"candidate_pairs={len(shared_by_pair)}"
            )

    relations = {
        pair: sorted(keywords)
        for pair, keywords in shared_by_pair.items()
        if len(keywords) >= int(min_shared)
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

    for index, ((source_id, target_id), keywords) in enumerate(
        sorted(relations.items()),
        start=1,
    ):
        shared_keywords = [
            keyword_labels.get(keyword, keyword)
            for keyword in keywords
        ]
        weight = len(shared_keywords)
        details = {"shared_keywords": shared_keywords}
        current = existing.get((source_id, target_id))

        try:
            if current:
                current_weight = int(current.get("weight") or 1)
                current_details = current.get("details") or {}
                if (
                    current_weight == weight
                    and current_details == details
                ):
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
                    "[KEYWORD COOCCURRENCE][WARN] save failed "
                    f"source_id={source_id} "
                    f"target_id={target_id}: {error}",
                    flush=True,
                )

        if index % 25 == 0 or index == total_relations:
            _log(
                "Saving relations "
                f"{index}/{total_relations} | "
                f"inserted={inserted} updated={updated} "
                f"skipped={skipped} errors={errors}"
            )

    deleted = 0
    if limit is None:
        deleted, delete_errors = _delete_stale_relations(
            existing,
            set(relations),
        )
        errors += delete_errors
        if deleted or delete_errors:
            _log(
                "Removing stale relations | "
                f"deleted={deleted} errors={delete_errors}"
            )

    _log(
        "Done | "
        f"publications={len(publications)} relations={len(relations)} "
        f"inserted={inserted} updated={updated} "
        f"skipped={skipped} deleted={deleted} errors={errors}"
    )
    return {
        "processed_publications": len(publications),
        "publications_with_keywords": publications_with_keywords,
        "unique_keywords": len(keyword_index),
        "ignored_generic_keywords": ignored_generic_keywords,
        "excluded_keywords": sorted(GENERIC_KEYWORDS),
        "matched_relations": len(relations),
        "inserted_edges": inserted,
        "updated_edges": updated,
        "skipped_existing_edges": skipped,
        "deleted_stale_edges": deleted,
        "errors": errors,
        "relation_type": RELATION_TYPE,
        "minimum_shared_keywords": int(min_shared),
    }


def build_keyword_cooccurrence(limit=None, min_shared=2):
    if not _BUILD_LOCK.acquire(blocking=False):
        raise KeywordCooccurrenceBuildInProgressError(
            "Proses keyword co-occurrence sedang berjalan"
        )

    try:
        return _build_keyword_cooccurrence(
            limit=limit,
            min_shared=min_shared,
        )
    finally:
        _BUILD_LOCK.release()
