"""The test suite modules 1-6 build toward and module 7's CI pipeline runs.

Module 7 in the previous version of this course required >80% coverage of a test
suite the course never taught. These exist from module 1 so that requirement is
reachable.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import (
    MAX_PASSWORD_BYTES,
    PasswordTooLongError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_root(client: TestClient) -> None:
    assert client.get("/").status_code == 200


def test_health_reports_database_ok(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["checks"]["database"] == "ok", body


def test_metrics_needs_trailing_slash(client: TestClient) -> None:
    # The behavior students trip over, pinned as a test so it stays documented.
    assert b"itc531_requests_total" in client.get("/metrics/").content


def test_task_round_trip(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "write the adapter"})
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]
    assert client.get(f"/tasks/{task_id}").json()["title"] == "write the adapter"
    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404


def test_register_login_and_me(client: TestClient) -> None:
    # A unique address per run, so the suite is idempotent against a persistent
    # volume. A fixed address passes once and then 409s forever, which looks
    # like a regression and is not one.
    creds = {
        "email": f"student-{uuid4().hex[:12]}@example.edu",
        "password": "a-sufficiently-long-passphrase",
    }
    registered = client.post("/auth/register", json=creds)
    assert registered.status_code == 201, registered.text
    # roles must serialize as objects, not strings
    assert registered.json()["roles"][0]["name"] == "user"

    # the same address twice is a conflict, not a second account
    assert client.post("/auth/register", json=creds).status_code == 409

    token = client.post(
        "/auth/login",
        data={"username": creds["email"], "password": creds["password"]},
    ).json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == creds["email"]


def test_login_rejects_wrong_password(client: TestClient) -> None:
    creds = {
        "email": f"student-{uuid4().hex[:12]}@example.edu",
        "password": "a-sufficiently-long-passphrase",
    }
    assert client.post("/auth/register", json=creds).status_code == 201
    response = client.post(
        "/auth/login", data={"username": creds["email"], "password": "wrong-but-long-enough"}
    )
    assert response.status_code == 401


def test_me_rejects_missing_and_bad_tokens(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_password_hashing_round_trip() -> None:
    hashed = hash_password("a-sufficiently-long-passphrase")
    assert verify_password("a-sufficiently-long-passphrase", hashed)
    assert not verify_password("something-else-entirely", hashed)


def test_password_over_72_bytes_is_rejected_not_truncated() -> None:
    with pytest.raises(PasswordTooLongError):
        hash_password("x" * (MAX_PASSWORD_BYTES + 1))


def test_token_round_trip() -> None:
    assert decode_access_token(create_access_token("someone@example.edu"))["sub"] == (
        "someone@example.edu"
    )


def test_function_handler_shape() -> None:
    from functions.handler import handler

    class Ctx:
        function_name = "test"
        memory_limit_in_mb = 128

    ok = handler({"body": '{"name": "ada"}'}, Ctx())
    assert ok["statusCode"] == 200
    assert "ada" in ok["body"]

    assert handler({"body": "{}"}, Ctx())["statusCode"] == 422
    assert handler({"body": "not json"}, Ctx())["statusCode"] == 400
