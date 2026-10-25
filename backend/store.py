import os
from typing import Any

import psycopg
from psycopg.rows import dict_row


def _database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL must be set before accessing the database."
        )
    return database_url


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
        row = connection.execute(
            """
            SELECT id, email, password_hash
            FROM users
            WHERE email = %s
            """,
            (email,),
        ).fetchone()
    return dict(row) if row is not None else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
        row = connection.execute(
            """
            SELECT id, email
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def create_user_if_missing(email: str, password_hash: str) -> bool:
    with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
        row = connection.execute(
            """
            INSERT INTO users (email, password_hash)
            VALUES (%s, %s)
            ON CONFLICT (email) DO NOTHING
            RETURNING id
            """,
            (email, password_hash),
        ).fetchone()
    return row is not None


_COMMITMENT_FIELDS = """
    id, title, type, date, start_time, end_time, description, completed,
    created_at, updated_at
"""


def _commitment_dict(row: Any) -> dict[str, Any]:
    commitment = dict(row)
    for field in ("date", "created_at", "updated_at"):
        commitment[field] = commitment[field].isoformat()
    for field in ("start_time", "end_time"):
        if commitment[field] is not None:
            commitment[field] = commitment[field].strftime("%H:%M")
    return commitment


def list_commitments(user_id: int) -> list[dict[str, Any]]:
    with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
        rows = connection.execute(
            f"""
            SELECT {_COMMITMENT_FIELDS}
            FROM commitments
            WHERE user_id = %s
            ORDER BY date, start_time NULLS LAST, id
            """,
            (user_id,),
        ).fetchall()
    return [_commitment_dict(row) for row in rows]


def get_commitment(user_id: int, commitment_id: int) -> dict[str, Any] | None:
    with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
        row = connection.execute(
            f"""
            SELECT {_COMMITMENT_FIELDS}
            FROM commitments
            WHERE user_id = %s AND id = %s
            """,
            (user_id, commitment_id),
        ).fetchone()
    return _commitment_dict(row) if row is not None else None


def create_commitment(user_id: int, values: dict[str, Any]) -> dict[str, Any]:
    with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
        row = connection.execute(
            f"""
            INSERT INTO commitments
                (user_id, title, type, date, start_time, end_time, description, completed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING {_COMMITMENT_FIELDS}
            """,
            (
                user_id,
                values["title"],
                values["type"],
                values["date"],
                values.get("start_time"),
                values.get("end_time"),
                values.get("description"),
                values.get("completed", False),
            ),
        ).fetchone()
    return _commitment_dict(row)


def update_commitment(
    user_id: int, commitment_id: int, values: dict[str, Any]
) -> dict[str, Any] | None:
    assignments = [f"{field} = %s" for field in values]
    parameters = list(values.values())
    assignments.append("updated_at = CURRENT_TIMESTAMP")
    parameters.extend((user_id, commitment_id))
    with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
        row = connection.execute(
            f"""
            UPDATE commitments
            SET {", ".join(assignments)}
            WHERE user_id = %s AND id = %s
            RETURNING {_COMMITMENT_FIELDS}
            """,
            parameters,
        ).fetchone()
    return _commitment_dict(row) if row is not None else None


def delete_commitment(user_id: int, commitment_id: int) -> bool:
    with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
        row = connection.execute(
            """
            DELETE FROM commitments
            WHERE user_id = %s AND id = %s
            RETURNING id
            """,
            (user_id, commitment_id),
        ).fetchone()
    return row is not None
