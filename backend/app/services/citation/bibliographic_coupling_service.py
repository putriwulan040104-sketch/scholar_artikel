import json
import re
import threading
from bisect import bisect_left
from collections import defaultdict
from itertools import combinations
from rapidfuzz import fuzz
from app.db import supabase

PUBLICATIONS_TABLE = "cleaned_papers_results"
RELATIONS_TABLE = "article_relations"
RELATION_TYPE = "bibliographic_coupling"
DOI_PATTERN = re.compile(
    r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
    re.I,
)
YEAR_PATTERN = re.compile(r"\((?:19|20)\d{2}[a-z]?\)\.?", re.I)
REFERENCE_BOUNDARY_PATTERN = re.compile(
    r"(?<=\.)\s+"
    r"(?=(?:\[\d+\]\s*)?"
    r"[A-ZÀ-ÖØ-Þ][\wÀ-ÖØ-öø-ÿ'’-]{1,}"
    r"(?:\s+[A-ZÀ-ÖØ-Þ][\wÀ-ÖØ-öø-ÿ'’-]{1,})*,\s+"
    r"[^()]{0,240}?\((?:19|20)\d{2}[a-z]?\)\.?)",
)
URL_NOISE_PATTERN = re.compile(r"https?://|www\.", re.I)
ACCESS_DATE_PATTERN = re.compile(
    r"^accessed on? \d{1,2}\s+[a-z]+\s+\d{4}$",
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

def _clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def _split_reference_entries(reference):
    value = _clean_text(reference)
    if not value:
        return []

    entries = [
        _clean_text(entry)
        for entry in REFERENCE_BOUNDARY_PATTERN.split(value)
        if _clean_text(entry)
    ]
    return entries or [value]

def _extract_reference_title(reference):
    value = _clean_text(reference)
    if not value:
        return ""

    value = re.sub(r"^\s*(?:\[\d+\]|\d+[.)])\s*", "", value)
    year_match = YEAR_PATTERN.search(value)
    candidate = value[year_match.end():] if year_match else value
    candidate = candidate.strip(" .:-;")

    if not year_match:
        parts = re.split(r"\.\s+", candidate, maxsplit=1)
        if len(parts) > 1:
            candidate = parts[1].strip()

    title = re.split(r"\.\s+", candidate, maxsplit=1)[0]
    return _clean_text(title.strip(" .:-;"))

def _extract_reference_authors(reference):
    value = _clean_text(reference)
    if not value:
        return ""

    value = re.sub(r"^\s*(?:\[\d+\]|\d+[.)])\s*", "", value)
    year_match = YEAR_PATTERN.search(value)
    if year_match:
        return _clean_text(value[:year_match.start()].strip(" .:-;"))

    first_sentence = re.split(r"\.\s+", value, maxsplit=1)[0]
    return _clean_text(first_sentence.strip(" .:-;"))

def _extract_reference_year(reference):
    match = YEAR_PATTERN.search(_clean_text(reference))
    if not match:
        return ""

    year_match = re.search(r"(?:19|20)\d{2}[a-z]?", match.group(0), re.I)
    return year_match.group(0) if year_match else ""

def _extract_reference_metadata(reference):
    original_reference = _clean_text(reference)
    title = _extract_reference_title(original_reference)

    return {
        "original_reference": original_reference,
        "authors": _extract_reference_authors(original_reference),
        "year": _extract_reference_year(original_reference),
        "title": title,
    }

def _normalize_reference_title(title):
    value = _clean_text(title)
    if not value:
        return ""

    value = DOI_PATTERN.sub(" ", value)
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"\barxiv:\S+", " ", value, flags=re.I)
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    if len(value) < 12 or len(value.split()) < 3:
        return ""

    return value

def _title_similarity(left, right):
    left = _normalize_reference_title(left)
    right = _normalize_reference_title(right)
    if not left or not right:
        return 0

    return fuzz.ratio(left, right) / 100.0

# Hanya judul yang "layak" ikut pencocokan fuzzy. Menghindari false
# positive dari referensi web (URL), tanggal akses, atau fragmen
# pengarang/penerbit yang bukan judul sebenarnya
def _fuzzy_title_eligible(metadata, normalized_title):
    if len(normalized_title.split()) < 4:
        return False

    original = _clean_text(
        metadata.get("original_reference")
        or metadata.get("reference")
        or ""
    )
    if URL_NOISE_PATTERN.search(original):
        return False
    if ACCESS_DATE_PATTERN.match(normalized_title):
        return False

    return True

# Menggabungkan judul referensi yang mirip ke satu identity.
# Hanya antar referensi yang tahunnya sama
def _fuzzy_merge_title_identities(
    reference_index,
    reference_metadata,
    reference_labels,
    min_similarity,
):
    parent = {}
    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left, right):
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    title_identities = []
    for identity in reference_index:
        if not identity.startswith("title:"):
            continue
        title = _normalize_reference_title(identity[len("title:"):])
        if not title:
            continue
        metadata = reference_metadata.get(identity) or {}
        if not _fuzzy_title_eligible(metadata, title):
            continue
        year = _clean_text(metadata.get("year"))
        title_identities.append((identity, title, year))

    if len(title_identities) < 2:
        return reference_index, reference_metadata, reference_labels, 0

    # Untuk rasio >= min_similarity, selisih panjang tidak boleh terlalu
    # mencapai threshold, jadi bisa di-skip dengan aman.
    max_len_ratio = (2 - min_similarity) / min_similarity

    merged_count = 0
    by_year = defaultdict(list)
    for identity, title, year in title_identities:
        by_year[year].append((identity, title))

    for year, items in by_year.items():
        items.sort(key=lambda pair: len(pair[1]))
        lengths = [len(title) for _, title in items]
        for i in range(len(items)):
            identity, title = items[i]
            parent[identity] = identity
            lower = bisect_left(lengths, lengths[i] / max_len_ratio, 0, i)
            for j in range(lower, i):
                other_identity, other_title = items[j]
                if fuzz.ratio(title, other_title) / 100.0 >= min_similarity:
                    union(identity, other_identity)
                    merged_count += 1

    groups = defaultdict(list)
    for identity, _, _ in title_identities:
        groups[find(identity)].append(identity)

    alias_map = {}
    for members in groups.values():
        if len(members) < 2:
            continue

        representative = max(
            members,
            key=lambda identity: (
                len(reference_labels.get(identity, "")),
                reference_labels.get(identity, ""),
            ),
        )
        for identity in members:
            alias_map[identity] = representative

    if not alias_map:
        return reference_index, reference_metadata, reference_labels, 0

    merged_index = {}
    merged_metadata = {}
    merged_labels = {}
    merged_counts = defaultdict(int)

    for identity, publication_ids in reference_index.items():
        target = alias_map.get(identity, identity)
        merged_index.setdefault(target, set()).update(publication_ids)
        merged_counts[target] += 1

    for identity, publication_ids in reference_index.items():
        target = alias_map.get(identity, identity)
        if target not in merged_labels:
            merged_labels[target] = reference_labels.get(
                target,
                reference_labels.get(identity, ""),
            )
        if target not in merged_metadata:
            merged_metadata[target] = dict(
                reference_metadata.get(target, reference_metadata.get(identity, {}))
            )

    for identity, publication_ids in reference_index.items():
        target = alias_map.get(identity, identity)
        if identity == target:
            continue
        aliases = merged_metadata[target].setdefault("aliases", [])
        if identity not in aliases:
            aliases.append(identity)
        merged_metadata[target]["fuzzy_match"] = True
        if not merged_metadata[target].get("reference"):
            merged_metadata[target]["reference"] = reference_labels.get(
                identity,
                merged_labels[target],
            )

    return merged_index, merged_metadata, merged_labels, merged_count

# Mengekstrak identity dari satu referensi mentah
def _reference_identity_items(reference):
    identities = []

    for entry in _split_reference_entries(reference):
        metadata = _extract_reference_metadata(entry)
        doi_matches = list(DOI_PATTERN.finditer(entry))
        if doi_matches:
            for match in doi_matches:
                doi = match.group(1).lower().rstrip(".,;:)]}")
                identities.append({
                    "identity": f"doi:{doi}",
                    "label": _clean_text(entry),
                    "match_type": "doi",
                    **metadata,
                })
            continue

        title = metadata["title"]
        normalized_title = _normalize_reference_title(title)
        if normalized_title:
            identities.append({
                "identity": f"title:{normalized_title}",
                "label": title,
                "match_type": "title",
                **metadata,
            })
    return identities

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

def _normalize_detail_items(items):
    return {
        re.sub(r"\s+", " ", str(item or "")).strip().lower()
        for item in items or []
        if str(item or "").strip()
    }

def _extract_current_shared_references(details):
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except (TypeError, ValueError):
            return []

    if not isinstance(details, dict):
        return []

    shared = details.get("shared_references")
    return shared if isinstance(shared, list) else []

def _extract_current_shared_reference_matches(details):
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except (TypeError, ValueError):
            return []

    if not isinstance(details, dict):
        return []

    shared = details.get("shared_reference_matches")
    return shared if isinstance(shared, list) else []

def _normalize_match_items(items):
    normalized = []
    for item in items or []:
      if not isinstance(item, dict):
          continue
      normalized.append({
          "reference": _clean_text(item.get("reference")).lower(),
          "match_type": _clean_text(item.get("match_type")).lower(),
          "authors": _clean_text(item.get("authors")).lower(),
          "year": _clean_text(item.get("year")).lower(),
          "title": _clean_text(item.get("title")).lower(),
          "original_reference": _clean_text(
              item.get("original_reference")
          ).lower(),
      })
    return sorted(
        normalized,
        key=lambda item: (
            item["match_type"],
            item["reference"],
            item["authors"],
            item["year"],
            item["title"],
        ),
    )

def _is_unique_conflict(error):
    message = str(error).lower()
    return (
        getattr(error, "code", None) == "23505"
        or "'code': '23505'" in message
        or "duplicate key value" in message
    )

def _build_bibliographic_coupling(limit=None, min_shared=1, title_similarity_threshold=0.90):
    _log(
        "Starting build "
        f"(limit={limit or 'all'}, min_shared={min_shared}, "
        f"title_similarity_threshold={title_similarity_threshold})"
    )
    publications = _get_publications(limit=limit)
    _log(f"Loaded {len(publications)} publications")

    reference_index = defaultdict(set)
    reference_labels = {}
    reference_metadata = {}

    for index, publication in enumerate(publications, start=1):
        publication_id = publication.get("id")
        references = publication.get("reference_list") or []
        if publication_id is None or not isinstance(references, list):
            continue

        for reference in references:
            for item in _reference_identity_items(reference):
                identity = item["identity"]
                if not identity:
                    continue
                reference_index[identity].add(int(publication_id))
                reference_labels.setdefault(identity, item["label"])
                reference_metadata.setdefault(identity, {
                    "reference": item["label"],
                    "match_type": item["match_type"],
                    "authors": item.get("authors") or "",
                    "year": item.get("year") or "",
                    "title": item.get("title") or item["label"],
                    "original_reference": (
                        item.get("original_reference") or item["label"]
                    ),
                })

                match_type = item["match_type"]
                reference_labels.setdefault(
                    f"{identity}:match_type",
                    match_type,
                )

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

    fuzzy_merged_references = 0
    if title_similarity_threshold and title_similarity_threshold > 0:
        (
            reference_index,
            reference_metadata,
            reference_labels,
            fuzzy_merged_references,
        ) = _fuzzy_merge_title_identities(
            reference_index,
            reference_metadata,
            reference_labels,
            title_similarity_threshold,
        )
        _log(
            "Fuzzy title merge completed | "
            f"merged_aliases={fuzzy_merged_references} "
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
        shared_reference_matches = [
            reference_metadata.get(identity, {
                "reference": reference_labels[identity],
                "match_type": reference_labels.get(
                    f"{identity}:match_type",
                    "title" if identity.startswith("title:") else "doi",
                ),
                "authors": "",
                "year": "",
                "title": reference_labels[identity],
                "original_reference": reference_labels[identity],
            })
            for identity in identities
        ]
        details = {
            "shared_references": shared_references,
            "shared_reference_matches": shared_reference_matches,
        }
        current = existing.get((source_id, target_id))

        try:
            if current:
                current_weight = int(current.get("weight") or 1)
                current_shared_references = (
                    _extract_current_shared_references(
                        current.get("details")
                    )
                )
                current_shared_matches = (
                    _extract_current_shared_reference_matches(
                        current.get("details")
                    )
                )
                details_match = (
                    _normalize_detail_items(current_shared_references)
                    == _normalize_detail_items(shared_references)
                    and _normalize_match_items(current_shared_matches)
                    == _normalize_match_items(shared_reference_matches)
                )
                if current_weight == weight and details_match:
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
        "title_similarity_threshold": title_similarity_threshold,
        "fuzzy_merged_references": fuzzy_merged_references,
    }


def build_bibliographic_coupling(
    limit=None,
    min_shared=1,
    title_similarity_threshold=0.90,
):
    if not _BUILD_LOCK.acquire(blocking=False):
        raise BibliographicBuildInProgressError(
            "Proses bibliographic coupling sedang berjalan"
        )

    try:
        return _build_bibliographic_coupling(
            limit=limit,
            min_shared=min_shared,
            title_similarity_threshold=title_similarity_threshold,
        )
    finally:
        _BUILD_LOCK.release()
