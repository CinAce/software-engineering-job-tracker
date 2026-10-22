import base64
import jwt
import datetime as dt
from fastapi.testclient import TestClient

from app.main import app
from app.ports.config import get_settings
from app import security

client = TestClient(app)
settings = get_settings()

from app.db import Base, engine
Base.metadata.create_all(bind=engine)

# Unique credentials to prevent database collisions
TEST_USER = f"user_{dt.datetime.now().timestamp()}@example.com"
TEST_USER_2 = f"other_{dt.datetime.now().timestamp()}@example.com"
TEST_PASSWORD = "StrongPassword123!"

# ---------------------------------------------------------
# 4a: Authentication Tests
# ---------------------------------------------------------
def test_register_success():
    response = client.post("/auth/register", json={"email": TEST_USER, "password": TEST_PASSWORD})
    assert response.status_code == 201

def test_login_success():
    # OAuth2PasswordRequestForm requires form data, not JSON
    response = client.post("/auth/login", data={"username": TEST_USER, "password": TEST_PASSWORD})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password():
    response = client.post("/auth/login", data={"username": TEST_USER, "password": "wrongpassword"})
    assert response.status_code == 401

def test_login_unknown_user():
    response = client.post("/auth/login", data={"username": "unknown@example.com", "password": TEST_PASSWORD})
    assert response.status_code == 401

def test_missing_or_malformed_token():
    response = client.get("/auth/me", headers={"Authorization": "Bearer bad.token.here"})
    assert response.status_code == 401

# ---------------------------------------------------------
# 4b: Authorization Tests (Roles & Ownership)
# ---------------------------------------------------------
def test_authz_missing_token():
    response = client.get("/tasks")
    assert response.status_code == 401

def test_authz_valid_token_is_owner():
    token = client.post("/auth/login", data={"username": TEST_USER, "password": TEST_PASSWORD}).json()["access_token"]
    task_res = client.post("/tasks", json={"title": "My Task"}, headers={"Authorization": f"Bearer {token}"})
    task_id = task_res.json()["id"]
    
    res = client.get(f"/tasks/{task_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

def test_authz_valid_token_wrong_role_not_owner():
    # Register and login second user
    client.post("/auth/register", json={"email": TEST_USER_2, "password": TEST_PASSWORD})
    token2 = client.post("/auth/login", data={"username": TEST_USER_2, "password": TEST_PASSWORD}).json()["access_token"]
    
    # Attempt to access the first user's task
    res = client.get("/tasks/1", headers={"Authorization": f"Bearer {token2}"})
    assert res.status_code in [403, 404]

def test_administrative_endpoint_refuses_non_admin():
    token = client.post("/auth/login", data={"username": TEST_USER, "password": TEST_PASSWORD}).json()["access_token"]
    res = client.get("/admin/tasks", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

# ---------------------------------------------------------
# 4c: Attack Vectors
# ---------------------------------------------------------
def test_attack_expired_token():
    past = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=10)
    token = jwt.encode({"sub": TEST_USER, "exp": past}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401

def test_attack_invalid_algorithm():
    # Forging a token with the 'none' algorithm bypass
    def b64(val): return base64.urlsafe_b64encode(val.encode()).decode().rstrip('=')
    token = f"{b64('{\"alg\":\"none\",\"typ\":\"JWT\"}')}.{b64('{\"sub\":\"' + TEST_USER + '\"}')}."
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401

def test_attack_missing_required_role():
    token = client.post("/auth/login", data={"username": TEST_USER, "password": TEST_PASSWORD}).json()["access_token"]
    res = client.get("/admin/tasks", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

# ---------------------------------------------------------
# 4d: Password Storage Tests
# ---------------------------------------------------------
def test_password_round_trip():
    hashed = security.hash_password("MySecretPassword123!")
    assert security.verify_password("MySecretPassword123!", hashed) is True

def test_password_rejects_wrong_match():
    hashed = security.hash_password("MySecretPassword123!")
    assert security.verify_password("wrong", hashed) is False

def test_password_over_72_bytes_rejected():
    long_password = "a" * 73
    response = client.post("/auth/register", json={"email": "long@example.com", "password": long_password})
    assert response.status_code == 422