import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
import random # random 임포트 추가

from src.api.tests.helpers import create_test_user, get_auth_headers
from src.api.schemas.user import UserRead, Token
from src.api.services.user_service import UserService # UserService 임포트

# --- Registration Tests ---

def test_register_user_success(client: TestClient, real_db: Session):
    # Given
    username = f"testuser_{uuid4().hex}"
    email = f"{username}@test.com"
    password = "password123"

    # When
    response = client.post("/users/register", json={"username": username, "email": email, "password": password})

    # Then
    assert response.status_code == 200
    data = UserRead.model_validate(response.json())
    assert data.username == username
    assert data.email == email

def test_register_user_duplicate_username(client: TestClient, real_db: Session):
    # Given
    user = create_test_user(real_db)

    # When
    response = client.post("/users/register", json={"username": user.username, "email": f"new_{user.email}", "password": "new_password"})

    # Then
    assert response.status_code == 400
    assert "Username or email already registered" in response.json()["detail"]

# --- Login Tests ---

def test_login_user_success(client: TestClient, real_db: Session):
    # Given
    user = create_test_user(real_db)

    # When
    response = client.post("/users/login", json={"username": user.username, "password": "password123"})

    # Then
    assert response.status_code == 200
    data = Token.model_validate(response.json())
    assert data.token_type == "bearer"

def test_login_user_not_found(client: TestClient, real_db: Session):
    # When
    response = client.post("/users/login", json={"username": "nonexistent", "password": "password"})

    # Then
    assert response.status_code == 401

def test_login_user_wrong_password(client: TestClient, real_db: Session):
    # Given
    user = create_test_user(real_db)

    # When
    response = client.post("/users/login", json={"username": user.username, "password": "wrongpassword"})

    # Then
    assert response.status_code == 401

# --- Get/Update Me Tests ---

def test_get_me_success(client: TestClient, real_db: Session):
    # Given
    user = create_test_user(real_db)
    headers = get_auth_headers(user)

    # When
    response = client.get("/users/me", headers=headers)

    # Then
    assert response.status_code == 200
    data = UserRead.model_validate(response.json())
    assert data.username == user.username

def test_get_me_unauthenticated(client: TestClient):
    # When
    response = client.get("/users/me")
    # Then
    assert response.status_code == 403

def test_update_me_success(client: TestClient, real_db: Session):
    # Given
    user = create_test_user(real_db)
    headers = get_auth_headers(user)
    new_email = f"updated_{user.email}"

    # When
    response = client.put("/users/me", json={"email": new_email}, headers=headers)

    # Then
    assert response.status_code == 200
    data = UserRead.model_validate(response.json())
    assert data.email == new_email

# --- Telegram Registration Tests ---

def test_telegram_register_new_user(client: TestClient, real_db: Session):
    # Given
    telegram_id = random.randint(1000000000, 9999999999) # 고유한 텔레그램 ID 생성
    user_service = UserService() # UserService 인스턴스 생성

    # When
    response = client.put("/users/telegram_register", json={"telegram_id": telegram_id, "is_active": True})

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "registered"
    assert data["is_active"] is True
    # DB에서 사용자 조회하여 telegram_id가 올바르게 설정되었는지 확인
    registered_user = user_service.get_user_by_telegram_id(real_db, telegram_id)
    assert registered_user is not None
    assert registered_user.telegram_id == telegram_id

def test_telegram_register_update_user(client: TestClient, real_db: Session):
    # Given
    telegram_id = random.randint(1000000000, 9999999999) # 고유한 텔레그램 ID 생성
    user = create_test_user(real_db, telegram_id=telegram_id) # telegram_id를 가진 사용자 생성
    user_service = UserService() # UserService 인스턴스 생성

    # When
    response = client.put("/users/telegram_register", json={"telegram_id": telegram_id, "is_active": False})

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "updated"
    assert data["is_active"] is False
    # DB에서 사용자 조회하여 is_active가 올바르게 업데이트되었는지 확인
    updated_user = user_service.get_user_by_telegram_id(real_db, telegram_id)
    assert updated_user is not None
    assert updated_user.is_active is False

# --- Stats and Admin Tests ---

def test_get_user_stats_success(client: TestClient, real_db: Session):
    # Given
    user = create_test_user(real_db)

    # When
    response = client.get(f"/users/stats/{user.id}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user.id
    assert data["trade_count"] == 0 # 초기에는 0

def test_get_user_stats_not_found(client: TestClient):
    # When
    response = client.get("/users/stats/99999")
    # Then
    assert response.status_code == 404

def test_get_all_users_as_admin(client: TestClient, real_db: Session):
    # Given
    admin_user = create_test_user(real_db, role="admin")
    headers = get_auth_headers(admin_user)
    create_test_user(real_db) # Create another user

    # When
    response = client.get("/users/", headers=headers)

    # Then
    assert response.status_code == 200
    assert len(response.json()) >= 2

def test_get_all_users_as_user(client: TestClient, real_db: Session):
    # Given
    user = create_test_user(real_db, role="user")
    headers = get_auth_headers(user)

    # When
    response = client.get("/users/", headers=headers)

    # Then
    assert response.status_code == 403