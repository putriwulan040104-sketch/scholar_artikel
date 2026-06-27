import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from supabase import create_client, Client
from app.services.user_service import _validate_super_admin
from backend.app.services.activity_log_service import log_activity

request_bp = Blueprint("request_bp", __name__)

ARTICLE_REQUEST_TABLES = ["article_requests", "article_requests"]
REQUEST_STATUSES = {"pending", "processing", "done", "rejected"}

def get_supabase() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url:
        raise ValueError("SUPABASE_URL belum di-set di .env")
    if not supabase_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY atau SUPABASE_KEY belum di-set di .env")

    return create_client(supabase_url, supabase_key)

def send_dev_email(payload: dict) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    mail_from = os.getenv("MAIL_FROM", smtp_user)
    mail_to = os.getenv("MAIL_TO")

    if not smtp_host or not smtp_user or not smtp_pass or not mail_to:
        raise ValueError("Konfigurasi SMTP belum lengkap (SMTP_HOST/SMTP_USER/SMTP_PASS/MAIL_TO).")

    msg = EmailMessage()
    msg["Subject"] = f"Request Artikel Baru - {payload['kata_kunci']}"
    msg["From"] = mail_from
    msg["To"] = mail_to

    msg.set_content(
        f"""Ada request artikel baru:

        Nama: {payload['nama']}
        Email: {payload['email']}
        Kata Kunci: {payload['kata_kunci']}
        Judul Artikel: {payload.get('judul_artikel') or '-'}
        Keterangan: {payload.get('keterangan_tambahan') or '-'}
        Dikirim pada: {payload['created_at']}
        """
    )

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

def _normalize_request(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "nama": row.get("nama"),
        "email": row.get("email"),
        "kataKunci": row.get("kata_kunci"),
        "judulArtikel": row.get("judul_artikel"),
        "keterangan": row.get("keterangan_tambahan"),
        "status": row.get("status") or "pending",
        "createdAt": row.get("created_at"),
        "updatedAt": row.get("updated_at"),
    }

def _execute_on_request_table(action):
    supabase = get_supabase()
    last_error = None

    for table_name in ARTICLE_REQUEST_TABLES:
        try:
            return action(supabase.table(table_name)), table_name
        except Exception as error:
            last_error = error

    raise last_error

def _get_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    return auth_header.replace("Bearer ", "", 1).strip()

@request_bp.route("/request-article", methods=["POST"])
def request_article():
    try:
        body = request.get_json(force=True)

        nama = (body.get("nama") or "").strip()
        email = (body.get("email") or "").strip()
        kata_kunci = (body.get("kataKunci") or "").strip()
        judul_artikel = (body.get("judulArtikel") or "").strip()
        keterangan_tambahan = (body.get("keterangan") or "").strip()

        if not nama or not email or not kata_kunci:
            return jsonify(
                {
                    "status": "error",
                    "message": "Nama, email, dan kata kunci wajib diisi.",
                }
            ), 400

        payload = {
            "nama": nama,
            "email": email,
            "kata_kunci": kata_kunci,
            "judul_artikel": judul_artikel or None,
            "keterangan_tambahan": keterangan_tambahan or None,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            _execute_on_request_table(lambda table: table.insert(payload).execute())
        except Exception:
            payload.pop("status", None)
            _execute_on_request_table(lambda table: table.insert(payload).execute())

        send_dev_email(payload)

        return jsonify({"status": "success", "message": "pesan email terkirim"}), 200

    except Exception as e:
        return jsonify(
            {"status": "error", "message": f"Gagal mengirim permintaan: {str(e)}"}
        ), 500

@request_bp.route("/article-requests", methods=["GET"])
def list_article_requests():
    token = _get_token()
    if not token:
        return jsonify({
            "status": "error",
            "message": "Token tidak ditemukan",
        }), 401

    auth = _validate_super_admin(token)
    if auth["status"] == "error":
        status_code = auth.pop("status_code", 400)
        return jsonify(auth), status_code

    try:
        response, _table_name = _execute_on_request_table(
            lambda table: table
            .select("id, nama, email, kata_kunci, judul_artikel, keterangan_tambahan, status, created_at, updated_at")
            .order("created_at", desc=True)
            .execute()
        )

        items = [_normalize_request(row) for row in (response.data or [])]
        return jsonify({
            "status": "success",
            "total": len(items),
            "data": items,
        }), 200
    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error),
        }), 400

@request_bp.route("/article-requests/<request_id>/status", methods=["PUT"])
def update_article_request_status(request_id):
    token = _get_token()
    if not token:
        return jsonify({
            "status": "error",
            "message": "Token tidak ditemukan",
        }), 401

    auth = _validate_super_admin(token)
    if auth["status"] == "error":
        status_code = auth.pop("status_code", 400)
        return jsonify(auth), status_code

    body = request.json or {}
    next_status = (body.get("status") or "").strip().lower()

    if next_status not in REQUEST_STATUSES:
        return jsonify({
            "status": "error",
            "message": "Status tidak valid.",
        }), 400

    try:
        current_response, _current_table = _execute_on_request_table(
            lambda table: table
            .select(
                "id, nama, email, kata_kunci, judul_artikel, "
                "keterangan_tambahan, status, created_at, updated_at"
            )
            .eq("id", request_id)
            .single()
            .execute()
        )
        current = current_response.data if current_response else None
        if not current:
            return jsonify({
                "status": "error",
                "message": "Request artikel tidak ditemukan.",
            }), 404

        response, _table_name = _execute_on_request_table(
            lambda table: table
            .update({
                "status": next_status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", request_id)
            .execute()
        )

        item = (response.data or [None])[0]
        normalized_item = _normalize_request(item or {})
        log_activity(
            actor=auth.get("requester"),
            action="update_request_status",
            entity_type="article_request",
            entity_id=request_id,
            description=(
                f"Mengubah status request {current.get('kata_kunci') or request_id} "
                f"dari {current.get('status') or 'pending'} menjadi {next_status}."
            ),
            old_data=_normalize_request(current),
            new_data=normalized_item,
        )
        return jsonify({
            "status": "success",
            "message": "Status request berhasil diperbarui.",
            "data": normalized_item,
        }), 200
    except Exception as error:
        log_activity(
            actor=auth.get("requester"),
            action="update_request_status",
            entity_type="article_request",
            entity_id=request_id,
            description=f"Gagal mengubah status request ID {request_id}.",
            new_data={"status": next_status},
            status="failed",
        )
        return jsonify({
            "status": "error",
            "message": str(error),
        }), 400
