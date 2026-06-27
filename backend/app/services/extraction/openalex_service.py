import os
import re
from urllib.parse import quote
import requests

OPENALEX_BASE_URL = "https://api.openalex.org"
HEADERS = {
    "User-Agent": "paperCi/1.0 (openalex locator)",
    "Accept": "application/json",
}
DOI_PATTERN = re.compile(
    r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
    re.I,
)
OPENALEX_WORK_ID_PATTERN = re.compile(r"(W\d+)", re.I)
REFERENCE_LIMIT = 30
_WORK_CACHE = {}

def _clean_doi(value):
    if not value:
        return None

    value = str(value).strip()
    value = value.replace("https://doi.org/", "")
    value = value.replace("http://doi.org/", "")
    value = value.replace("doi.org/", "")
    value = value.strip().strip(".,;)")

    match = DOI_PATTERN.search(value)
    if not match:
        return None

    doi = match.group(1).lower()
    if doi.endswith(".pdf"):
        doi = doi[:-4]

    return doi

def _extract_doi_candidates(article):
    candidates = []
    for raw_value in [
        article.get("doi"),
        article.get("url"),
        article.get("pdf_url"),
    ]:
        doi = _clean_doi(raw_value)
        if doi and doi not in candidates:
            candidates.append(doi)

    return candidates

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
    if not doi:
        return None

    encoded = quote(f"https://doi.org/{doi}", safe="")
    try:
        return _openalex_get_json(f"{OPENALEX_BASE_URL}/works/{encoded}")
    except Exception:
        return None


def _name_tokens(value):
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", str(value or ""))
        if token.lower() not in {"and", "the", "with", "author", "authors"}
    }


def _extract_article_author_tokens(article):
    raw_authors = article.get("authors")
    if not raw_authors:
        return set()

    if isinstance(raw_authors, list):
        values = raw_authors
    else:
        values = re.split(r",|;|\band\b", str(raw_authors))

    tokens = set()
    for value in values:
        tokens.update(_name_tokens(value))

    return tokens


def _extract_authors(work):
    authors = []
    for authorship in work.get("authorships", []):
        author = authorship.get("author", {}) or {}
        name = (author.get("display_name") or "").strip()
        if name:
            authors.append(name)

    return authors


def _author_overlap_score(work, article_author_tokens):
    if not article_author_tokens:
        return 0

    work_tokens = set()
    for author in _extract_authors(work):
        work_tokens.update(_name_tokens(author))

    return len(article_author_tokens & work_tokens)


def _fetch_by_title(title, article=None):
    if not title:
        return None

    try:
        data = _openalex_get_json(
            f"{OPENALEX_BASE_URL}/works",
            params={"search": title, "per-page": 5},
        )
    except Exception:
        return None

    results = data.get("results", [])
    if not results:
        return None

    author_tokens = _extract_article_author_tokens(article or {})
    if not author_tokens:
        return results[0]

    return max(
        results,
        key=lambda work: _author_overlap_score(work, author_tokens),
    )


def _extract_pdf_url(work):
    best_location = work.get("best_oa_location") or {}
    if best_location.get("pdf_url"):
        return best_location["pdf_url"]

    for location in work.get("locations", []) or []:
        if location.get("pdf_url"):
            return location["pdf_url"]

    return None


def _extract_document_urls(work):
    urls = []
    seen = set()
    locations = []

    best_location = work.get("best_oa_location") or {}
    if best_location:
        locations.append(best_location)
    locations.extend(work.get("locations", []) or [])

    for location in locations:
        for field in ("pdf_url", "landing_page_url"):
            url = (location.get(field) or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            urls.append(url)

    return urls


def _work_to_result(work):
    return {
        "pdf_url": _extract_pdf_url(work),
        "document_urls": _extract_document_urls(work),
    }


def _extract_journal(work):
    primary = work.get("primary_location", {}) or {}
    source = primary.get("source", {}) or {}
    name = (source.get("display_name") or "").strip()
    if name:
        return name

    host_venue = work.get("host_venue", {}) or {}
    return (host_venue.get("display_name") or "").strip() or None


def _format_reference_citation(work):
    title = (work.get("display_name") or "").strip()
    if not title:
        return None

    authors = _extract_authors(work)
    author_part = (
        f"{authors[0]} et al."
        if len(authors) > 1
        else authors[0]
        if authors
        else "Unknown author"
    )
    year = work.get("publication_year") or "n.d."
    journal = _extract_journal(work)
    doi = _clean_doi(work.get("doi") or "")

    parts = [f"{author_part} ({year}). {title}."]
    if journal:
        parts.append(f"{journal}.")
    if doi:
        parts.append(f"https://doi.org/{doi}")

    return " ".join(parts).strip()


def _extract_openalex_work_id(value):
    match = OPENALEX_WORK_ID_PATTERN.search(str(value or ""))
    if not match:
        return None

    return match.group(1).upper()


def _fetch_work_by_openalex_id(work_id):
    if not work_id:
        return None
    if work_id in _WORK_CACHE:
        return _WORK_CACHE[work_id]

    try:
        data = _openalex_get_json(f"{OPENALEX_BASE_URL}/works/{work_id}")
    except Exception:
        data = None

    _WORK_CACHE[work_id] = data
    return data


def _extract_references(work):
    references = []
    seen = set()

    for item in work.get("referenced_works", []) or []:
        work_id = _extract_openalex_work_id(item)
        if not work_id or work_id in seen:
            continue

        seen.add(work_id)
        ref_work = _fetch_work_by_openalex_id(work_id)
        citation = _format_reference_citation(ref_work or {})
        if citation:
            references.append(citation)

        if len(references) >= REFERENCE_LIMIT:
            break

    return references


def fetch_openalex_enrichment(article):
    for doi in _extract_doi_candidates(article):
        work = _fetch_by_doi(doi)
        if work:
            return _work_to_result(work)

    work = _fetch_by_title(article.get("title"), article=article)
    if work:
        return _work_to_result(work)

    return None


def fetch_openalex_references_by_doi(article):
    for doi in _extract_doi_candidates(article):
        work = _fetch_by_doi(doi)
        if not work:
            continue

        if _clean_doi(work.get("doi") or "") != doi:
            continue

        return _extract_references(work)

    return []
