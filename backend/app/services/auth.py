import os
import bcrypt
import jwt
import datetime
from app.db import supabase

SECRET_KEY = os.getenv("SECRET_KEY")

def register_user(name, email, password):
    try:
        existing = supabase.table("users").select("id").eq("email", email).execute()
        if existing.data:
            return {
                "status": "error",
                "message": "Email sudah terdaftar"
            }
        
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        response = supabase.table("users").insert({
            "name": name,
            "email": email,
            "password": hashed
        }).execute()

        # Versi postgrest tertentu tidak mendukung chaining .select() setelah insert,
        # jadi lakukan fetch terpisah.
        user = None
        if response.data:
            user = response.data[0]
        if not user:
            latest = (
                supabase
                .table("users")
                .select("id, name, email, avatar_url")
                .eq("email", email)
                .single()
                .execute()
            )
            user = latest.data if latest else None

        if not user:
            return {
                "status": "error",
                "message": "Gagal mengambil data user setelah register"
            }
        return {
            "status": "success",
            "data": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "avatarUrl": user.get("avatar_url"),
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def login_user(email, password):
    try:
        response = supabase.table("users").select("*").eq("email", email).execute()

        if not response.data:
            return {
                "status": "error",
                "message": "Email atau password salah"
            }

        user = response.data[0]

        is_valid = bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8"))
        if not is_valid:
            return {
                "status": "error",
                "message": "Email atau password salah"
            }
        
        token = jwt.encode({
            "user_id": user["id"],
            "email": user["email"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, SECRET_KEY, algorithm="HS256")

        return {
            "status": "success",
            "token": token,
            "data": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "avatarUrl": user.get("avatar_url"),
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def _decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return {"_token_error": "Token sudah kedaluwarsa"}
    except Exception:
        return None


def update_profile_user(token, name=None, email=None, avatar_url=None):
    payload = _decode_token(token)
    if not payload:
        return {
            "status": "error",
            "message": "Token tidak valid"
        }
    if isinstance(payload, dict) and payload.get("_token_error"):
        return {
            "status": "error",
            "message": payload["_token_error"]
        }

    user_id = payload.get("user_id")
    if not user_id:
        return {
            "status": "error",
            "message": "User pada token tidak ditemukan"
        }

    try:
        existing_response = (
            supabase
            .table("users")
            .select("id, name, email, avatar_url")
            .eq("id", user_id)
            .execute()
        )

        if not existing_response.data:
            return {
                "status": "error",
                "message": "User tidak ditemukan"
            }

        current_user = existing_response.data[0]
        next_name = (name or "").strip() if isinstance(name, str) else current_user.get("name")
        next_email = (email or "").strip() if isinstance(email, str) else current_user.get("email")

        if not next_name or not next_email:
            return {
                "status": "error",
                "message": "Nama dan email wajib diisi"
            }

        # Cegah duplicate email antar user.
        if next_email != current_user.get("email"):
            email_check = (
                supabase
                .table("users")
                .select("id")
                .eq("email", next_email)
                .neq("id", user_id)
                .execute()
            )
            if email_check.data:
                return {
                    "status": "error",
                    "message": "Email sudah digunakan akun lain"
                }

        update_payload = {
            "name": next_name,
            "email": next_email,
        }

        # Coba simpan avatar_url jika kolom tersedia.
        if isinstance(avatar_url, str):
            update_payload["avatar_url"] = avatar_url

        try:
            update_response = (
                supabase
                .table("users")
                .update(update_payload)
                .eq("id", user_id)
                .execute()
            )
        except Exception as update_error:
            # Fallback saat kolom avatar_url belum ada di DB.
            if "avatar_url" in update_payload:
                update_payload.pop("avatar_url", None)
                update_response = (
                    supabase
                    .table("users")
                    .update(update_payload)
                    .eq("id", user_id)
                    .execute()
                )
            else:
                raise update_error

        user = (update_response.data or [None])[0]
        if not user:
            # Beberapa konfigurasi PostgREST bisa return kosong;
            # lakukan re-fetch untuk memastikan update berhasil.
            latest = (
                supabase
                .table("users")
                .select("id, name, email, avatar_url")
                .eq("id", user_id)
                .single()
                .execute()
            )
            user = latest.data if latest else None

        if not user:
            return {
                "status": "error",
                "message": "Gagal memperbarui profile"
            }

        return {
            "status": "success",
            "data": {
                "id": user.get("id"),
                "name": user.get("name"),
                "email": user.get("email"),
                "avatarUrl": user.get("avatar_url"),
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
