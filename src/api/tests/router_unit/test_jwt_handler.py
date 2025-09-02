import pytest
from jose import jwt, JWTError
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials

from src.api.auth import jwt_handler
from src.api.auth import password_utils
from src.common.models.user import User
from src.api.services.user_service import UserService

# Test constants
TEST_SECRET_KEY = "test_secret_key"
ALGORITHM = "HS256"

@pytest.fixture(autouse=True)
def override_env_vars(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET_KEY)

# 1. Password Hashing and Verification Tests

def test_password_hashing_and_verification():
    password = "plain_password"
    hashed_password = password_utils.get_password_hash(password)
    assert hashed_password != password
    assert password_utils.verify_password(password, hashed_password)

# 2. Access Token Creation and Verification Tests

def test_create_and_verify_access_token():
    data = {"sub": "testuser", "user_id": 1}
    token = jwt_handler.create_access_token(data)
    payload = jwt_handler.verify_token(token)
    assert payload["sub"] == data["sub"]

def test_verify_token_expired():
    data = {"sub": "testuser"}
    expired_token = jwt_handler.create_access_token(data, expires_delta=timedelta(minutes=-1))
    with pytest.raises(HTTPException) as exc_info:
        jwt_handler.verify_token(expired_token)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

# 3. Current User Dependency Tests

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def mock_user_service():
    return MagicMock(spec=UserService)

def test_get_current_active_user_success(mock_db_session, mock_user_service):
    user_id = 1
    username = "testuser"
    mock_user = User(id=user_id, username=username, is_active=True)
    mock_user_service.get_user_by_id.return_value = mock_user
    
    token_data = {"sub": username, "user_id": user_id}
    token = jwt_handler.create_access_token(token_data)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    
    # 직접 함수를 호출하며 mock 객체를 전달
    user = jwt_handler.get_current_active_user(credentials=credentials, db=mock_db_session, user_service=mock_user_service)
    
    assert user.id == user_id
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, user_id)

def test_get_current_active_user_inactive(mock_db_session, mock_user_service):
    user_id = 1
    username = "inactiveuser"
    mock_user = User(id=user_id, username=username, is_active=False)
    mock_user_service.get_user_by_id.return_value = mock_user
    
    token_data = {"sub": username, "user_id": user_id}
    token = jwt_handler.create_access_token(token_data)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        jwt_handler.get_current_active_user(credentials=credentials, db=mock_db_session, user_service=mock_user_service)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

def test_get_current_active_user_not_found(mock_db_session, mock_user_service):
    user_id = 999
    username = "ghostuser"
    mock_user_service.get_user_by_id.return_value = None
    
    token_data = {"sub": username, "user_id": user_id}
    token = jwt_handler.create_access_token(token_data)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        jwt_handler.get_current_active_user(credentials=credentials, db=mock_db_session, user_service=mock_user_service)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

# 4. Admin User Dependency Tests

def test_get_current_active_admin_user_success():
    admin_user = User(username="admin", role="admin", is_active=True)
    result = jwt_handler.get_current_active_admin_user(current_user=admin_user)
    assert result == admin_user

def test_get_current_active_admin_user_not_admin():
    non_admin_user = User(username="testuser", role="user", is_active=True)
    with pytest.raises(HTTPException) as exc_info:
        jwt_handler.get_current_active_admin_user(current_user=non_admin_user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
