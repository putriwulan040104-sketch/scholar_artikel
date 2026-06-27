from flask import Blueprint, jsonify, request
from app.services.user_service import create_user, delete_user, get_users, update_user

users_bp = Blueprint("users", __name__)

def _get_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    return auth_header.replace("Bearer ", "", 1).strip()

def _json_result(result, success_status=200):
    if result["status"] == "error":
        status_code = result.pop("status_code", 400)
        return jsonify(result), status_code

    return jsonify(result), success_status

@users_bp.route("/users", methods=["GET"])
def list_users():
    token = _get_token()
    if not token:
        return jsonify({
            "status": "error",
            "message": "Token tidak ditemukan",
        }), 401

    result = get_users(token)
    return _json_result(result)

@users_bp.route("/users", methods=["POST"])
def store_user():
    token = _get_token()
    if not token:
        return jsonify({
            "status": "error",
            "message": "Token tidak ditemukan",
        }), 401

    result = create_user(token, request.json or {})
    return _json_result(result, 201)

@users_bp.route("/users/<user_id>", methods=["PUT"])
def edit_user(user_id):
    token = _get_token()
    if not token:
        return jsonify({
            "status": "error",
            "message": "Token tidak ditemukan",
        }), 401

    result = update_user(token, user_id, request.json or {})
    return _json_result(result)

@users_bp.route("/users/<user_id>", methods=["DELETE"])
def remove_user(user_id):
    token = _get_token()
    if not token:
        return jsonify({
            "status": "error",
            "message": "Token tidak ditemukan",
        }), 401

    result = delete_user(token, user_id)
    return _json_result(result)
