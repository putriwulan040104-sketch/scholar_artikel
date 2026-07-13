import os
import re
from difflib import SequenceMatcher
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


def _normalize_title(value):
    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _title_similarity(left, right):
    left = _normalize_title(left)
    right = _normalize_title(right)
    if not left or not right:
        return 0

    return SequenceMatcher(None, left, right).ratio()


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

    article = article or {}
    author_tokens = _extract_article_author_tokens(article)
    doi_candidates = _extract_doi_candidates(article)
    scored = []

    for work in results:
        work_doi = _clean_doi(work.get("doi") or "")
        if doi_candidates and work_doi and work_doi not in doi_candidates:
            continue

        similarity = _title_similarity(title, work.get("display_name"))
        author_overlap = _author_overlap_score(work, author_tokens)
        if similarity < 0.8:
            continue
        if author_tokens and author_overlap <= 0:
            continue
        if not author_tokens and similarity < 0.92:
            continue

        scored.append((author_overlap, similarity, work))

    if not scored:
        return None

    return max(scored, key=lambda item: (item[0], item[1]))[2]


def _work_matches_article(work, article):
    doi_candidates = _extract_doi_candidates(article)
    work_doi = _clean_doi(work.get("doi") or "")
    if doi_candidates:
        return work_doi in doi_candidates

    title = article.get("title")
    similarity = _title_similarity(title, work.get("display_name"))
    author_tokens = _extract_article_author_tokens(article)
    author_overlap = _author_overlap_score(work, author_tokens)

    if author_tokens:
        return similarity >= 0.8 and author_overlap > 0

    return similarity >= 0.92


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
        for field in ("landing_page_url", "pdf_url"):
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


def fetch_openalex_enrichment(article):
    for doi in _extract_doi_candidates(article):
        work = _fetch_by_doi(doi)
        if work and _work_matches_article(work, article):
            return _work_to_result(work)

    work = _fetch_by_title(article.get("title"), article=article)
    if work and _work_matches_article(work, article):
        return _work_to_result(work)

    return None
