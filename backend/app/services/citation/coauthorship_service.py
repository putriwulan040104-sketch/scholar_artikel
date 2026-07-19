import json
import re
import threading
import unicodedata
from collections import defaultdict
from itertools import combinations
from app.db import supabase


PUBLICATIONS_TABLE = "cleaned_papers_results"
RELATIONS_TABLE = "article_relations"
RELATION_TYPE = "co_authorship"
_BUILD_LOCK = threading.Lock()


class CoauthorshipBuildInProgressError(RuntimeError):
    pass


def _log(message):
    print(f"[CO-AUTHORSHIP] {message}", flush=True)


def _get_publications(limit=None):
    rows = []
    page_size = 100
    offset = 0

    while True:
        response = (
            supabase
            .table(PUBLICATIONS_TABLE)
            .select("id,authors")
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


def _as_author_list(value):
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

    return re.split(r"\s*[,;]\s*|\s+\band\b\s+", value)


def _normalize_author(value):
    if value is None:
        return None

    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = normalized.replace("…", " ")
    normalized = normalized.replace("...", " ")
    normalized = normalized.strip()
    normalized = re.sub(r"\bet\s+al\.?\b", " ", normalized, flags=re.I)
    normalized = re.sub(r"[^A-Za-zÀ-ÿ'\-\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()

    if not normalized:
        return None
    if len(normalized) < 3:
        return None
    if normalized in {"unknown", "unknown author", "anonymous"}:
        return None

    tokens = normalized.split()
    if len(tokens) == 1 and len(tokens[0]) <= 2:
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
                "[CO-AUTHORSHIP][WARN] stale delete failed "
                f"id={row.get('id')}: {error}",
                flush=True,
            )

    return deleted, errors


def _build_coauthorship(limit=None, min_shared=1):
    _log(
        "Starting build "
        f"(limit={limit or 'all'}, min_shared={min_shared})"
    )
    publications = _get_publications(limit=limit)
    _log(f"Loaded {len(publications)} publications")

    author_index = defaultdict(set)
    author_labels = {}
    publications_with_authors = 0

    for index, publication in enumerate(publications, start=1):
        publication_id = publication.get("id")
        if publication_id is None:
            continue

        publication_authors = set()
        for raw_author in _as_author_list(publication.get("authors")):
            author = _normalize_author(raw_author)
            if not author:
                continue

            publication_authors.add(author)
            author_labels.setdefault(author, str(raw_author).strip())

        if publication_authors:
            publications_with_authors += 1

        for author in publication_authors:
            author_index[author].add(int(publication_id))

        if index % 10 == 0 or index == len(publications):
            _log(
                "Indexing authors "
                f"{index}/{len(publications)} | "
                f"unique_authors={len(author_index)}"
            )

    shared_by_pair = defaultdict(set)
    indexed_authors = list(author_index.items())
    total_authors = len(indexed_authors)

    for index, (author, publication_ids) in enumerate(
        indexed_authors,
        start=1,
    ):
        if len(publication_ids) >= 2:
            for source_id, target_id in combinations(
                sorted(publication_ids),
                2,
            ):
                shared_by_pair[(source_id, target_id)].add(author)

        if index % 100 == 0 or index == total_authors:
            _log(
                "Matching shared authors "
                f"{index}/{total_authors} | "
                f"candidate_pairs={len(shared_by_pair)}"
            )

    relations = {
        pair: sorted(authors)
        for pair, authors in shared_by_pair.items()
        if len(authors) >= int(min_shared)
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

    for index, ((source_id, target_id), authors) in enumerate(
        sorted(relations.items()),
        start=1,
    ):
        shared_authors = [
            author_labels.get(author, author)
            for author in authors
        ]
        weight = len(shared_authors)
        details = {"shared_authors": shared_authors}
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
                    "[CO-AUTHORSHIP][WARN] save failed "
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
        "publications_with_authors": publications_with_authors,
        "unique_authors": len(author_index),
        "matched_relations": len(relations),
        "inserted_edges": inserted,
        "updated_edges": updated,
        "skipped_existing_edges": skipped,
        "deleted_stale_edges": deleted,
        "errors": errors,
        "relation_type": RELATION_TYPE,
        "minimum_shared_authors": int(min_shared),
    }


def build_coauthorship(limit=None, min_shared=1):
    if not _BUILD_LOCK.acquire(blocking=False):
        raise CoauthorshipBuildInProgressError(
            "Proses co-authorship sedang berjalan"
        )

    try:
        return _build_coauthorship(
            limit=limit,
            min_shared=min_shared,
        )
    finally:
        _BUILD_LOCK.release()
