from flask import Blueprint, request, jsonify
from app.services.auth import (
  register_user,
  login_user,
  logout_user,
  update_profile_user,
)

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
  data = request.json

  if not data:
        return jsonify({
            "status": "error",
            "message": "Body kosong"
        }), 400

  name = data.get("name")
  email = data.get("email")
  password = data.get("password")

  if not all([name, email, password]):
    return jsonify({"status": "error", "message": "Name, email, dan password wajib diisi"}), 400

  result = register_user(name, email, password)

  if result["status"] == "error":
        return jsonify(result), 400

  return jsonify(result), 201

@auth_bp.route("/login", methods=["POST"])
def login():
  data = request.json

  if not data:
    return jsonify({"status": "error", "message": "Body kosong"}), 400
  
  email = data.get("email")
  password = data.get("password")

  if not all([email, password]):
    return jsonify({"status": "error", "message": "Email dan password wajib diisi"}), 400

  result = login_user(email, password)

  if result["status"] == "error":
    return jsonify(result), 401

  return jsonify(result), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
  auth_header = request.headers.get("Authorization", "")
  if not auth_header.startswith("Bearer "):
    return jsonify({
      "status": "error",
      "message": "Token tidak ditemukan"
    }), 401

  token = auth_header.replace("Bearer ", "", 1).strip()
  result = logout_user(token)
  if result["status"] == "error":
    return jsonify(result), 400

  return jsonify(result), 200


@auth_bp.route("/profile", methods=["PUT"])
def update_profile():
  auth_header = request.headers.get("Authorization", "")
  if not auth_header.startswith("Bearer "):
    return jsonify({
      "status": "error",
      "message": "Token tidak ditemukan"
    }), 401

  token = auth_header.replace("Bearer ", "", 1).strip()
  data = request.json or {}

  result = update_profile_user(
    token=token,
    name=data.get("name"),
    email=data.get("email"),
    avatar_url=data.get("avatarUrl")
  )

  if result["status"] == "error":
    status_code = 400
    if "token" in (result.get("message") or "").lower():
      status_code = 401
    return jsonify(result), status_code

  return jsonify(result), 200
