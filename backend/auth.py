from typing import Any

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

import store


auth_blueprint = Blueprint("auth", __name__, url_prefix="/api/auth")


def _public_user(user: dict[str, Any]) -> dict[str, int | str]:
    return {"id": user["id"], "email": user["email"]}


@auth_blueprint.post("/login")
def login():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    email = payload.get("email")
    password = payload.get("password")
    if not isinstance(email, str) or not email.strip():
        return jsonify({"error": "A valid email is required."}), 400
    if not isinstance(password, str) or not password:
        return jsonify({"error": "A password is required."}), 400

    user = store.get_user_by_email(email.strip().lower())
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    session.clear()
    session["user_id"] = user["id"]
    return jsonify({"user": _public_user(user)}), 200


@auth_blueprint.post("/logout")
def logout():
    session.clear()
    return "", 204


@auth_blueprint.get("/me")
def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401

    user = store.get_user_by_id(user_id)
    if user is None:
        session.clear()
        return jsonify({"error": "Authentication required."}), 401

    return jsonify({"user": _public_user(user)}), 200
