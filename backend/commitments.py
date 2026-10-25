import re
from datetime import date, time
from typing import Any

from flask import Blueprint, jsonify, request, session

import store


commitments_blueprint = Blueprint(
    "commitments", __name__, url_prefix="/api/commitments"
)

_ALLOWED_TYPES = {"assignment", "work", "event", "personal"}
_FIELDS = {
    "title",
    "type",
    "date",
    "start_time",
    "end_time",
    "description",
    "completed",
}
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")


@commitments_blueprint.before_request
def require_login():
    if session.get("user_id") is None:
        return jsonify({"error": "Authentication required."}), 401
    return None


def _user_id() -> int:
    return session["user_id"]


def _json_object() -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, (jsonify({"error": "Request body must be a JSON object."}), 400)
    unknown_fields = set(payload) - _FIELDS
    if unknown_fields:
        field = sorted(unknown_fields)[0]
        return None, (jsonify({"error": f"Unknown field: {field}."}), 400)
    return payload, None


def _validate_values(
    payload: dict[str, Any], *, partial: bool
) -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
    values = dict(payload)
    if not partial:
        missing = {"title", "type", "date"} - values.keys()
        if missing:
            field = sorted(missing)[0]
            return None, (jsonify({"error": f"Field '{field}' is required."}), 400)

    if "title" in values:
        title = values["title"]
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
            return None, (
                jsonify({"error": "Title must contain 1 to 200 characters."}),
                400,
            )
        values["title"] = title.strip()

    if "type" in values and (
        not isinstance(values["type"], str) or values["type"] not in _ALLOWED_TYPES
    ):
        return None, (
            jsonify(
                {
                    "error": (
                        "Type must be one of: assignment, work, event, personal."
                    )
                }
            ),
            400,
        )

    if "date" in values:
        date_value = values["date"]
        if not isinstance(date_value, str) or not _DATE_PATTERN.fullmatch(date_value):
            return None, (jsonify({"error": "Date must use YYYY-MM-DD format."}), 400)
        try:
            date.fromisoformat(date_value)
        except ValueError:
            return None, (jsonify({"error": "Date must be a valid calendar date."}), 400)

    for field in ("start_time", "end_time"):
        if field not in values or values[field] is None:
            continue
        time_value = values[field]
        if not isinstance(time_value, str) or not _TIME_PATTERN.fullmatch(time_value):
            return None, (
                jsonify({"error": f"{field} must use HH:MM format or be null."}),
                400,
            )
        try:
            time.fromisoformat(time_value)
        except ValueError:
            return None, (jsonify({"error": f"{field} must be a valid time."}), 400)

    start_time = values.get("start_time")
    end_time = values.get("end_time")
    if start_time is not None and end_time is not None:
        if time.fromisoformat(end_time) <= time.fromisoformat(start_time):
            return None, (
                jsonify({"error": "End time must be later than start time."}),
                400,
            )

    if "description" in values:
        description = values["description"]
        if description is not None and (
            not isinstance(description, str) or len(description) > 5000
        ):
            return None, (
                jsonify({"error": "Description must be at most 5000 characters or null."}),
                400,
            )

    if "completed" in values and not isinstance(values["completed"], bool):
        return None, (jsonify({"error": "Completed must be a boolean."}), 400)

    return values, None


def _commitment_id(value: str) -> int | None:
    if len(value) > 19 or not value.isascii() or not value.isdecimal():
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


@commitments_blueprint.get("")
def list_commitments():
    return jsonify({"commitments": store.list_commitments(_user_id())})


@commitments_blueprint.post("")
def create_commitment():
    payload, error = _json_object()
    if error:
        return error
    values, error = _validate_values(payload, partial=False)
    if error:
        return error
    commitment = store.create_commitment(_user_id(), values)
    return jsonify({"commitment": commitment}), 201


@commitments_blueprint.route(
    "/<commitment_id>", methods=["GET", "PUT", "PATCH", "DELETE"]
)
def commitment_detail(commitment_id: str):
    parsed_id = _commitment_id(commitment_id)
    if parsed_id is None:
        return jsonify({"error": "Commitment not found."}), 404

    if request.method == "GET":
        commitment = store.get_commitment(_user_id(), parsed_id)
        if commitment is None:
            return jsonify({"error": "Commitment not found."}), 404
        return jsonify({"commitment": commitment})

    if request.method == "DELETE":
        if not store.delete_commitment(_user_id(), parsed_id):
            return jsonify({"error": "Commitment not found."}), 404
        return "", 204

    payload, error = _json_object()
    if error:
        return error
    values, error = _validate_values(payload, partial=request.method == "PATCH")
    if error:
        return error
    if not values:
        return jsonify({"error": "At least one field must be provided."}), 400
    if request.method == "PUT":
        values = {
            "title": values["title"],
            "type": values["type"],
            "date": values["date"],
            "start_time": values.get("start_time"),
            "end_time": values.get("end_time"),
            "description": values.get("description"),
            "completed": values.get("completed", False),
        }

    existing = store.get_commitment(_user_id(), parsed_id)
    if existing is None:
        return jsonify({"error": "Commitment not found."}), 404
    candidate_start = values.get("start_time", existing["start_time"])
    candidate_end = values.get("end_time", existing["end_time"])
    if (
        candidate_start is not None
        and candidate_end is not None
        and time.fromisoformat(candidate_end) <= time.fromisoformat(candidate_start)
    ):
        return jsonify({"error": "End time must be later than start time."}), 400

    commitment = store.update_commitment(_user_id(), parsed_id, values)
    if commitment is None:
        return jsonify({"error": "Commitment not found."}), 404
    return jsonify({"commitment": commitment})


@commitments_blueprint.patch("/<commitment_id>/completion")
def set_completion(commitment_id: str):
    parsed_id = _commitment_id(commitment_id)
    if parsed_id is None:
        return jsonify({"error": "Commitment not found."}), 404

    payload, error = _json_object()
    if error:
        return error
    if set(payload) != {"completed"} or not isinstance(payload["completed"], bool):
        return jsonify({"error": "Provide a boolean 'completed' value."}), 400

    commitment = store.update_commitment(
        _user_id(), parsed_id, {"completed": payload["completed"]}
    )
    if commitment is None:
        return jsonify({"error": "Commitment not found."}), 404
    return jsonify({"commitment": commitment})
