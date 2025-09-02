import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from fastapi import FastAPI
from sqlalchemy.orm import Session
import datetime

from src.api.routers.user import router as user_router, get_auth_service, get_user_service
from src.api.auth.jwt_handler import get_current_active_user
from src.common.database.db_connector import get_db
from src.common.models.user import User
from src.api.services.auth_service import AuthService
from src.api.services.user_service import UserService
from src.common.schemas.user import UserCreate, UserUpdate, TelegramRegister, UserRead, Token

# --- Test Setup ---

app = FastAPI()

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_auth_service():
    return MagicMock(spec=AuthService)

@pytest.fixture
def mock_user_service():
    return MagicMock(spec=UserService)

@pytest.fixture
def mock_current_user():
    now = datetime.datetime.now()
    return User(
        id=1, 
        username="testuser", 
        email="test@test.com", 
        role="user", 
        is_active=True,
        created_at=now,
        updated_at=now,
        telegram_id=12345
    )

@pytest.fixture
def client(mock_db_session, mock_auth_service, mock_user_service, mock_current_user):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_current_active_user] = lambda: mock_current_user
    app.include_router(user_router)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# --- Test Cases ---

def test_register_user(client, mock_auth_service):
    now = datetime.datetime.now()
    user_data = UserCreate(username="newuser", email="new@test.com", password="newpass")
    mock_auth_service.create_user.return_value = User(id=2, username="newuser", email="new@test.com", role="user", is_active=True, created_at=now, updated_at=now)
    response = client.post("/users/register", json=user_data.model_dump())
    assert response.status_code == 200
    assert response.json()["username"] == "newuser"

def test_login_user(client, mock_auth_service, mock_current_user):
    login_data = {"username": "testuser", "password": "testpass"}
    # The login service returns a dict with the token and user model
    mock_auth_service.login_user.return_value = {"access_token": "fake-token", "token_type": "bearer", "user": mock_current_user}
    response = client.post("/users/login", json=login_data) # Use json instead of data
    assert response.status_code == 200
    assert response.json()["access_token"] == "fake-token"

def test_get_current_user_info(client, mock_auth_service, mock_current_user):
    mock_auth_service.get_user_by_id.return_value = mock_current_user
    response = client.get("/users/me")
    assert response.status_code == 200
    assert response.json()["username"] == mock_current_user.username

def test_update_current_user(client, mock_auth_service, mock_db_session, mock_current_user):
    update_data = UserUpdate(email="updated@test.com")
    mock_auth_service.get_user_by_id.return_value = mock_current_user
    response = client.put("/users/me", json=update_data.model_dump(exclude_unset=True))
    assert response.status_code == 200
    mock_db_session.commit.assert_called_once()

def test_telegram_register_new_user(client, mock_user_service, mock_db_session):
    register_data = TelegramRegister(telegram_id="12345", is_active=True)
    mock_user_service.get_user_by_telegram_id.return_value = None
    mock_user_service.create_user_from_telegram.return_value = User(id=2, telegram_id=12345, is_active=True)
    response = client.put("/users/telegram_register", json=register_data.model_dump())
    assert response.status_code == 200
    assert response.json()["result"] == "registered"

def test_get_user_by_telegram_id(client, mock_user_service, mock_current_user):
    mock_user_service.get_user_by_telegram_id.return_value = mock_current_user
    response = client.get(f"/users/telegram/{mock_current_user.telegram_id}")
    assert response.status_code == 200
    assert response.json()["username"] == mock_current_user.username

def test_get_user_stats(client, mock_auth_service, mock_db_session, mock_current_user):
    mock_auth_service.get_user_by_id.return_value = mock_current_user
    mock_db_session.query.return_value.filter.return_value.count.side_effect = [5, 10] # trade_count, prediction_count
    response = client.get(f"/users/stats/{mock_current_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["trade_count"] == 5
    assert data["prediction_count"] == 10

def test_get_all_users_as_admin(client, mock_db_session, mock_current_user):
    mock_current_user.role = "admin"
    mock_db_session.query.return_value.offset.return_value.limit.return_value.all.return_value = [mock_current_user]
    response = client.get("/users/")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_get_all_users_not_admin(client, mock_current_user):
    mock_current_user.role = "user"
    response = client.get("/users/")
    assert response.status_code == 403
