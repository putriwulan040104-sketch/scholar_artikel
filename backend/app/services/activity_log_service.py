import json
import re
from datetime import datetime, timezone
from flask import has_request_context, request
from app.db import supabase

SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "authorization",
}

HIDDEN_ACTIONS = {"login", "logout", "register"}

ACTION_SEARCH_TEXT = {
    "update_profile": "update profile ubah profil",
    "create_user": "create user tambah pengguna",
    "update_user": "update user ubah pengguna",
    "delete_user": "delete user hapus pengguna",
    "update_request_status": "update request status ubah status request",
    "update_publication": "update publication ubah publikasi",
    "delete_publication": "delete publication hapus publikasi",
}

def _sanitize_value(value, key=""):
    normalized_key = str(key or "").strip().lower()
    if normalized_key in SENSITIVE_KEYS:
        return "[REDACTED]"

    if normalized_key in {"avatar_url", "avatarurl"}:
        text = str(value or "")
        return "[IMAGE_DATA]" if text.startswith("data:image/") else text

    if isinstance(value, dict):
        return {
            str(item_key): _sanitize_value(item_value, item_key)
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)

def _json_value(value):
    if value is None:
        return None
    sanitized = _sanitize_value(value)
    try:
        json.dumps(sanitized)
        return sanitized
    except (TypeError, ValueError):
        return {"value": str(sanitized)}

def _request_ip():
    if not has_request_context():
        return None

    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.remote_addr

def log_activity(
    *,
    actor=None,
    action,
    entity_type=None,
    entity_id=None,
    description=None,
    old_data=None,
    new_data=None,
    status="success",
    user_name=None,
):
    if str(action) in HIDDEN_ACTIONS:
        return False

    actor = actor or {}
    payload = {
        "user_id": actor.get("id"),
        "user_name": (
            user_name
            or actor.get("name")
            or actor.get("email")
            or "System"
        ),
        "action": str(action),
        "entity_type": str(entity_type) if entity_type is not None else None,
        "entity_id": str(entity_id) if entity_id is not None else None,
        "description": description,
        "old_data": _json_value(old_data),
        "new_data": _json_value(new_data),
        "ip_address": _request_ip(),
        "status": "failed" if status == "failed" else "success",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        supabase.table("activity_logs").insert(payload).execute()
        return True
    except Exception as error:
        print(f"[AUDIT LOG] Gagal menyimpan aktivitas {action}: {error}")
        return False


def _normalize_log(row):
    return {
        "id": row.get("id"),
        "userId": row.get("user_id"),
        "userName": row.get("user_name") or "System",
        "action": row.get("action"),
        "entityType": row.get("entity_type"),
        "entityId": row.get("entity_id"),
        "description": row.get("description"),
        "oldData": row.get("old_data"),
        "newData": row.get("new_data"),
        "ipAddress": row.get("ip_address"),
        "status": row.get("status") or "success",
        "createdAt": row.get("created_at"),
    }

def _matching_actions(term):
    normalized_term = re.sub(r"\s+", " ", str(term or "").lower()).strip()
    if not normalized_term:
        return []

    words = normalized_term.split()
    matches = []
    for action, search_text in ACTION_SEARCH_TEXT.items():
        if action in HIDDEN_ACTIONS:
            continue
        normalized_search_text = search_text.lower()
        if normalized_term in normalized_search_text or all(
            word in normalized_search_text for word in words
        ):
            matches.append(action)
    return matches

def get_activity_logs(
    *,
    page=1,
    page_size=10,
    search="",
    action="all",
    entity_type="all",
    status="all",
    date_from=None,
    date_to=None,
):
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 10), 1), 100)
    start = (page - 1) * page_size
    end = start + page_size - 1

    query = (
        supabase
        .table("activity_logs")
        .select(
            "id,user_id,user_name,action,entity_type,entity_id,"
            "description,old_data,new_data,ip_address,status,created_at",
            count="exact",
        )
    )
    for hidden_action in HIDDEN_ACTIONS:
        query = query.neq("action", hidden_action)

    if action and action != "all":
        if action in HIDDEN_ACTIONS:
            return {
                "status": "success",
                "data": [],
                "total": 0,
                "page": page,
                "pageSize": page_size,
                "totalPages": 1,
            }
        query = query.eq("action", action)
    if entity_type and entity_type != "all":
        query = query.eq("entity_type", entity_type)
    if status and status != "all":
        query = query.eq("status", status)
    if date_from:
        query = query.gte("created_at", date_from)
    if date_to:
        query = query.lte("created_at", date_to)
    if search:
        term = re.sub(r"[^a-zA-Z0-9@._\-\s]", " ", str(search)).strip()
        if term:
            search_clauses = [
                f"user_name.ilike.%{term}%",
                f"description.ilike.%{term}%",
                f"entity_id.ilike.%{term}%",
                f"action.ilike.%{term}%",
            ]
            search_clauses.extend(
                f"action.eq.{matched_action}"
                for matched_action in _matching_actions(term)
            )
            query = query.or_(",".join(search_clauses))

    response = query.order("created_at", desc=True).range(start, end).execute()
    rows = [_normalize_log(row) for row in (response.data or [])]
    total = int(response.count or 0)

    return {
        "status": "success",
        "data": rows,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }
