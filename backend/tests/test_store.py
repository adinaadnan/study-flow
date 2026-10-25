from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

import store


@pytest.fixture(autouse=True)
def database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost/db")


def test_database_access_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL")

    with pytest.raises(RuntimeError, match="DATABASE_URL must be set"):
        store.get_user_by_email("adina@test.com")


def test_get_user_by_email_uses_parameterized_query():
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchone.return_value = {
        "id": 1,
        "email": "adina@test.com",
        "password_hash": "hashed-value",
    }
    with patch("store.psycopg.connect", return_value=connection) as connect:
        user = store.get_user_by_email("adina@test.com")

    assert user == {
        "id": 1,
        "email": "adina@test.com",
        "password_hash": "hashed-value",
    }
    connect.assert_called_once()
    assert "%s" in connection.execute.call_args.args[0]
    assert connection.execute.call_args.args[1] == ("adina@test.com",)


@pytest.mark.parametrize(
    ("inserted_row", "expected"),
    [({"id": 2}, True), (None, False)],
)
def test_create_user_if_missing_does_not_overwrite_existing_user(
    inserted_row, expected
):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchone.return_value = inserted_row
    with patch("store.psycopg.connect", return_value=connection):
        created = store.create_user_if_missing("sarah@test.com", "hashed-value")

    query, parameters = connection.execute.call_args.args
    assert "ON CONFLICT (email) DO NOTHING" in query
    assert parameters == ("sarah@test.com", "hashed-value")
    assert created is expected


@pytest.mark.parametrize(
    ("method_name", "arguments", "result_method", "result_value"),
    [
        ("list_commitments", (23,), "fetchall", []),
        ("get_commitment", (23, 81), "fetchone", None),
        ("update_commitment", (23, 81, {"title": "Changed"}), "fetchone", None),
        ("delete_commitment", (23, 81), "fetchone", None),
    ],
)
def test_commitment_queries_scope_records_to_user(
    method_name, arguments, result_method, result_value
):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    getattr(connection.execute.return_value, result_method).return_value = result_value
    with patch("store.psycopg.connect", return_value=connection):
        getattr(store, method_name)(*arguments)

    query, parameters = connection.execute.call_args.args
    assert "user_id = %s" in query
    assert arguments[0] in parameters


def test_create_commitment_binds_owner_id_as_parameter():
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchone.return_value = {
        "id": 81,
        "title": "Report",
        "type": "assignment",
        "date": date(2026, 11, 3),
        "start_time": None,
        "end_time": None,
        "description": None,
        "completed": False,
        "created_at": datetime(2026, 10, 25),
        "updated_at": datetime(2026, 10, 25),
    }
    values = {
        "title": "Report",
        "type": "assignment",
        "date": "2026-11-03",
    }
    with patch("store.psycopg.connect", return_value=connection):
        store.create_commitment(23, values)

    query, parameters = connection.execute.call_args.args
    assert "INSERT INTO commitments" in query
    assert parameters[0] == 23
