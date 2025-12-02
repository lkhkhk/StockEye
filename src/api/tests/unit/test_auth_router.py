import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from src.api.routers.auth import router as auth_router, verify_bot_secret_key
from src.common.services.user_service import get_user_service, UserService
from src.common.database.db_connector import get_db
from src.common.models.user import User

# --- Test Setup ---

app = FastAPI()

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_user_service():
    return MagicMock(spec=UserService)

async def override_verify_bot_secret_key():
    return True

@pytest.fixture
def client(mock_db_session, mock_user_service):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[verify_bot_secret_key] = override_verify_bot_secret_key
    app.include_router(auth_router)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# --- Test Cases ---

def test_get_token_for_bot_success(client, mock_db_session, mock_user_service):
    # GIVEN
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = 'testuser'
    mock_user.role = 'user'
    mock_user.is_admin = False # Default for non-admin token

    mock_user_service.get_user_by_telegram_id.return_value = mock_user
    telegram_id = 12345
    headers = {"X-Bot-Secret-Key": "test_key"}

    # WHEN
    with patch('src.api.routers.auth.create_access_token', return_value="fake_token") as mock_create_token:
        response = client.post("/auth/bot/token", json={"telegram_id": telegram_id}, headers=headers)

    # THEN
    assert response.status_code == 200
    assert response.json() == {"access_token": "fake_token", "token_type": "bearer"}
    mock_user_service.get_user_by_telegram_id.assert_called_once_with(mock_db_session, telegram_id)
    mock_create_token.assert_called_once()

def test_get_token_for_bot_user_not_found(client, mock_user_service):
    # GIVEN
    mock_user_service.get_user_by_telegram_id.return_value = None
    telegram_id = 99999
    headers = {"X-Bot-Secret-Key": "test_key"}

    # WHEN
    response = client.post("/auth/bot/token", json={"telegram_id": telegram_id}, headers=headers)

    # THEN
    assert response.status_code == 404

@pytest.fixture
def client_for_key_test(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    if verify_bot_secret_key in app.dependency_overrides:
        del app.dependency_overrides[verify_bot_secret_key]
    app.include_router(auth_router)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@patch.dict(os.environ, {"BOT_SECRET_KEY": "real_secret_key"})
def test_get_token_for_bot_invalid_key(client_for_key_test):
    # GIVEN
    headers = {"X-Bot-Secret-Key": "invalid_key"}
    
    # WHEN
    response = client_for_key_test.post("/auth/bot/token", json={"telegram_id": 123}, headers=headers)

    # THEN
    assert response.status_code == 401

@patch.dict(os.environ, {"BOT_SECRET_KEY": "real_secret_key"})
def test_get_token_for_bot_no_key(client_for_key_test):
    # GIVEN: No headers

    # WHEN
    response = client_for_key_test.post("/auth/bot/token", json={"telegram_id": 123})

    # THEN
    assert response.status_code == 401


# --- Admin Token Tests ---

def test_get_admin_token_for_bot_success(client, mock_db_session, mock_user_service):
    # GIVEN
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = 'adminuser'
    mock_user.role = 'admin'
    mock_user.is_admin = True

    mock_user_service.get_user_by_telegram_id.return_value = mock_user
    telegram_id = 12345
    headers = {"X-Bot-Secret-Key": "test_key"}

    # WHEN
    with patch('src.api.routers.auth.create_access_token', return_value="fake_admin_token") as mock_create_token:
        response = client.post("/auth/bot/token/admin", json={"telegram_id": telegram_id}, headers=headers)

    # THEN
    assert response.status_code == 200
    assert response.json() == {"access_token": "fake_admin_token", "token_type": "bearer"}
    mock_user_service.get_user_by_telegram_id.assert_called_once_with(mock_db_session, telegram_id)
    mock_create_token.assert_called_once()

def test_get_admin_token_for_bot_not_admin(client, mock_user_service):
    # GIVEN
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = 'normaluser'
    mock_user.role = 'user'
    mock_user.is_admin = False

    mock_user_service.get_user_by_telegram_id.return_value = mock_user
    telegram_id = 12345
    headers = {"X-Bot-Secret-Key": "test_key"}

    # WHEN
    response = client.post("/auth/bot/token/admin", json={"telegram_id": telegram_id}, headers=headers)

    # THEN
    assert response.status_code == 403
    assert response.json()["detail"] == "User is not an admin"

def test_get_admin_token_for_bot_user_not_found(client, mock_user_service):
    # GIVEN
    mock_user_service.get_user_by_telegram_id.return_value = None
    telegram_id = 99999
    headers = {"X-Bot-Secret-Key": "test_key"}

    # WHEN
    response = client.post("/auth/bot/token/admin", json={"telegram_id": telegram_id}, headers=headers)

    # THEN
    assert response.status_code == 404
    assert response.json()["detail"] == f"User with telegram_id {telegram_id} not found"
