from flask import Blueprint, request, jsonify
from app.services.auth import register_user, login_user

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