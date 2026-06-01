import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from supabase import create_client, Client

request_bp = Blueprint("request_bp", __name__)


def get_supabase() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    # fallback supaya tetap jalan jika env lama masih SUPABASE_KEY
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
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        supabase = get_supabase()
        supabase.table("article_requests").insert(payload).execute()
        send_dev_email(payload)

        return jsonify({"status": "success", "message": "pesan email terkirim"}), 200

    except Exception as e:
        return jsonify(
            {"status": "error", "message": f"Gagal mengirim permintaan: {str(e)}"}
        ), 500