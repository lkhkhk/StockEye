import pytest
from pydantic import ValidationError, EmailStr
from datetime import datetime
from src.common.schemas.user import (
    UserCreate,
    UserLogin,
    UserRead,
    UserUpdate,
    Token,
    TokenData,
    TelegramRegister,
)

def test_user_create_valid():
    # Test with required fields
    user = UserCreate(username="testuser", email="test@example.com", password="password123")
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.password == "password123"
    assert user.nickname is None
    assert user.full_name is None
    assert user.role == "user"

    # Test with all fields
    user = UserCreate(
        username="adminuser",
        email="admin@example.com",
        password="adminpassword",
        nickname="Admin",
        full_name="Admin User",
        role="admin"
    )
    assert user.username == "adminuser"
    assert user.email == "admin@example.com"
    assert user.password == "adminpassword"
    assert user.nickname == "Admin"
    assert user.full_name == "Admin User"
    assert user.role == "admin"

def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(username="testuser", email="invalid-email", password="password123")

def test_user_create_missing_fields():
    with pytest.raises(ValidationError):
        UserCreate(username="testuser", email="test@example.com") # Missing password

def test_user_login_valid():
    user = UserLogin(username="testuser", password="password123")
    assert user.username == "testuser"
    assert user.password == "password123"

def test_user_login_missing_fields():
    with pytest.raises(ValidationError):
        UserLogin(username="testuser") # Missing password

def test_user_read_valid():
    now = datetime.now()
    user = UserRead(
        id=1,
        username="testuser",
        email="test@example.com",
        role="user",
        is_active=True,
        telegram_id=12345,
        created_at=now,
        updated_at=now
    )
    assert user.id == 1
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.role == "user"
    assert user.is_active is True
    assert user.telegram_id == 12345
    assert user.created_at == now
    assert user.updated_at == now

def test_user_read_missing_fields():
    with pytest.raises(ValidationError):
        UserRead(id=1, username="testuser") # Missing email, role, is_active, created_at, updated_at

def test_user_update_valid():
    user = UserUpdate(email="new@example.com", is_active=False)
    assert user.email == "new@example.com"
    assert user.is_active is False
    assert user.telegram_id is None

def test_user_update_invalid_email():
    with pytest.raises(ValidationError):
        UserUpdate(email="invalid-email")

def test_token_valid():
    now = datetime.now()
    user_read = UserRead(
        id=1,
        username="testuser",
        email="test@example.com",
        role="user",
        is_active=True,
        created_at=now,
        updated_at=now
    )
    token = Token(access_token="some_token", token_type="bearer", user=user_read)
    assert token.access_token == "some_token"
    assert token.token_type == "bearer"
    assert token.user.username == "testuser"

def test_token_missing_fields():
    now = datetime.now()
    user_read = UserRead(
        id=1,
        username="testuser",
        email="test@example.com",
        role="user",
        is_active=True,
        created_at=now,
        updated_at=now
    )
    with pytest.raises(ValidationError):
        Token(access_token="some_token", user=user_read) # Missing token_type

def test_token_data_valid():
    token_data = TokenData(username="testuser", role="user", user_id=1)
    assert token_data.username == "testuser"
    assert token_data.role == "user"
    assert token_data.user_id == 1

    token_data = TokenData() # All optional
    assert token_data.username is None

def test_telegram_register_valid():
    reg = TelegramRegister(telegram_id="12345", is_active=True)
    assert reg.telegram_id == "12345"
    assert reg.is_active is True

def test_telegram_register_missing_fields():
    with pytest.raises(ValidationError):
        TelegramRegister(telegram_id="12345") # Missing is_active
