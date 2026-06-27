from app.db import supabase
from app.services.auth import _decode_token
from backend.app.services.activity_log_service import log_activity
from app.utils.hash import hash_password


def _normalize_role(role):
    return (role or "").strip().lower().replace("-", "_").replace(" ", "_")


def _normalize_user(user):
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "email": user.get("email"),
        "avatarUrl": user.get("avatar_url"),
        "role": user.get("role") or "user",
        "createdAt": user.get("created_at"),
    }


def _get_requester(user_id):
    response = (
        supabase
        .table("users")
        .select("id, name, email, role")
        .eq("id", user_id)
        .single()
        .execute()
    )
    return response.data if response else None


def _validate_super_admin(token):
    payload = _decode_token(token)
    if not payload:
        return {
            "status": "error",
            "message": "Token tidak valid",
            "status_code": 401,
        }
    if isinstance(payload, dict) and payload.get("_token_error"):
        return {
            "status": "error",
            "message": payload["_token_error"],
            "status_code": 401,
        }

    user_id = payload.get("user_id")
    if not user_id:
        return {
            "status": "error",
            "message": "User pada token tidak ditemukan",
            "status_code": 401,
        }

    try:
        requester = _get_requester(user_id)
        if not requester:
            return {
                "status": "error",
                "message": "User tidak ditemukan",
                "status_code": 404,
            }

        if _normalize_role(requester.get("role")) != "super_admin":
            return {
                "status": "error",
                "message": "Akses ditolak. Fitur ini hanya untuk super admin.",
                "status_code": 403,
            }

        return {
            "status": "success",
            "requester": requester,
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
            "status_code": 400,
        }


def _safe_select_user(user_id):
    response = (
        supabase
        .table("users")
        .select("id, name, email, avatar_url, role, created_at")
        .eq("id", user_id)
        .single()
        .execute()
    )
    return response.data if response else None


def _normalize_email(email):
    return (email or "").strip().lower()


def _normalize_name(name):
    return (name or "").strip()


def _safe_role(role):
    normalized = _normalize_role(role)
    return "super_admin" if normalized == "super_admin" else "user"


def get_users(token):
    auth = _validate_super_admin(token)
    if auth["status"] == "error":
        return auth

    try:
        response = (
            supabase
            .table("users")
            .select("id, name, email, avatar_url, role, created_at")
            .execute()
        )
        users = [_normalize_user(user) for user in (response.data or [])]
        users.sort(key=lambda user: user.get("createdAt") or "", reverse=True)

        return {
            "status": "success",
            "total": len(users),
            "data": users,
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
            "status_code": 400,
        }


def create_user(token, data):
    auth = _validate_super_admin(token)
    if auth["status"] == "error":
        return auth

    name = _normalize_name(data.get("name"))
    email = _normalize_email(data.get("email"))
    password = data.get("password") or ""
    role = _safe_role(data.get("role"))

    if not name or not email or not password:
        return {
            "status": "error",
            "message": "Nama, email, dan password wajib diisi.",
            "status_code": 400,
        }

    try:
        existing = supabase.table("users").select("id").eq("email", email).execute()
        if existing.data:
            log_activity(
                actor=auth.get("requester"),
                action="create_user",
                entity_type="user",
                description=f"Gagal menambahkan pengguna {email}: email sudah terdaftar.",
                new_data={"name": name, "email": email, "role": role},
                status="failed",
            )
            return {
                "status": "error",
                "message": "Email sudah terdaftar.",
                "status_code": 400,
            }

        hashed = hash_password(password)

        response = (
            supabase
            .table("users")
            .insert({
                "name": name,
                "email": email,
                "password": hashed,
                "role": role,
            })
            .execute()
        )

        user = (response.data or [None])[0]
        if not user:
            latest = (
                supabase
                .table("users")
                .select("id")
                .eq("email", email)
                .single()
                .execute()
            )
            user = _safe_select_user(latest.data.get("id")) if latest and latest.data else None

        normalized_user = _normalize_user(user or {})
        log_activity(
            actor=auth.get("requester"),
            action="create_user",
            entity_type="user",
            entity_id=normalized_user.get("id"),
            description=f"Menambahkan pengguna {normalized_user.get('name') or email}.",
            new_data=normalized_user,
        )

        return {
            "status": "success",
            "message": "User berhasil ditambahkan.",
            "data": normalized_user,
        }
    except Exception as error:
        log_activity(
            actor=auth.get("requester"),
            action="create_user",
            entity_type="user",
            description=f"Gagal menambahkan pengguna {email}.",
            new_data={"name": name, "email": email, "role": role},
            status="failed",
        )
        return {
            "status": "error",
            "message": str(error),
            "status_code": 400,
        }


def update_user(token, user_id, data):
    auth = _validate_super_admin(token)
    if auth["status"] == "error":
        return auth

    name = _normalize_name(data.get("name"))
    email = _normalize_email(data.get("email"))
    password = data.get("password") or ""
    role = _safe_role(data.get("role"))

    if not name or not email:
        return {
            "status": "error",
            "message": "Nama dan email wajib diisi.",
            "status_code": 400,
        }

    try:
        current = _safe_select_user(user_id)
        if not current:
            return {
                "status": "error",
                "message": "User tidak ditemukan.",
                "status_code": 404,
            }

        duplicate = (
            supabase
            .table("users")
            .select("id")
            .eq("email", email)
            .neq("id", user_id)
            .execute()
        )
        if duplicate.data:
            log_activity(
                actor=auth.get("requester"),
                action="update_user",
                entity_type="user",
                entity_id=user_id,
                description=f"Gagal memperbarui pengguna {email}: email digunakan akun lain.",
                old_data=_normalize_user(current),
                new_data={"name": name, "email": email, "role": role},
                status="failed",
            )
            return {
                "status": "error",
                "message": "Email sudah digunakan user lain.",
                "status_code": 400,
            }

        update_payload = {
            "name": name,
            "email": email,
            "role": role,
        }

        if password:
            update_payload["password"] = hash_password(password)

        response = (
            supabase
            .table("users")
            .update(update_payload)
            .eq("id", user_id)
            .execute()
        )

        user = (response.data or [None])[0] or _safe_select_user(user_id)

        normalized_user = _normalize_user(user or {})
        log_activity(
            actor=auth.get("requester"),
            action="update_user",
            entity_type="user",
            entity_id=user_id,
            description=f"Memperbarui pengguna {normalized_user.get('name') or user_id}.",
            old_data=_normalize_user(current),
            new_data=normalized_user,
        )

        return {
            "status": "success",
            "message": "User berhasil diperbarui.",
            "data": normalized_user,
        }
    except Exception as error:
        log_activity(
            actor=auth.get("requester"),
            action="update_user",
            entity_type="user",
            entity_id=user_id,
            description=f"Gagal memperbarui pengguna ID {user_id}.",
            status="failed",
        )
        return {
            "status": "error",
            "message": str(error),
            "status_code": 400,
        }


def delete_user(token, user_id):
    auth = _validate_super_admin(token)
    if auth["status"] == "error":
        return auth

    requester_id = str(auth.get("requester", {}).get("id"))
    if str(user_id) == requester_id:
        return {
            "status": "error",
            "message": "Tidak bisa menghapus akun sendiri.",
            "status_code": 400,
        }

    try:
        current = _safe_select_user(user_id)
        if not current:
            return {
                "status": "error",
                "message": "User tidak ditemukan.",
                "status_code": 404,
            }

        supabase.table("users").delete().eq("id", user_id).execute()

        log_activity(
            actor=auth.get("requester"),
            action="delete_user",
            entity_type="user",
            entity_id=user_id,
            description=f"Menghapus pengguna {current.get('name') or user_id}.",
            old_data=_normalize_user(current),
        )

        return {
            "status": "success",
            "message": "User berhasil dihapus.",
            "data": _normalize_user(current),
        }
    except Exception as error:
        log_activity(
            actor=auth.get("requester"),
            action="delete_user",
            entity_type="user",
            entity_id=user_id,
            description=f"Gagal menghapus pengguna ID {user_id}.",
            status="failed",
        )
        return {
            "status": "error",
            "message": str(error),
            "status_code": 400,
        }
