import os
import re
from types import SimpleNamespace
from urllib.parse import quote
import requests

OPENALEX_BASE_URL = "https://api.openalex.org"

HEADERS = {
    "User-Agent": "paperCi/1.0 (openalex fallback)",
    "Accept": "application/json",
}

DOI_PATTERN = re.compile(
    r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
    re.I
)
OPENALEX_WORK_ID_PATTERN = re.compile(r"(W\d+)", re.I)
REFERENCE_LIMIT = 30
_WORK_CACHE = {}

def _clean_doi(value):
    if not value:
        return None

    value = value.strip()
    value = value.replace("https://doi.org/", "")
    value = value.replace("http://doi.org/", "")
    value = value.replace("doi.org/", "")
    value = value.strip().strip(".,;)")

    match = DOI_PATTERN.search(value)
    if match:
        return match.group(1).lower()

    return None

def _extract_doi_candidates(article):
    candidates = []

    for raw_value in [
        article.get("url"),
        article.get("pdf_url"),
        article.get("title"),
    ]:
        if not raw_value:
            continue
        match = DOI_PATTERN.search(str(raw_value))
        if match:
            candidates.append(match.group(1))

    cleaned = []
    seen = set()

    for doi in candidates:
        normalized = _clean_doi(doi)
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)

    return cleaned

def _reconstruct_abstract(abstract_inverted_index):
    if not abstract_inverted_index:
        return None

    positions = {}

    for word, idx_list in abstract_inverted_index.items():
        for idx in idx_list:
            positions[idx] = word

    if not positions:
        return None

    max_idx = max(positions.keys())
    tokens = []

    for idx in range(max_idx + 1):
        token = positions.get(idx, "")
        if token:
            tokens.append(token)

    abstract = " ".join(tokens).strip()
    return abstract or None

def _extract_authors(work):
    authors = []

    for authorship in work.get("authorships", []):
        author_obj = authorship.get("author", {})
        name = (author_obj.get("display_name") or "").strip()
        if name:
            authors.append(name)

    return authors

def _extract_journal(work):
    primary = work.get("primary_location", {}) or {}
    source = primary.get("source", {}) or {}
    name = (source.get("display_name") or "").strip()

    if name:
        return name

    host_venue = work.get("host_venue", {}) or {}
    return (host_venue.get("display_name") or "").strip() or None

def _extract_keywords(work):
    keywords = []

    for item in work.get("keywords", []) or []:
        display_name = (item.get("display_name") or "").strip()
        if display_name:
            keywords.append(display_name)

    if keywords:
        return keywords

    for item in work.get("concepts", []) or []:
        display_name = (item.get("display_name") or "").strip()
        if display_name:
            keywords.append(display_name)
        if len(keywords) >= 15:
            break

    return keywords

def _format_reference_citation(work):
    title = (work.get("display_name") or "").strip()
    year = work.get("publication_year")
    authors = _extract_authors(work)
    doi = _clean_doi(work.get("doi") or "")
    journal = _extract_journal(work)

    if not title:
        return None

    if authors:
        first_author = authors[0]
        author_part = (
            f"{first_author} et al."
            if len(authors) > 1
            else first_author
        )
    else:
        author_part = "Unknown author"

    year_part = str(year) if year else "n.d."

    parts = [
        f"{author_part} ({year_part}). {title}."
    ]

    if journal:
        parts.append(journal + ".")
    if doi:
        parts.append(f"https://doi.org/{doi}")

    return " ".join(parts).strip()

def _extract_openalex_work_id(value):
    if not value:
        return None

    match = OPENALEX_WORK_ID_PATTERN.search(str(value))
    if not match:
        return None

    return match.group(1).upper()

def _fetch_work_by_openalex_id(work_id):
    if not work_id:
        return None

    if work_id in _WORK_CACHE:
        return _WORK_CACHE[work_id]

    try:
        data = _openalex_get_json(
            f"{OPENALEX_BASE_URL}/works/{work_id}"
        )
    except Exception:
        data = None

    _WORK_CACHE[work_id] = data
    return data

def _extract_references(work):
    references = []
    seen = set()

    for item in work.get("referenced_works", []) or []:
        work_id = _extract_openalex_work_id(item)
        if not work_id:
            continue

        if work_id in seen:
            continue
        seen.add(work_id)

        ref_work = _fetch_work_by_openalex_id(work_id)
        if not ref_work:
            continue

        citation_text = _format_reference_citation(ref_work)
        if not citation_text:
            continue

        references.append(citation_text)

        if len(references) >= REFERENCE_LIMIT:
            break

    return references

def _work_to_result(work):
    title = (work.get("display_name") or "").strip()
    doi = _clean_doi(work.get("doi") or "")
    year = work.get("publication_year")
    journal = _extract_journal(work)
    authors = _extract_authors(work)
    keywords = _extract_keywords(work)
    references = _extract_references(work)
    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))

    metadata = SimpleNamespace(
        title=title or None,
        author=", ".join(authors) if authors else None,
        sitename=journal,
        doi=doi,
    )

    return {
        "metadata": metadata,
        "content": abstract,
        "doi": doi,
        "keywords": keywords,
        "references": references,
        "year": year,
        "title": title or None,
        "authors": authors,
        "journal": journal,
    }

def _openalex_get_json(url, params=None):
    request_params = dict(params or {})

    mailto = os.getenv("OPENALEX_EMAIL")
    if mailto and "mailto" not in request_params:
        request_params["mailto"] = mailto

    response = requests.get(
        url,
        headers=HEADERS,
        params=request_params,
        timeout=25,
    )
    response.raise_for_status()
    return response.json()

def _fetch_by_doi(doi):
    encoded = quote(f"https://doi.org/{doi}", safe="")
    url = f"{OPENALEX_BASE_URL}/works/{encoded}"

    try:
        data = _openalex_get_json(url)
        return data
    except Exception:
        return None

def _fetch_by_title(title):
    if not title:
        return None

    try:
        data = _openalex_get_json(
            f"{OPENALEX_BASE_URL}/works",
            params={"search": title, "per-page": 1}
        )
    except Exception:
        return None

    results = data.get("results", [])
    if not results:
        return None

    return results[0]

def fetch_openalex_enrichment(article):
    doi_candidates = _extract_doi_candidates(article)

    for doi in doi_candidates:
        work = _fetch_by_doi(doi)
        if work:
            return _work_to_result(work)

    work = _fetch_by_title(article.get("title"))
    if work:
        return _work_to_result(work)

    return None
