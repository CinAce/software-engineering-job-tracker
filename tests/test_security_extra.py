"""Additional authentication and authorization tests."""

import datetime as dt
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.main import app
from app.security import settings


def make_user(client):
    email = f"security-{uuid4().hex[:12]}@example.edu"
    password = "a-sufficiently-long-passphrase"

    response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201, response.text

    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, response.text

    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_expired_token_rejected():
    with TestClient(app) as client:
        token = jwt.encode(
            {
                "sub": "expired@example.edu",
                "exp": dt.datetime.now(dt.UTC) - dt.timedelta(minutes=5),
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401


def test_unsigned_token_rejected():
    with TestClient(app) as client:
        token = jwt.encode(
            {"sub": "unsigned@example.edu"},
            key="",
            algorithm="none",
        )

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401


def test_regular_user_cannot_access_admin_tasks():
    with TestClient(app) as client:
        headers = make_user(client)
        response = client.get("/admin/tasks", headers=headers)
        assert response.status_code == 403


def test_regular_user_cannot_publish_admin_event():
    with TestClient(app) as client:
        headers = make_user(client)
        response = client.post(
            "/api/events/publish",
            json={"event_type": "test", "data": {"message": "hello"}},
            headers=headers,
        )
        assert response.status_code == 403


def test_user_cannot_access_another_users_task():
    with TestClient(app) as client:
        user_a = make_user(client)
        user_b = make_user(client)

        response = client.post(
            "/tasks",
            json={"title": "Private task"},
            headers=user_a,
        )
        assert response.status_code == 201, response.text

        task_id = response.json()["id"]

        assert client.get(
            f"/tasks/{task_id}", headers=user_b
        ).status_code == 403

        assert client.delete(
            f"/tasks/{task_id}", headers=user_b
        ).status_code == 403

        assert client.get(
            f"/tasks/{task_id}", headers=user_a
        ).status_code == 200
