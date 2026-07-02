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

    if action and action != "all":
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
            query = query.or_(
                f"user_name.ilike.%{term}%,"
                f"description.ilike.%{term}%,"
                f"entity_id.ilike.%{term}%"
            )

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
