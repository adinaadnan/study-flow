import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from flask import Flask, jsonify, request

from auth import auth_blueprint
from commitments import commitments_blueprint
from seed import DEMO_ACCOUNTS, seed_demo_users


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    same_site_value = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax").lower()
    same_site_options = {"lax": "Lax", "strict": "Strict", "none": "None"}
    if same_site_value not in same_site_options:
        raise RuntimeError(
            "SESSION_COOKIE_SAMESITE must be Lax, Strict, or None."
        )
    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "")
    if frontend_origin:
        parsed_origin = urlsplit(frontend_origin)
        if (
            frontend_origin == "*"
            or parsed_origin.scheme not in {"http", "https"}
            or not parsed_origin.netloc
            or parsed_origin.path
            or parsed_origin.query
            or parsed_origin.fragment
            or parsed_origin.username
            or parsed_origin.password
        ):
            raise RuntimeError(
                "FRONTEND_ORIGIN must be one exact HTTP(S) origin without a path."
            )

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE=same_site_options[same_site_value],
        SESSION_COOKIE_SECURE=os.environ.get(
            "SESSION_COOKIE_SECURE", "false"
        ).lower()
        in {"1", "true", "yes"},
        FRONTEND_ORIGIN=frontend_origin,
    )
    if test_config is not None:
        app.config.update(test_config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY must be set in the environment.")
    if (
        app.config["SESSION_COOKIE_SAMESITE"] == "None"
        and not app.config["SESSION_COOKIE_SECURE"]
    ):
        raise RuntimeError(
            "SESSION_COOKIE_SECURE must be true when SameSite=None is used."
        )
    if app.config["FRONTEND_ORIGIN"] == "*":
        raise RuntimeError("FRONTEND_ORIGIN cannot be a wildcard.")

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(commitments_blueprint)

    @app.before_request
    def verify_api_origin():
        if (
            app.config["FRONTEND_ORIGIN"]
            and request.path.startswith("/api/")
            and request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and request.headers.get("Origin") != app.config["FRONTEND_ORIGIN"]
        ):
            return jsonify({"error": "Request origin is not allowed."}), 403
        return None

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        allowed_origin = app.config["FRONTEND_ORIGIN"]
        if allowed_origin and origin == allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = allowed_origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS"
            )
            response.vary.add("Origin")
        return response

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.cli.command("seed-demo-users")
    def seed_demo_users_command():
        created_count = seed_demo_users()
        print(f"Created {created_count} of {len(DEMO_ACCOUNTS)} demo accounts.")

    return app
