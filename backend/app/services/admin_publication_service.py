import json

from app.db import supabase
from app.services.activity_log_service import log_activity
from app.services.doi_lookup_service import DOI_TABLE, load_doi_by_publication_id
from app.services.user_service import _validate_super_admin


PUBLICATIONS_TABLE = "cleaned_papers_results"
PUBLICATION_COLUMNS = (
    "id,url,pdf_url,title,authors,keywords,reference_list,"
    "source,category,year"
)

def _as_list(value):
    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]
    if value in (None, ""):
        return []

    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [
                    str(item).strip()
                    for item in parsed
                    if str(item).strip()
                ]
        except (TypeError, ValueError):
            pass

    return [text]

def _normalize_publication(publication):
    references = _as_list(publication.get("reference_list"))
    keywords = _as_list(publication.get("keywords"))
    metadata_count = sum(
        bool(publication.get(field))
        for field in ("title", "authors", "doi", "source", "year")
    )
    if references and keywords and metadata_count >= 3:
        extraction_status = "complete"
    elif references or keywords or metadata_count >= 2:
        extraction_status = "partial"
    else:
        extraction_status = "empty"

    return {
        "id": publication.get("id"),
        "articleId": publication.get("id"),
        "articleUrl": publication.get("url"),
        "pdfUrl": publication.get("pdf_url"),
        "title": publication.get("title"),
        "authors": _as_list(publication.get("authors")),
        "keywords": keywords,
        "referenceList": references,
        "referenceCount": len(references),
        "doi": publication.get("doi"),
        "journal": publication.get("source"),
        "year": publication.get("year"),
        "category": publication.get("category"),
        "extractionStatus": extraction_status,
        "createdAt": publication.get("created_at"),
    }

# disimpan ke log aktivitas
def _publication_audit_data(publication):
    references = _as_list(publication.get("reference_list"))
    return {
        "id": publication.get("id"),
        "articleId": publication.get("id"),
        "title": publication.get("title"),
        "authors": _as_list(publication.get("authors")),
        "keywords": _as_list(publication.get("keywords")),
        "doi": publication.get("doi"),
        "journal": publication.get("source"),
        "year": publication.get("year"),
        "articleUrl": publication.get("url"),
        "pdfUrl": publication.get("pdf_url"),
        "referenceList": references,
        "referenceCount": len(references),
    }

def _with_doi(publication, doi_by_id):
    result = dict(publication)
    publication_id = result.get("id")
    if publication_id is not None:
        result["doi"] = doi_by_id.get(int(publication_id))
    return result

def get_admin_publications(token):
    auth = _validate_super_admin(token)
    if auth["status"] == "error":
        return auth

    try:
        response = (
            supabase
            .table(PUBLICATIONS_TABLE)
            .select(PUBLICATION_COLUMNS)
            .order("id")
            .execute()
        )
        publication_ids = [
            int(item["id"])
            for item in (response.data or [])
            if item.get("id") is not None
        ]
        doi_by_id = load_doi_by_publication_id(publication_ids)

        publications = [
            _normalize_publication(_with_doi(item, doi_by_id))
            for item in (response.data or [])
        ]

        return {
            "status": "success",
            "total": len(publications),
            "data": publications,
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
            "status_code": 400,
        }

def update_admin_publication(token, publication_id, data):
    auth = _validate_super_admin(token)
    if auth["status"] == "error":
        return auth

    title = str(data.get("title") or "").strip()
    if not title:
        return {
            "status": "error",
            "message": "Judul publikasi wajib diisi.",
            "status_code": 400,
        }

    year = data.get("year")
    if year not in (None, ""):
        try:
            year = int(year)
        except (TypeError, ValueError):
            return {
                "status": "error",
                "message": "Tahun publikasi tidak valid.",
                "status_code": 400,
            }
    else:
        year = None

    payload = {
        "title": title,
        "authors": _as_list(data.get("authors")),
        "keywords": _as_list(data.get("keywords")),
        "reference_list": _as_list(data.get("referenceList")),
        "source": str(data.get("journal") or "").strip() or None,
        "year": year,
        "url": str(data.get("articleUrl") or "").strip() or None,
        "pdf_url": str(data.get("pdfUrl") or "").strip() or None,
    }
    doi = str(data.get("doi") or "").strip() or None

    try:
        current_response = (
            supabase
            .table(PUBLICATIONS_TABLE)
            .select(PUBLICATION_COLUMNS)
            .eq("id", publication_id)
            .single()
            .execute()
        )
        current = current_response.data if current_response else None
        if not current:
            return {
                "status": "error",
                "message": "Publikasi tidak ditemukan.",
                "status_code": 404,
            }

        doi_by_id = load_doi_by_publication_id([publication_id])
        current = _with_doi(current, doi_by_id)

        response = (
            supabase
            .table(PUBLICATIONS_TABLE)
            .update(payload)
            .eq("id", publication_id)
            .execute()
        )
        publication = (response.data or [None])[0]
        if not publication:
            latest = (
                supabase
                .table(PUBLICATIONS_TABLE)
                .select(PUBLICATION_COLUMNS)
                .eq("id", publication_id)
                .single()
                .execute()
            )
            publication = latest.data if latest else None

        if not publication:
            return {
                "status": "error",
                "message": "Publikasi tidak ditemukan.",
                "status_code": 404,
            }
        (
            supabase
            .table(DOI_TABLE)
            .update({"doi": doi})
            .eq("id", publication_id)
            .execute()
        )
        publication = dict(publication)
        publication["doi"] = doi

        normalized_publication = _normalize_publication(publication)
        log_activity(
            actor=auth.get("requester"),
            action="update_publication",
            entity_type="publication",
            entity_id=publication_id,
            description=f"Memperbarui publikasi {title}.",
            old_data=_publication_audit_data(current),
            new_data=_publication_audit_data(publication),
        )

        return {
            "status": "success",
            "message": "Publikasi berhasil diperbarui.",
            "data": normalized_publication,
        }
    except Exception as error:
        log_activity(
            actor=auth.get("requester"),
            action="update_publication",
            entity_type="publication",
            entity_id=publication_id,
            description=f"Gagal memperbarui publikasi ID {publication_id}.",
            status="failed",
        )
        return {
            "status": "error",
            "message": str(error),
            "status_code": 400,
        }

def delete_admin_publication(token, publication_id):
    auth = _validate_super_admin(token)
    if auth["status"] == "error":
        return auth

    try:
        current = (
            supabase
            .table(PUBLICATIONS_TABLE)
            .select(PUBLICATION_COLUMNS)
            .eq("id", publication_id)
            .single()
            .execute()
        )
        if not current or not current.data:
            return {
                "status": "error",
                "message": "Publikasi tidak ditemukan.",
                "status_code": 404,
            }

        doi_by_id = load_doi_by_publication_id([publication_id])
        publication = _with_doi(current.data, doi_by_id)
        (
            supabase
            .table(PUBLICATIONS_TABLE)
            .delete()
            .eq("id", publication_id)
            .execute()
        )

        log_activity(
            actor=auth.get("requester"),
            action="delete_publication",
            entity_type="publication",
            entity_id=publication_id,
            description=f"Menghapus publikasi {current.data.get('title') or publication_id}.",
            old_data=_publication_audit_data(publication),
        )

        return {
            "status": "success",
            "message": "Publikasi berhasil dihapus.",
            "data": _normalize_publication(publication),
        }
    except Exception as error:
        log_activity(
            actor=auth.get("requester"),
            action="delete_publication",
            entity_type="publication",
            entity_id=publication_id,
            description=f"Gagal menghapus publikasi ID {publication_id}.",
            status="failed",
        )
        return {
            "status": "error",
            "message": str(error),
            "status_code": 400,
        }
