from app.db import supabase
from app.services.activity.activity_log_service import log_activity
from app.services.user_service import _validate_super_admin


PUBLICATION_COLUMNS = (
    "id,article_id,article_url,pdf_url,title,authors,keywords,"
    "reference_list,doi,journal,year,created_at"
)


def _as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _normalize_publication(publication, category=None):
    references = _as_list(publication.get("reference_list"))
    keywords = _as_list(publication.get("keywords"))
    metadata_count = sum(
        bool(publication.get(field))
        for field in ("title", "authors", "doi", "journal", "year")
    )
    if references and keywords and metadata_count >= 3:
        extraction_status = "complete"
    elif references or keywords or metadata_count >= 2:
        extraction_status = "partial"
    else:
        extraction_status = "empty"

    return {
        "id": publication.get("id"),
        "articleId": publication.get("article_id"),
        "articleUrl": publication.get("article_url"),
        "pdfUrl": publication.get("pdf_url"),
        "title": publication.get("title"),
        "authors": _as_list(publication.get("authors")),
        "keywords": keywords,
        "referenceList": references,
        "referenceCount": len(references),
        "doi": publication.get("doi"),
        "journal": publication.get("journal"),
        "year": publication.get("year"),
        "category": category,
        "extractionStatus": extraction_status,
        "createdAt": publication.get("created_at"),
    }


def _publication_audit_data(publication):
    references = _as_list(publication.get("reference_list"))
    return {
        "id": publication.get("id"),
        "articleId": publication.get("article_id"),
        "title": publication.get("title"),
        "authors": _as_list(publication.get("authors")),
        "keywords": _as_list(publication.get("keywords")),
        "doi": publication.get("doi"),
        "journal": publication.get("journal"),
        "year": publication.get("year"),
        "articleUrl": publication.get("article_url"),
        "pdfUrl": publication.get("pdf_url"),
        "referenceCount": len(references),
    }


def get_admin_publications(token):
    auth = _validate_super_admin(token)
    if auth["status"] == "error":
        return auth

    try:
        response = (
            supabase
            .table("publications")
            .select(PUBLICATION_COLUMNS)
            .order("id")
            .execute()
        )

        article_ids = [
            item.get("article_id")
            for item in (response.data or [])
            if item.get("article_id") is not None
        ]
        category_by_article_id = {}
        if article_ids:
            category_response = (
                supabase
                .table("scholar_articles")
                .select("id,category")
                .in_("id", article_ids)
                .execute()
            )
            category_by_article_id = {
                item.get("id"): item.get("category")
                for item in (category_response.data or [])
            }

        publications = [
            _normalize_publication(
                item,
                category_by_article_id.get(item.get("article_id")),
            )
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
        "doi": str(data.get("doi") or "").strip() or None,
        "journal": str(data.get("journal") or "").strip() or None,
        "year": year,
        "article_url": str(data.get("articleUrl") or "").strip() or None,
        "pdf_url": str(data.get("pdfUrl") or "").strip() or None,
    }

    try:
        current_response = (
            supabase
            .table("publications")
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

        response = (
            supabase
            .table("publications")
            .update(payload)
            .eq("id", publication_id)
            .execute()
        )
        publication = (response.data or [None])[0]
        if not publication:
            latest = (
                supabase
                .table("publications")
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
            .table("publications")
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

        supabase.table("publications").delete().eq("id", publication_id).execute()

        log_activity(
            actor=auth.get("requester"),
            action="delete_publication",
            entity_type="publication",
            entity_id=publication_id,
            description=f"Menghapus publikasi {current.data.get('title') or publication_id}.",
            old_data=_publication_audit_data(current.data),
        )

        return {
            "status": "success",
            "message": "Publikasi berhasil dihapus.",
            "data": _normalize_publication(current.data),
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
