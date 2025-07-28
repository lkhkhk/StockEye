import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from src.api.tests.helpers import create_test_user, get_auth_headers
from src.api.schemas.user import UserRead, Token

# --- Registration Tests ---

def test_register_user_success(client: TestClient, db: Session):
    # Given
    username = f"testuser_{uuid4().hex}"
    email = f"{username}@test.com"
    password = "password123"

    # When
    response = client.post("/users/register", json={"username": username, "email": email, "password": password})

    # Then
    assert response.status_code == 200
    data = UserRead.parse_obj(response.json())
    assert data.username == username
    assert data.email == email

def test_register_user_duplicate_username(client: TestClient, db: Session):
    # Given
    user = create_test_user(db)

    # When
    response = client.post("/users/register", json={"username": user.username, "email": f"new_{user.email}", "password": "new_password"})

    # Then
    assert response.status_code == 400
    assert "Username or email already registered" in response.json()["detail"]

# --- Login Tests ---

def test_login_user_success(client: TestClient, db: Session):
    # Given
    user = create_test_user(db)

    # When
    response = client.post("/users/login", json={"username": user.username, "password": "password123"})

    # Then
    assert response.status_code == 200
    data = Token.parse_obj(response.json())
    assert data.token_type == "bearer"

def test_login_user_not_found(client: TestClient, db: Session):
    # When
    response = client.post("/users/login", json={"username": "nonexistent", "password": "password"})

    # Then
    assert response.status_code == 401

def test_login_user_wrong_password(client: TestClient, db: Session):
    # Given
    user = create_test_user(db)

    # When
    response = client.post("/users/login", json={"username": user.username, "password": "wrongpassword"})

    # Then
    assert response.status_code == 401

# --- Get/Update Me Tests ---

def test_get_me_success(client: TestClient, db: Session):
    # Given
    user = create_test_user(db)
    headers = get_auth_headers(user)

    # When
    response = client.get("/users/me", headers=headers)

    # Then
    assert response.status_code == 200
    data = UserRead.parse_obj(response.json())
    assert data.username == user.username

def test_get_me_unauthenticated(client: TestClient):
    # When
    response = client.get("/users/me")
    # Then
    assert response.status_code == 403

def test_update_me_success(client: TestClient, db: Session):
    # Given
    user = create_test_user(db)
    headers = get_auth_headers(user)
    new_email = f"updated_{user.email}"

    # When
    response = client.put("/users/me", json={"email": new_email}, headers=headers)

    # Then
    assert response.status_code == 200
    data = UserRead.parse_obj(response.json())
    assert data.email == new_email

# --- Telegram Registration Tests ---

def test_telegram_register_new_user(client: TestClient, db: Session):
    # Given
    telegram_id = 123456789012345678 # A large integer within BIGINT range

    # When
    response = client.put("/users/telegram_register", json={"telegram_id": telegram_id, "is_active": True})

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "registered"
    assert data["is_active"] is True

def test_telegram_register_update_user(client: TestClient, db: Session):
    # Given
    user = create_test_user(db)
    new_telegram_id = 987654321098765432 # Another large integer within BIGINT range
    user.telegram_id = new_telegram_id
    db.commit()

    # When
    response = client.put("/users/telegram_register", json={"telegram_id": new_telegram_id, "is_active": False})

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "updated"
    assert data["is_active"] is False

# --- Stats and Admin Tests ---

def test_get_user_stats_success(client: TestClient, db: Session):
    # Given
    user = create_test_user(db)

    # When
    response = client.get(f"/users/stats/{user.id}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user.id
    assert "trade_count" in data

def test_get_user_stats_not_found(client: TestClient):
    # When
    response = client.get("/users/stats/99999")
    # Then
    assert response.status_code == 404

def test_get_all_users_as_admin(client: TestClient, db: Session):
    # Given
    admin_user = create_test_user(db, role="admin")
    headers = get_auth_headers(admin_user)
    create_test_user(db) # Create another user

    # When
    response = client.get("/users/", headers=headers)

    # Then
    assert response.status_code == 200
    assert len(response.json()) >= 2

def test_get_all_users_as_user(client: TestClient, db: Session):
    # Given
    user = create_test_user(db, role="user")
    headers = get_auth_headers(user)

    # When
    response = client.get("/users/", headers=headers)

    # Then
    assert response.status_code == 403