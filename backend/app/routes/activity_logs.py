from flask import Blueprint, jsonify, request
from app.services.activity_log_service import get_activity_logs
from app.services.user_service import _validate_super_admin

activity_logs_bp = Blueprint("activity_logs", __name__)

def _get_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return ""
    return auth_header.replace("Bearer ", "", 1).strip()

@activity_logs_bp.route("/admin/activity-logs", methods=["GET"])
def list_activity_logs():
    auth = _validate_super_admin(_get_token())
    if auth["status"] == "error":
        status_code = auth.pop("status_code", 400)
        return jsonify(auth), status_code

    try:
        result = get_activity_logs(
            page=request.args.get("page", 1),
            page_size=request.args.get("page_size", 10),
            search=request.args.get("search", ""),
            action=request.args.get("action", "all"),
            entity_type=request.args.get("entity_type", "all"),
            status=request.args.get("status", "all"),
            date_from=request.args.get("date_from"),
            date_to=request.args.get("date_to"),
        )
        return jsonify(result), 200
    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error),
        }), 400
    