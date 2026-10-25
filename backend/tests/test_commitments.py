from unittest.mock import patch

import pytest

from app import create_app


USER_ID = 17
COMMITMENT = {
    "id": 31,
    "title": "Submit report",
    "type": "assignment",
    "date": "2026-11-03",
    "start_time": "09:30",
    "end_time": "10:30",
    "description": "Finish the draft",
    "completed": False,
    "created_at": "2026-10-25T12:00:00+00:00",
    "updated_at": "2026-10-25T12:00:00+00:00",
}
VALID_INPUT = {
    "title": "Submit report",
    "type": "assignment",
    "date": "2026-11-03",
    "start_time": "09:30",
    "end_time": "10:30",
    "description": "Finish the draft",
}


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "SECRET_KEY": "test-only-secret"})
    return app.test_client()


def authenticate(client, user_id=USER_ID):
    with client.session_transaction() as session:
        session["user_id"] = user_id


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/commitments", None),
        ("post", "/api/commitments", VALID_INPUT),
        ("get", "/api/commitments/31", None),
        ("patch", "/api/commitments/31", {"title": "Changed"}),
        ("put", "/api/commitments/31", VALID_INPUT),
        ("delete", "/api/commitments/31", None),
        ("patch", "/api/commitments/31/completion", {"completed": True}),
    ],
)
def test_commitment_endpoints_require_authentication(client, method, path, payload):
    response = getattr(client, method)(path, json=payload)

    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication required."}


def test_list_commitments_returns_current_users_ordered_results(client):
    authenticate(client)
    with patch("commitments.store.list_commitments", return_value=[COMMITMENT]) as list_rows:
        response = client.get("/api/commitments")

    assert response.status_code == 200
    assert response.get_json() == {"commitments": [COMMITMENT]}
    list_rows.assert_called_once_with(USER_ID)


def test_create_commitment_returns_created_record(client):
    authenticate(client)
    with patch(
        "commitments.store.create_commitment", return_value=COMMITMENT
    ) as create:
        response = client.post("/api/commitments", json=VALID_INPUT)

    assert response.status_code == 201
    assert response.get_json() == {"commitment": COMMITMENT}
    create.assert_called_once_with(USER_ID, VALID_INPUT)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"type": "event", "date": "2026-11-03"}, "title"),
        ({**VALID_INPUT, "title": " "}, "Title"),
        ({**VALID_INPUT, "title": "x" * 201}, "Title"),
        ({**VALID_INPUT, "type": "other"}, "Type"),
        ({**VALID_INPUT, "type": []}, "Type"),
        ({**VALID_INPUT, "date": "03-11-2026"}, "Date"),
        ({**VALID_INPUT, "date": "2026-02-30"}, "Date"),
        ({**VALID_INPUT, "start_time": "9:30"}, "start_time"),
        ({**VALID_INPUT, "end_time": "25:00"}, "end_time"),
        ({**VALID_INPUT, "start_time": "11:00", "end_time": "10:00"}, "End time"),
        ({**VALID_INPUT, "description": "x" * 5001}, "Description"),
        ({**VALID_INPUT, "completed": "yes"}, "Completed"),
        ({**VALID_INPUT, "unexpected": "value"}, "Unknown field"),
    ],
)
def test_create_validates_payload_without_writing(client, payload, message):
    authenticate(client)
    with patch("commitments.store.create_commitment") as create:
        response = client.post("/api/commitments", json=payload)

    assert response.status_code == 400
    assert message in response.get_json()["error"]
    create.assert_not_called()


def test_create_rejects_non_object_json(client):
    authenticate(client)

    response = client.post(
        "/api/commitments",
        data="[]",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Request body must be a JSON object."}


def test_get_commitment_returns_not_found_for_other_users_record(client):
    authenticate(client, user_id=USER_ID + 1)
    with patch("commitments.store.get_commitment", return_value=None) as get:
        response = client.get("/api/commitments/31")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Commitment not found."}
    get.assert_called_once_with(USER_ID + 1, 31)


def test_patch_updates_only_owned_record_and_validates_time_order(client):
    authenticate(client)
    with (
        patch("commitments.store.get_commitment", return_value=COMMITMENT),
        patch("commitments.store.update_commitment") as update,
    ):
        response = client.patch(
            "/api/commitments/31",
            json={"end_time": "09:00"},
        )

    assert response.status_code == 400
    assert "End time" in response.get_json()["error"]
    update.assert_not_called()


def test_update_hides_other_users_record(client):
    authenticate(client, user_id=USER_ID + 1)
    with (
        patch("commitments.store.get_commitment", return_value=None) as get,
        patch("commitments.store.update_commitment") as update,
    ):
        response = client.patch(
            "/api/commitments/31",
            json={"title": "Someone else's record"},
        )

    assert response.status_code == 404
    get.assert_called_once_with(USER_ID + 1, 31)
    update.assert_not_called()


def test_delete_hides_other_users_record(client):
    authenticate(client, user_id=USER_ID + 1)
    with patch("commitments.store.delete_commitment", return_value=False) as delete:
        response = client.delete("/api/commitments/31")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Commitment not found."}
    delete.assert_called_once_with(USER_ID + 1, 31)


def test_completion_hides_other_users_record(client):
    authenticate(client, user_id=USER_ID + 1)
    with patch("commitments.store.update_commitment", return_value=None) as update:
        response = client.patch(
            "/api/commitments/31/completion",
            json={"completed": True},
        )

    assert response.status_code == 404
    update.assert_called_once_with(
        USER_ID + 1, 31, {"completed": True}
    )


def test_completion_requires_boolean_value(client):
    authenticate(client)

    response = client.patch(
        "/api/commitments/31/completion",
        json={"completed": 1},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Provide a boolean 'completed' value."
    }
