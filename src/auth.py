from functools import wraps
from flask import request, jsonify, g
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from dotenv import load_dotenv
import os

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT")

def verify_token(token):
    try:
        idinfo = id_token.verify_oauth2_token(token, grequests.Request(), GOOGLE_CLIENT_ID)
        return idinfo
    except Exception:
        return None

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid token"}), 401

        token = auth_header.split(" ")[1]
        user = verify_token(token)
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 403

        g.user = user

        return f(*args, **kwargs)
    return wrapper
