from app.db import supabase
import time
from app.services.extraction.article_service import (
    extract_article
)
from app.services.extraction.pdf_service import (
    download_pdf,
    extract_pdf_content,
    remove_pdf
)
from app.models.publication_model import (
    build_publication
)
from app.services.extraction.openalex_service import (
    fetch_openalex_enrichment
)
import app.services.processing.normalization_service as normalizer
from app.utils.cleaner import clean_text


SOURCE_TABLE = "scholar_articles"
TARGET_TABLE = "publications"

def _sanitize_for_postgres(value):
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [_sanitize_for_postgres(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _sanitize_for_postgres(val)
            for key, val in value.items()
        }

    return value

# GET ARTICLES
def get_articles():
    all_rows = []
    page_size = 100
    offset = 0
    max_retries = 3

    while True:
        response = None
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                response = (
                    supabase
                    .table(SOURCE_TABLE)
                    .select("id, title, authors, year, source, url, pdf_url")
                    .order("id", desc=False)
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                last_error = None
                break
            except Exception as e:
                last_error = e
                print(
                    f"[WARN] get_articles retry {attempt}/{max_retries} "
                    f"offset={offset}: {e}"
                )
                time.sleep(attempt * 2)

        if last_error is not None:
            raise Exception(
                f"Failed fetching scholar_articles at offset={offset}: {last_error}"
            )

        batch = response.data or []

        if not batch:
            break

        all_rows.extend(batch)
        offset += page_size

        if len(batch) < page_size:
            break

    return all_rows

# SAVE PUBLICATION
def save_publication(data):
    try:
        response = (
            supabase
            .table(TARGET_TABLE)
            .upsert(data, on_conflict="article_id")
            .execute()
        )
    except Exception:
        response = (
            supabase
            .table(TARGET_TABLE)
            .upsert(data, on_conflict="article_url")
            .execute()
        )

    return response

def _build_minimal_publication(article):
    return {
        "article_id": article.get("id"),
        "article_url": article.get("url"),
        "pdf_url": article.get("pdf_url"),
        "title": normalizer.normalize_title(article.get("title")),
        "authors": normalizer.normalize_authors(article.get("authors")),
        "keywords": [],
        "reference_list": [],
        "doi": None,
        "journal": clean_text(article.get("source")),
        "year": article.get("year"),
        "raw_text": None,
    }

def _build_publication_from_openalex(article, enrichment):
    title = enrichment.get("title") or article.get("title")
    authors = enrichment.get("authors") or article.get("authors")
    year = enrichment.get("year") or article.get("year")
    journal = enrichment.get("journal") or article.get("source")

    return {
        "article_id": article.get("id"),
        "article_url": article.get("url"),
        "pdf_url": article.get("pdf_url"),
        "title": normalizer.normalize_title(title),
        "authors": normalizer.normalize_authors(authors),
        "keywords": normalizer.normalize_keywords(
            enrichment.get("keywords") or []
        ),
        "reference_list": normalizer.normalize_reference(
            enrichment.get("references") or []
        ),
        "doi": normalizer.normalize_doi(
            enrichment.get("doi")
        ),
        "journal": clean_text(journal),
        "year": year,
        "raw_text": (
            (enrichment.get("content") or "")[:50000]
            if enrichment.get("content")
            else None
        ),
    }

def _merge_openalex_missing_fields(publication, enrichment):
    if not enrichment:
        return publication
    if (
        not publication.get("reference_list")
        and enrichment.get("references")
    ):
        publication["reference_list"] = normalizer.normalize_reference(
            enrichment.get("references") or []
        )
    if (
        not publication.get("keywords")
        and enrichment.get("keywords")
    ):
        publication["keywords"] = normalizer.normalize_keywords(
            enrichment.get("keywords") or []
        )
    if (
        not publication.get("doi")
        and enrichment.get("doi")
    ):
        publication["doi"] = normalizer.normalize_doi(
            enrichment.get("doi")
        )

    return publication

# PROCESS ARTICLES
def process_articles():
    articles = get_articles()
    results = []
    total = len(articles)

    for idx, article in enumerate(articles, start=1):
        try:
            source_id = article.get("id")
            url = article.get("url")
            pdf_url = article.get("pdf_url")
            print(f"[{idx}/{total}] Processing source_id={source_id} url={url}")

            content = None
            metadata = None

            # PDF EXTRACTION
            if pdf_url:
                print(
                    f"Processing PDF: {pdf_url}"
                )

                try:
                    pdf_path = download_pdf(
                        pdf_url
                    )
                    content = extract_pdf_content(
                        pdf_path
                    )

                    remove_pdf(pdf_path)

                except Exception as pdf_error:
                    print(
                        "PDF Error:",
                        pdf_error
                    )

            # ARTICLE EXTRACTION
            if not content and url:
                print(
                    f"Processing Article: {url}"
                )
                article_result = extract_article(
                    url
                )
                if article_result:
                    metadata = article_result[
                        "metadata"
                    ]
                    content = article_result[
                        "content"
                    ]

            openalex_enrichment = None

            if not content:
                openalex_enrichment = fetch_openalex_enrichment(article)
                if openalex_enrichment:
                    print(
                        f"OpenAlex enrichment found: {url}"
                    )
                    metadata = (
                        openalex_enrichment.get("metadata")
                        or metadata
                    )
                    content = openalex_enrichment.get("content")

            if not content:
                if openalex_enrichment:
                    publication = _build_publication_from_openalex(
                        article,
                        openalex_enrichment
                    )
                else:
                    publication = _build_minimal_publication(article)
            else:
                publication = build_publication(
                    article,
                    metadata,
                    content,
                    html_keywords=(
                        openalex_enrichment.get("keywords")
                        if openalex_enrichment
                        else None
                    ),
                    html_references=(
                        openalex_enrichment.get("references")
                        if openalex_enrichment
                        else None
                    ),
                    html_doi=(
                        openalex_enrichment.get("doi")
                        if openalex_enrichment
                        else None
                    )
                )

                if (
                    not publication.get("reference_list")
                    or not publication.get("keywords")
                    or not publication.get("doi")
                ):
                    if not openalex_enrichment:
                        openalex_enrichment = fetch_openalex_enrichment(article)
                        if openalex_enrichment:
                            print(
                                f"OpenAlex enrichment (missing fields): {url}"
                            )
                    publication = _merge_openalex_missing_fields(
                        publication,
                        openalex_enrichment
                    )

            try:
                publication = _sanitize_for_postgres(publication)
                save_publication(publication)
            except Exception as save_error:
                results.append({
                    "article_url": article.get("url"),
                    "status": "save_failed",
                    "message": str(save_error),
                })
                continue

            results.append({
                "source_id": source_id,
                "title": publication["title"],
                "status": "saved"
            })

        except Exception as e:
            results.append({
                "source_id": article.get("id"),
                "article_url":
                    article.get("url"),
                "status":
                    "error",
                "message":
                    str(e)
            })

    return results
