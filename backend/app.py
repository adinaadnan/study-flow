import os
from collections.abc import Mapping
from typing import Any

from flask import Flask, jsonify

from auth import auth_blueprint
from commitments import commitments_blueprint
from seed import DEMO_ACCOUNTS, seed_demo_users


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get(
            "SESSION_COOKIE_SECURE", "false"
        ).lower()
        in {"1", "true", "yes"},
    )
    if test_config is not None:
        app.config.update(test_config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY must be set in the environment.")

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(commitments_blueprint)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.cli.command("seed-demo-users")
    def seed_demo_users_command():
        created_count = seed_demo_users()
        print(f"Created {created_count} of {len(DEMO_ACCOUNTS)} demo accounts.")

    return app
