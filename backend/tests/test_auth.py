from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.database import SessionLocal
from tests.conftest import reset_db

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_user():
    reset_db()
    payload = {"name": "Alice", "email": "alice@example.com", "password": "password123"}
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "alice@example.com"
    assert "access_token" in data


def test_duplicate_registration():
    reset_db()
    payload = {"name": "Alice", "email": "alice@example.com", "password": "password123"}
    client.post("/api/auth/register", json=payload)
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 409


def test_login_user():
    reset_db()
    client.post("/api/auth/register", json={"name": "Alice", "email": "alice@example.com", "password": "password123"})
    response = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_invalid_login():
    reset_db()
    client.post("/api/auth/register", json={"name": "Alice", "email": "alice@example.com", "password": "password123"})
    response = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrongpassword"})
    assert response.status_code == 401


def test_authenticated_user():
    reset_db()
    response = client.post("/api/auth/register", json={"name": "Alice", "email": "alice@example.com", "password": "password123"})
    token = response.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_unauthorized_access():
    response = client.get("/api/progress")
    assert response.status_code == 401
