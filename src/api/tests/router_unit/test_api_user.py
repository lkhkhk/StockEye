import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.orm import Session
from src.api.main import app
from src.common.database.db_connector import get_db
from src.common.schemas.user import UserCreate, UserLogin, UserRead, UserUpdate, TelegramRegister, Token
from src.common.models.user import User
from src.api.routers.user import router, get_auth_service, get_user_service
from src.api.services.auth_service import AuthService
from src.api.services.user_service import UserService
from src.api.auth.jwt_handler import create_access_token, get_current_active_user
from datetime import timedelta

# Include the router in the test app
app.include_router(router)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_db_session():
    db = MagicMock(spec=Session)
    yield db
    app.dependency_overrides.clear()

@pytest.fixture
def mock_auth_service():
    service = MagicMock(spec=AuthService)
    yield service
    app.dependency_overrides.clear()

@pytest.fixture
def mock_user_service():
    service = MagicMock(spec=UserService)
    yield service
    app.dependency_overrides.clear()

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.hashed_password = "hashed_password"
    user.role = "user"
    user.is_active = True
    user.telegram_id = None
    return user

@pytest.fixture
def mock_admin_user():
    admin_user = MagicMock(spec=User)
    admin_user.id = 2
    admin_user.username = "adminuser"
    admin_user.email = "admin@example.com"
    admin_user.hashed_password = "hashed_admin_password"
    admin_user.role = "admin"
    admin_user.is_active = True
    admin_user.telegram_id = None
    return admin_user

# --- POST /users/register tests ---

@pytest.mark.asyncio
async def test_register_user_success(client, mock_db_session, mock_auth_service, mock_user):
    # GIVEN
    user_create = UserCreate(username="newuser", email="new@example.com", password="password123")
    mock_auth_service.create_user.return_value = mock_user

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    # WHEN
    response = client.post("/users/register", json=user_create.model_dump())

    # THEN
    assert response.status_code == 200
    assert response.json()["username"] == mock_user.username
    mock_auth_service.create_user.assert_called_once_with(
        db=mock_db_session,
        username=user_create.username,
        email=user_create.email,
        password=user_create.password,
        role=user_create.role
    )

# --- POST /users/login tests ---

@pytest.mark.asyncio
async def test_login_user_success(client, mock_db_session, mock_auth_service, mock_user):
    # GIVEN
    user_login = UserLogin(username="testuser", password="password123")
    mock_auth_service.login_user.return_value = {
        "access_token": "fake_token",
        "token_type": "bearer",
        "user": UserRead.model_validate(mock_user)
    }

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    # WHEN
    response = client.post("/users/login", json=user_login.model_dump())

    # THEN
    assert response.status_code == 200
    assert response.json()["access_token"] == "fake_token"
    mock_auth_service.login_user.assert_called_once_with(
        db=mock_db_session,
        username=user_login.username,
        password=user_login.password
    )

# --- GET /users/me tests ---

@pytest.mark.asyncio
async def test_get_current_user_info_success(client, mock_db_session, mock_auth_service, mock_user):
    # GIVEN
    mock_auth_service.get_user_by_id.return_value = mock_user

    # Mock get_current_active_user dependency
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    # WHEN
    response = client.get("/users/me")

    # THEN
    assert response.status_code == 200
    assert response.json()["username"] == mock_user.username
    mock_auth_service.get_user_by_id.assert_called_once_with(mock_db_session, mock_user.id)

# --- PUT /users/telegram_register tests ---

@pytest.mark.asyncio
async def test_telegram_register_new_user_success(client, mock_db_session, mock_user_service):
    # GIVEN
    telegram_id = 12345
    register_data = TelegramRegister(telegram_id=str(telegram_id), is_active=True)

    mock_user_service.get_user_by_telegram_id.return_value = None # User not found
    mock_user_service.create_user_from_telegram.return_value = MagicMock(spec=User, id=1, telegram_id=telegram_id, is_active=True)

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    # WHEN
    response = client.put("/users/telegram_register", json=register_data.model_dump())

    # THEN
    assert response.status_code == 200
    assert response.json() == {"result": "registered", "is_active": True}
    mock_user_service.get_user_by_telegram_id.assert_called_once_with(mock_db_session, telegram_id)
    mock_user_service.create_user_from_telegram.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_register_existing_user_update_success(client, mock_db_session, mock_user_service):
    # GIVEN
    telegram_id = 12345
    register_data = TelegramRegister(telegram_id=str(telegram_id), is_active=False)

    existing_user = MagicMock(spec=User, id=1, telegram_id=telegram_id, is_active=True)
    mock_user_service.get_user_by_telegram_id.return_value = existing_user # User found

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    # WHEN
    response = client.put("/users/telegram_register", json=register_data.model_dump())

    # THEN
    assert response.status_code == 200
    assert response.json() == {"result": "updated", "is_active": False}
    mock_user_service.get_user_by_telegram_id.assert_called_once_with(mock_db_session, telegram_id)
    assert existing_user.is_active == False # Verify attribute updated
    mock_db_session.commit.assert_called_once()
    mock_user_service.create_user_from_telegram.assert_not_called()
