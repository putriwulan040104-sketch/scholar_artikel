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

        user = response.data[0]
        return {
            "status": "success",
            "data": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
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
                "email": user["email"]
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }