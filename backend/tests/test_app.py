from unittest.mock import patch

import pytest
from werkzeug.security import generate_password_hash

from app import create_app

USER = {"id": 1, "email": "adina@test.com"}
PASSWORD_HASH = generate_password_hash("studentplanner123")


@pytest.fixture
def client():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "SESSION_COOKIE_SECURE": True,
        }
    )
    return app.test_client()


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_login_success_returns_safe_user_and_secure_session_cookie(client):
    user = {**USER, "password_hash": PASSWORD_HASH}
    with patch("auth.store.get_user_by_email", return_value=user):
        response = client.post(
            "/api/auth/login",
            json={"email": " ADINA@test.com ", "password": "studentplanner123"},
        )

    assert response.status_code == 200
    assert response.get_json() == {"user": USER}
    assert "password_hash" not in response.get_data(as_text=True)
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Secure" in cookie


@pytest.mark.parametrize(
    ("user", "password"),
    [
        (None, "studentplanner123"),
        ({"id": 1, "email": USER["email"], "password_hash": PASSWORD_HASH}, "wrong"),
    ],
)
def test_login_failure_uses_generic_error(client, user, password):
    with patch("auth.store.get_user_by_email", return_value=user):
        response = client.post(
            "/api/auth/login",
            json={"email": USER["email"], "password": password},
        )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid email or password."}


@pytest.mark.parametrize(
    "payload",
    [None, {}, {"email": "", "password": "x"}, {"email": USER["email"], "password": ""}],
)
def test_login_rejects_invalid_request_payload(client, payload):
    response = client.post("/api/auth/login", json=payload)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_current_user_requires_authentication(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication required."}


def test_current_user_returns_safe_user_after_login(client):
    with (
        patch(
            "auth.store.get_user_by_email",
            return_value={**USER, "password_hash": PASSWORD_HASH},
        ),
        patch("auth.store.get_user_by_id", return_value=USER),
    ):
        login_response = client.post(
            "/api/auth/login",
            json={"email": USER["email"], "password": "studentplanner123"},
        )
        response = client.get("/api/auth/me")

    assert login_response.status_code == 200
    assert response.status_code == 200
    assert response.get_json() == {"user": USER}


def test_logout_clears_authentication(client):
    with patch(
        "auth.store.get_user_by_email",
        return_value={**USER, "password_hash": PASSWORD_HASH},
    ):
        assert client.post(
            "/api/auth/login",
            json={"email": USER["email"], "password": "studentplanner123"},
        ).status_code == 200

    logout_response = client.post("/api/auth/logout")
    current_user_response = client.get("/api/auth/me")

    assert logout_response.status_code == 204
    assert current_user_response.status_code == 401


def test_missing_secret_key_is_rejected(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
        create_app()


def test_cookie_samesite_none_requires_secure_cookie(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "None")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")

    with pytest.raises(RuntimeError, match="SESSION_COOKIE_SECURE must be true"):
        create_app({"SECRET_KEY": "test-only-secret"})


def test_cors_allows_only_configured_origin_and_credentials():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "FRONTEND_ORIGIN": "https://planner.example.com",
        }
    )
    client = app.test_client()

    allowed = client.get(
        "/health", headers={"Origin": "https://planner.example.com"}
    )
    denied = client.get("/health", headers={"Origin": "https://other.example.com"})

    assert allowed.headers["Access-Control-Allow-Origin"] == (
        "https://planner.example.com"
    )
    assert allowed.headers["Access-Control-Allow-Credentials"] == "true"
    assert "Origin" in allowed.headers["Vary"]
    assert "Access-Control-Allow-Origin" not in denied.headers


def test_cors_preflight_allows_credentials_and_requested_api_headers():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "FRONTEND_ORIGIN": "https://planner.example.com",
        }
    )
    client = app.test_client()

    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://planner.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == (
        "https://planner.example.com"
    )
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert response.headers["Access-Control-Allow-Headers"] == "Content-Type"


def test_commitment_preflight_does_not_require_session_cookie():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "FRONTEND_ORIGIN": "https://planner.example.com",
        }
    )

    response = app.test_client().options(
        "/api/commitments/31",
        headers={
            "Origin": "https://planner.example.com",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == (
        "https://planner.example.com"
    )
    assert "PATCH" in response.headers["Access-Control-Allow-Methods"]


def test_login_uses_cross_site_secure_cookie_when_configured():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "SESSION_COOKIE_SAMESITE": "None",
            "SESSION_COOKIE_SECURE": True,
            "FRONTEND_ORIGIN": "https://planner.example.com",
        }
    )
    with patch(
        "auth.store.get_user_by_email",
        return_value={**USER, "password_hash": PASSWORD_HASH},
    ):
        response = app.test_client().post(
            "/api/auth/login",
            json={"email": USER["email"], "password": "studentplanner123"},
            headers={"Origin": "https://planner.example.com"},
        )

    assert response.status_code == 200
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=None" in cookie
    assert "Secure" in cookie


def test_configured_cors_origin_is_required_for_api_mutations():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "FRONTEND_ORIGIN": "https://planner.example.com",
        }
    )

    response = app.test_client().post("/api/auth/logout")

    assert response.status_code == 403
    assert response.get_json() == {"error": "Request origin is not allowed."}


def test_wildcard_cors_origin_is_rejected():
    with pytest.raises(RuntimeError, match="FRONTEND_ORIGIN cannot be a wildcard"):
        create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-only-secret",
                "FRONTEND_ORIGIN": "*",
            }
        )


def test_seed_command_is_registered(client, monkeypatch):
    monkeypatch.setattr("app.seed_demo_users", lambda: 2)

    result = client.application.test_cli_runner().invoke(
        args=["seed-demo-users"]
    )

    assert result.exit_code == 0
    assert "Created 2 of 2 demo accounts." in result.output
