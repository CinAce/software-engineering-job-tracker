"""Tests for file ownership and authorization."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from tests.test_security_extra import make_user


def test_file_ownership():
    with TestClient(app) as client:
        user_a = make_user(client)
        user_b = make_user(client)

        filename = f"private-{uuid4().hex}.txt"

        response = client.post(
            "/files",
            files={
                "file": (
                    filename,
                    b"This belongs to user A.",
                    "text/plain",
                )
            },
            headers=user_a,
        )
        assert response.status_code in (200, 201), response.text

        file_id = response.json()["id"]

        # Owner can see their file.
        response = client.get("/files", headers=user_a)
        assert response.status_code == 200, response.text
        assert any(
            row["id"] == file_id for row in response.json()
        )

        # Another user cannot see it.
        response = client.get("/files", headers=user_b)
        assert response.status_code == 200, response.text
        assert all(
            row["id"] != file_id for row in response.json()
        )

        # Another user cannot download it.
        assert client.get(
            f"/files/download/{file_id}",
            headers=user_b,
        ).status_code == 403

        # Another user cannot generate a download URL.
        assert client.get(
            f"/files/{file_id}/url",
            headers=user_b,
        ).status_code == 403

        # Another user cannot delete it.
        assert client.delete(
            f"/files/{file_id}",
            headers=user_b,
        ).status_code == 403

        # Owner can download it.
        response = client.get(
            f"/files/download/{file_id}",
            headers=user_a,
        )
        assert response.status_code == 200, response.text
        assert response.content == b"This belongs to user A."

        # Owner can delete it.
        assert client.delete(
            f"/files/{file_id}",
            headers=user_a,
        ).status_code == 204


def test_user_cannot_confirm_another_users_upload():
    with TestClient(app) as client:
        user_a = make_user(client)
        user_b = make_user(client)

        response = client.post(
            "/files/presign",
            params={"filename": "private.txt"},
            headers=user_a,
        )
        assert response.status_code == 200, response.text

        key = response.json()["key"]

        response = client.post(
            "/files/presign/confirm",
            params={
                "key": key,
                "filename": "private.txt",
            },
            headers=user_b,
        )
        assert response.status_code == 403, response.text
