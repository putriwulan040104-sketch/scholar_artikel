import time
import re
import threading
from datetime import datetime, timezone
from app.db import supabase
from app.models.publication_model import build_publication
from app.services.extraction.article_service import extract_article
from app.services.extraction.openalex_service import (
    fetch_openalex_enrichment,
    fetch_openalex_references_by_doi,
)
from app.services.extraction.pdf_service import (
    download_pdf,
    extract_pdf_content,
    remove_pdf,
)

SOURCE_TABLE = "scholar_article_doi"
TARGET_TABLE = "cleaned_papers_results"
SOURCE_COLUMNS = "id,title,doi,url,pdf_url,authors"
MIN_KEYWORDS_BEFORE_HTML_CHECK = 3
MIN_REFERENCE_SCORE_BEFORE_ALTERNATE_CHECK = 75

NON_REFERENCE_PHRASES = (
    "abstract",
    "introduction",
    "creative commons",
    "article views",
    "usage metrics",
    "data extraction and quality assessment",
    "inclusion criteria",
    "methodology",
    "results and discussion",
)
_REFERENCE_REPAIR_LOCK = threading.Lock()

class ReferenceRepairInProgressError(RuntimeError):
    pass

def _sanitize_for_postgres(value):
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [_sanitize_for_postgres(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _sanitize_for_postgres(item)
            for key, item in value.items()
        }
    return value

def _merge_keywords(*keyword_lists):
    merged = []
    seen = set()

    for keywords in keyword_lists:
        for keyword in keywords or []:
            value = str(keyword).strip()
            if not value:
                continue

            key = value.lower()
            if key in seen:
                continue

            seen.add(key)
            merged.append(value)

    return merged

def analyze_reference_quality(references):
    if not isinstance(references, list) or not references:
        return {
            "valid": False,
            "score": 0,
            "count": 0,
            "reasons": ["empty"],
        }

    cleaned = [
        re.sub(r"\s+", " ", str(reference)).strip()
        for reference in references
        if str(reference).strip()
    ]
    if not cleaned:
        return {
            "valid": False,
            "score": 0,
            "count": 0,
            "reasons": ["empty"],
        }

    citation_like = 0
    phrase_hits = 0
    very_long = 0
    numbered = 0

    for reference in cleaned:
        lower = reference.lower()
        if (
            re.search(r"\b(19|20)\d{2}\b", reference)
            or re.search(r"\b10\.\d{4,9}/", reference, re.I)
            or "http://" in lower
            or "https://" in lower
            or re.match(
                r"^\s*(?:\[\d{1,3}\]|\(\d{1,3}\)|\d{1,3}[.)])\s*",
                reference,
            )
        ):
            citation_like += 1

        if any(phrase in lower for phrase in NON_REFERENCE_PHRASES):
            phrase_hits += 1
        if len(reference) > 2000:
            very_long += 1
        if re.match(r"^\s*\d{1,3}[.)]\s+", reference):
            numbered += 1

    count = len(cleaned)
    citation_ratio = citation_like / count
    reasons = []
    if count == 1:
        reasons.append("single_entry")
    if phrase_hits:
        reasons.append(f"non_reference_text:{phrase_hits}")
    if very_long:
        reasons.append(f"very_long_entry:{very_long}")
    if citation_ratio < 0.5:
        reasons.append(
            f"low_citation_ratio:{citation_like}/{count}"
        )

    score = min(count, 50) * 2
    score += round(citation_ratio * 50)
    score += min(numbered, 20)
    score -= phrase_hits * 15
    score -= very_long * 20
    if count == 1:
        score -= 25

    valid = (
        count >= 2
        and citation_ratio >= 0.5
        and very_long == 0
        and (
            phrase_hits <= max(1, count // 10)
            or citation_ratio >= 0.9
        )
    )
    return {
        "valid": valid,
        "score": max(0, score),
        "count": count,
        "reasons": reasons,
    }

def _pick_better_references(current_references, candidate_references):
    current_references = current_references or []
    candidate_references = candidate_references or []

    if not candidate_references:
        return current_references
    if not current_references:
        return candidate_references

    current_quality = analyze_reference_quality(current_references)
    candidate_quality = analyze_reference_quality(candidate_references)

    if not candidate_quality["valid"]:
        return current_references
    if not current_quality["valid"]:
        return candidate_references
    if candidate_quality["score"] > current_quality["score"]:
        return candidate_references
    if (
        candidate_quality["score"] == current_quality["score"]
        and candidate_quality["count"] > current_quality["count"]
    ):
        return candidate_references

    return current_references

def _needs_reference_enrichment(references):
    quality = analyze_reference_quality(references or [])
    return (
        not quality["valid"]
        or quality["score"] < MIN_REFERENCE_SCORE_BEFORE_ALTERNATE_CHECK
    )

def get_articles(source_ids=None):
    if source_ids:
        response = (
            supabase
            .table(SOURCE_TABLE)
            .select(SOURCE_COLUMNS)
            .in_("id", sorted({int(source_id) for source_id in source_ids}))
            .order("id")
            .execute()
        )
        return response.data or []

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
                    .select(SOURCE_COLUMNS)
                    .order("id")
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                last_error = None
                break
            except Exception as error:
                last_error = error
                print(
                    f"[WARN] get_articles retry {attempt}/{max_retries} "
                    f"offset={offset}: {error}"
                )
                time.sleep(attempt * 2)

        if last_error is not None:
            raise RuntimeError(
                f"Gagal mengambil {SOURCE_TABLE} pada offset={offset}: "
                f"{last_error}"
            )

        batch = response.data or []
        if not batch:
            break

        all_rows.extend(batch)
        offset += page_size
        if len(batch) < page_size:
            break

    return all_rows

def _ensure_target_columns():
    try:
        (
            supabase
            .table(TARGET_TABLE)
            .select("id,keywords,reference_list")
            .limit(1)
            .execute()
        )
    except Exception as error:
        message = str(error).lower()
        if "keywords" in message or "reference_list" in message:
            raise RuntimeError(
                "Kolom keywords/reference_list belum tersedia di "
                f"{TARGET_TABLE}. Jalankan SQL "
                "backend/sql/add_extraction_fields_to_cleaned_papers.sql "
                "melalui Supabase SQL Editor."
            ) from error
        raise

def save_publication(extraction_result):
    source_id = extraction_result.get("source_id")
    if source_id is None:
        raise ValueError("source_id hasil ekstraksi tidak tersedia")

    payload = {
        "keywords": _sanitize_for_postgres(
            extraction_result.get("keywords") or []
        ),
        "reference_list": _sanitize_for_postgres(
            extraction_result.get("reference_list") or []
        ),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    keywords = extraction_result.get("keywords") or []
    references = extraction_result.get("reference_list") or []

    print(
        "[EXTRACTION][SAVE] "
        f"source_id={source_id} "
        f"keywords={len(keywords)} "
        f"references={len(references)} "
        "source=pdf/html",
        flush=True,
    )

    response = (
        supabase
        .table(TARGET_TABLE)
        .update(payload)
        .eq("id", source_id)
        .execute()
    )

    if not response.data:
        existing = (
            supabase
            .table(TARGET_TABLE)
            .select("id")
            .eq("id", source_id)
            .limit(1)
            .execute()
        )
        if not existing.data:
            raise ValueError(
                f"Data target ID {source_id} tidak ditemukan di {TARGET_TABLE}"
            )

    return response

def _extract_article_fields(article):
    content = None
    article_result = None
    declared_keywords = []
    attempted_pdf_urls = set()
    attempted_article_urls = set()
    non_pdf_urls = set()
    pdf_url = article.get("pdf_url")
    article_url = article.get("url")
    doi_url = (
        f"https://doi.org/{article['doi']}"
        if article.get("doi")
        else None
    )

    def looks_like_pdf_url(url):
        url = str(url or "").lower()
        return (
            ".pdf" in url
            or "/pdf/" in url
            or "/doi/pdf/" in url
            or "/servlets/purl/" in url
        )

    def is_non_pdf_error(error):
        return "URL tidak mengembalikan berkas PDF" in str(error)

    def try_pdf(url, label, timeout=20, max_duration=25):
        if not url or url in attempted_pdf_urls:
            return None
        attempted_pdf_urls.add(url)
        print(f"{label}: {url}")
        pdf_path = None
        try:
            pdf_path = download_pdf(
                url,
                timeout=timeout,
                max_duration=max_duration,
            )
            return extract_pdf_content(pdf_path)
        except Exception as error:
            if is_non_pdf_error(error):
                non_pdf_urls.add(url)
            print(f"{label} Error: {error}")
            return None
        finally:
            if pdf_path:
                remove_pdf(pdf_path)

    def try_article(url, label, timeout=25):
        if not url or url in attempted_article_urls:
            return None
        attempted_article_urls.add(url)
        print(f"{label}: {url}")
        return extract_article(url, timeout=timeout)

    if pdf_url:
        content = try_pdf(
            pdf_url,
            "Processing PDF",
            timeout=15,
            max_duration=20,
        )
        if not content and pdf_url in non_pdf_urls:
            article_result = try_article(
                pdf_url,
                "Processing PDF URL as Article",
                timeout=25,
            )
            if article_result:
                declared_keywords = article_result.get("keywords") or []
                content = article_result.get("content")

    if not content and doi_url and str(article.get("doi") or "").lower().endswith(".pdf"):
        content = try_pdf(
            doi_url,
            "Processing PDF via DOI",
            timeout=15,
            max_duration=20,
        )
        if not content and doi_url in non_pdf_urls:
            article_result = try_article(
                doi_url,
                "Processing DOI PDF URL as Article",
                timeout=20,
            )
            if article_result:
                declared_keywords = _merge_keywords(
                    declared_keywords,
                    article_result.get("keywords") or [],
                )
                content = article_result.get("content")

    result = build_publication(
        article,
        content or "",
        declared_keywords=declared_keywords,
    )

    if len(result["keywords"]) < MIN_KEYWORDS_BEFORE_HTML_CHECK and article_url:
        article_result = try_article(
            article_url,
            "Processing Article Keywords",
            timeout=25,
        )
        if article_result:
            declared_keywords = article_result.get("keywords") or []
            if not content:
                content = article_result.get("content")
            result = build_publication(
                article,
                content or article_result.get("content") or "",
                declared_keywords=declared_keywords,
            )
            result["keywords"] = _merge_keywords(
                result["keywords"],
                declared_keywords,
            )
    if (
        len(result["keywords"]) < MIN_KEYWORDS_BEFORE_HTML_CHECK
        and doi_url
        and article_result is None
    ):
        doi_result = try_article(
            doi_url,
            "Processing DOI Keywords",
            timeout=20,
        )
        if doi_result:
            declared_keywords = doi_result.get("keywords") or []
            if not content:
                content = doi_result.get("content")
            result = build_publication(
                article,
                content or doi_result.get("content") or "",
                declared_keywords=declared_keywords,
            )
            result["keywords"] = _merge_keywords(
                result["keywords"],
                declared_keywords,
            )

    location_enrichment = None
    if (
        len(result["keywords"]) < MIN_KEYWORDS_BEFORE_HTML_CHECK
        or _needs_reference_enrichment(result["reference_list"])
    ):
        location_enrichment = fetch_openalex_enrichment(
            article,
        )
    if (
        len(result["keywords"]) < MIN_KEYWORDS_BEFORE_HTML_CHECK
        or _needs_reference_enrichment(result["reference_list"])
    ):
        max_alternates = 2
        tried_alternates = 0
        for document_url in (
            location_enrichment or {}
        ).get("document_urls") or []:
            if (
                not document_url
                or (
                    document_url in attempted_pdf_urls
                    and document_url in attempted_article_urls
                )
            ):
                continue
            if tried_alternates >= max_alternates:
                break
            tried_alternates += 1
            alternate_content = None
            alternate_keywords = []
            if looks_like_pdf_url(document_url):
                alternate_content = try_pdf(
                    document_url,
                    "Processing Alternate PDF",
                    timeout=12,
                    max_duration=12,
                )
                if not alternate_content and document_url in non_pdf_urls:
                    alternate_result = try_article(
                        document_url,
                        "Processing Alternate PDF URL as Article",
                        timeout=12,
                    )
                    if alternate_result:
                        alternate_content = alternate_result.get("content")
                        alternate_keywords = (
                            alternate_result.get("keywords") or []
                        )
            else:
                alternate_result = try_article(
                    document_url,
                    "Processing Alternate Article",
                    timeout=12,
                )
                if alternate_result:
                    alternate_content = alternate_result.get("content")
                    alternate_keywords = (
                        alternate_result.get("keywords") or []
                    )

            alternate_publication = build_publication(
                article,
                alternate_content or "",
                declared_keywords=alternate_keywords,
            )
            if (
                len(result["keywords"]) < MIN_KEYWORDS_BEFORE_HTML_CHECK
                and alternate_publication["keywords"]
            ):
                declared_keywords = _merge_keywords(
                    declared_keywords,
                    alternate_publication["keywords"],
                )
                result["keywords"] = _merge_keywords(
                    result["keywords"],
                    alternate_publication["keywords"],
                )
            if (
                alternate_publication["reference_list"]
            ):
                result["reference_list"] = _pick_better_references(
                    result["reference_list"],
                    alternate_publication["reference_list"]
                )
            if (
                len(result["keywords"]) >= MIN_KEYWORDS_BEFORE_HTML_CHECK
                and not _needs_reference_enrichment(result["reference_list"])
            ):
                break

    if _needs_reference_enrichment(result["reference_list"]):
        openalex_references = fetch_openalex_references_by_doi(article)
        if openalex_references:
            print(
                "OpenAlex DOI references fallback "
                f"source_id={article.get('id')} "
                f"count={len(openalex_references)}",
                flush=True,
            )
            result["reference_list"] = _pick_better_references(
                result["reference_list"],
                openalex_references,
            )

    return result

def process_articles(source_ids=None):
    _ensure_target_columns()
    articles = get_articles(source_ids=source_ids)
    results = []
    total = len(articles)

    for index, article in enumerate(articles, start=1):
        source_id = article.get("id")
        print(
            f"[{index}/{total}] Extracting source_id={source_id} "
            f"title={article.get('title') or '-'}"
        )

        try:
            extraction_result = _extract_article_fields(article)
            save_publication(extraction_result)

            keywords_count = len(extraction_result.get("keywords") or [])
            references_count = len(
                extraction_result.get("reference_list") or []
            )
            results.append({
                "source_id": source_id,
                "status": "saved",
                "keywords_count": keywords_count,
                "references_count": references_count,
            })
            print(
                f"  Saved: keywords={keywords_count}, "
                f"references={references_count}"
            )
        except Exception as error:
            results.append({
                "source_id": source_id,
                "article_url": article.get("url"),
                "status": "error",
                "message": str(error),
            })
            print(f"  Extraction Error: {error}")

    return results

def audit_reference_data():
    rows = []
    page_size = 100
    offset = 0

    while True:
        response = (
            supabase
            .table(TARGET_TABLE)
            .select("id,title,reference_list,pdf_url,url")
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

    issues = []
    for row in rows:
        quality = analyze_reference_quality(
            row.get("reference_list") or []
        )
        if quality["valid"]:
            continue
        issues.append({
            "source_id": row.get("id"),
            "title": row.get("title"),
            "reference_count": quality["count"],
            "quality_score": quality["score"],
            "reasons": quality["reasons"],
            "has_pdf_url": bool(row.get("pdf_url")),
            "has_article_url": bool(row.get("url")),
        })

    return {
        "total_publications": len(rows),
        "valid_references": len(rows) - len(issues),
        "problematic_references": len(issues),
        "issues": issues,
    }

def _repair_reference_data(source_ids=None, limit=None):
    audit = audit_reference_data()
    issue_ids = {
        int(item["source_id"])
        for item in audit["issues"]
        if item.get("source_id") is not None
    }
    if source_ids:
        requested_ids = {
            int(source_id)
            for source_id in source_ids
        }
        issue_ids &= requested_ids

    ordered_ids = sorted(issue_ids)
    if limit:
        ordered_ids = ordered_ids[:max(1, int(limit))]

    source_rows = {
        int(row["id"]): row
        for row in get_articles()
        if row.get("id") is not None
        and int(row["id"]) in issue_ids
    }
    results = []
    total = len(ordered_ids)

    for index, source_id in enumerate(ordered_ids, start=1):
        article = source_rows.get(source_id)
        if not article:
            results.append({
                "source_id": source_id,
                "status": "source_not_found",
            })
            continue

        current = (
            supabase
            .table(TARGET_TABLE)
            .select("reference_list")
            .eq("id", source_id)
            .single()
            .execute()
            .data
            or {}
        )
        current_quality = analyze_reference_quality(
            current.get("reference_list") or []
        )
        print(
            f"[REFERENCE][{index}/{total}] Repairing "
            f"source_id={source_id} "
            f"current_score={current_quality['score']}",
            flush=True,
        )

        try:
            extraction_result = _extract_article_fields(article)
            candidate = extraction_result.get("reference_list") or []
            candidate_quality = analyze_reference_quality(candidate)
            improved = (
                candidate_quality["valid"]
                and candidate_quality["score"] > current_quality["score"]
            )

            if improved:
                (
                    supabase
                    .table(TARGET_TABLE)
                    .update({
                        "reference_list": _sanitize_for_postgres(candidate),
                        "updated_at": datetime.now(
                            timezone.utc
                        ).isoformat(),
                    })
                    .eq("id", source_id)
                    .execute()
                )

            status = "updated" if improved else "not_improved"
            print(
                f"[REFERENCE] {status} source_id={source_id} "
                f"candidate_count={candidate_quality['count']} "
                f"candidate_score={candidate_quality['score']}",
                flush=True,
            )
            results.append({
                "source_id": source_id,
                "status": status,
                "old_quality": current_quality,
                "new_quality": candidate_quality,
            })
        except Exception as error:
            print(
                f"[REFERENCE][ERROR] source_id={source_id}: {error}",
                flush=True,
            )
            results.append({
                "source_id": source_id,
                "status": "error",
                "message": str(error),
            })

    return {
        "selected": total,
        "updated": sum(
            item["status"] == "updated"
            for item in results
        ),
        "not_improved": sum(
            item["status"] == "not_improved"
            for item in results
        ),
        "errors": sum(
            item["status"] == "error"
            for item in results
        ),
        "results": results,
    }

def repair_reference_data(source_ids=None, limit=None):
    if not _REFERENCE_REPAIR_LOCK.acquire(blocking=False):
        raise ReferenceRepairInProgressError(
            "Proses repair reference sedang berjalan"
        )

    try:
        return _repair_reference_data(
            source_ids=source_ids,
            limit=limit,
        )
    finally:
        _REFERENCE_REPAIR_LOCK.release()
