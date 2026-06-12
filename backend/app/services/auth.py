import os
import jwt
import datetime
from app.db import supabase
from app.services.activity.activity_log_service import log_activity
from app.utils.hash import hash_password, verify_password

SECRET_KEY = os.getenv("SECRET_KEY")


def _user_payload(user):
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "email": user.get("email"),
        "avatarUrl": user.get("avatar_url"),
        "role": user.get("role") or "user",
    }


def register_user(name, email, password):
    try:
        existing = supabase.table("users").select("id").eq("email", email).execute()
        if existing.data:
            log_activity(
                action="register",
                entity_type="user",
                description=f"Registrasi gagal untuk {email}: email sudah terdaftar.",
                new_data={"name": name, "email": email},
                status="failed",
                user_name=email,
            )
            return {
                "status": "error",
                "message": "Email sudah terdaftar"
            }
        
        hashed = hash_password(password)

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
                .select("id, name, email, avatar_url, role")
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
        normalized_user = _user_payload(user)
        log_activity(
            actor=user,
            action="register",
            entity_type="user",
            entity_id=user.get("id"),
            description=f"Akun {user.get('name') or email} berhasil didaftarkan.",
            new_data=normalized_user,
        )
        return {
            "status": "success",
            "data": normalized_user
        }
    except Exception as e:
        log_activity(
            action="register",
            entity_type="user",
            description=f"Registrasi gagal untuk {email}.",
            new_data={"name": name, "email": email},
            status="failed",
            user_name=email,
        )
        return {
            "status": "error",
            "message": str(e)
        }

def login_user(email, password):
    try:
        response = supabase.table("users").select("*").eq("email", email).execute()

        if not response.data:
            log_activity(
                action="login",
                entity_type="auth",
                description=f"Login gagal untuk {email}.",
                status="failed",
                user_name=email,
            )
            return {
                "status": "error",
                "message": "Email atau password salah"
            }

        user = response.data[0]

        is_valid = verify_password(password, user["password"])
        if not is_valid:
            log_activity(
                actor=user,
                action="login",
                entity_type="auth",
                entity_id=user.get("id"),
                description=f"Login gagal untuk {email}.",
                status="failed",
            )
            return {
                "status": "error",
                "message": "Email atau password salah"
            }
        
        token = jwt.encode({
            "user_id": user["id"],
            "email": user["email"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, SECRET_KEY, algorithm="HS256")

        log_activity(
            actor=user,
            action="login",
            entity_type="auth",
            entity_id=user.get("id"),
            description=f"{user.get('name') or email} berhasil login.",
        )
        return {
            "status": "success",
            "token": token,
            "data": _user_payload(user)
        }
    except Exception as e:
        log_activity(
            action="login",
            entity_type="auth",
            description=f"Login gagal untuk {email}.",
            status="failed",
            user_name=email,
        )
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
            .select("id, name, email, avatar_url, role")
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
            # lakukan re-fetch untuk memastikan update berhasil.
            latest = (
                supabase
                .table("users")
                .select("id, name, email, avatar_url, role")
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

        normalized_user = _user_payload(user)
        log_activity(
            actor=current_user,
            action="update_profile",
            entity_type="user",
            entity_id=user_id,
            description=f"{normalized_user.get('name') or user_id} memperbarui profil.",
            old_data=_user_payload(current_user),
            new_data=normalized_user,
        )
        return {
            "status": "success",
            "data": normalized_user
        }
    except Exception as e:
        log_activity(
            actor={"id": user_id, "email": payload.get("email")},
            action="update_profile",
            entity_type="user",
            entity_id=user_id,
            description=f"Gagal memperbarui profil user ID {user_id}.",
            status="failed",
        )
        return {
            "status": "error",
            "message": str(e)
        }


def logout_user(token):
    payload = _decode_token(token)
    if not payload or payload.get("_token_error"):
        return {
            "status": "error",
            "message": "Token tidak valid",
        }

    user_id = payload.get("user_id")
    try:
        response = (
            supabase
            .table("users")
            .select("id, name, email, role")
            .eq("id", user_id)
            .single()
            .execute()
        )
        user = response.data if response else {"id": user_id}
        log_activity(
            actor=user,
            action="logout",
            entity_type="auth",
            entity_id=user_id,
            description=f"{user.get('name') or user_id} logout.",
        )
        return {
            "status": "success",
            "message": "Logout berhasil",
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }
