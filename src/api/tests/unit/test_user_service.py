import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from src.api.services.user_service import create_user, get_user_by_username, authenticate_user, get_user_stats, UserService
from src.api.schemas.user import UserCreate
from src.api.models.user import User

# Fixture for a mock database session
@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

# Test cases for create_user function
def test_create_user_success(mock_db):
    user_create = UserCreate(username="testuser", email="test@example.com", password="password123")
    
    with patch('src.api.services.user_service.bcrypt') as mock_bcrypt:
        mock_bcrypt.hash.return_value = "hashed_password"
        with patch('src.api.services.user_service.User') as MockUser:
            mock_user_instance = MockUser.return_value
            mock_user_instance.id = 1
            mock_user_instance.username = "testuser"
            mock_user_instance.email = "test@example.com"
            mock_user_instance.password_hash = "hashed_password"

            mock_db.add.return_value = None
            mock_db.commit.return_value = None
            mock_db.refresh.side_effect = lambda x: x

            user = create_user(mock_db, user_create)

            mock_bcrypt.hash.assert_called_once_with("password123")
            mock_db.add.assert_called_once_with(mock_user_instance)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_user_instance)
            assert user.username == "testuser"
            assert user.email == "test@example.com"
            assert user.password_hash == "hashed_password"

def test_create_user_db_exception(mock_db):
    user_create = UserCreate(username="testuser", email="test@example.com", password="password123")
    mock_db.add.side_effect = Exception("DB Error")

    with patch('src.api.services.user_service.bcrypt') as mock_bcrypt:
        mock_bcrypt.hash.return_value = "hashed_password"
        with pytest.raises(Exception) as exc_info:
            create_user(mock_db, user_create)
        assert "DB Error" in str(exc_info.value)
        mock_db.add.assert_called_once()
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()

# Test cases for get_user_by_username function
def test_get_user_by_username_found(mock_db):
    mock_user = MagicMock(spec=User, id=1, username="existinguser", email="existing@example.com")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    user = get_user_by_username(mock_db, "existinguser")

    mock_db.query.assert_called_once_with(User)
    mock_db.query.return_value.filter.assert_called_once()
    assert user.username == "existinguser"

def test_get_user_by_username_not_found(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    user = get_user_by_username(mock_db, "nonexistentuser")

    assert user is None

def test_get_user_by_username_db_exception(mock_db):
    mock_db.query.side_effect = Exception("DB Error")

    user = get_user_by_username(mock_db, "testuser")

    assert user is None
    mock_db.query.assert_called_once()

# Test cases for authenticate_user function
def test_authenticate_user_success(mock_db):
    mock_user = MagicMock(spec=User, id=1, username="authuser", password_hash="hashed_password")
    
    with patch('src.api.services.user_service.get_user_by_username', return_value=mock_user) as mock_get_user_by_username:
        with patch('src.api.services.user_service.bcrypt') as mock_bcrypt:
            mock_bcrypt.verify.return_value = True

            user = authenticate_user(mock_db, "authuser", "correctpassword")

            mock_get_user_by_username.assert_called_once_with(mock_db, "authuser")
            mock_bcrypt.verify.assert_called_once_with("correctpassword", "hashed_password")
            assert user.username == "authuser"

def test_authenticate_user_incorrect_password(mock_db):
    mock_user = MagicMock(spec=User, id=1, username="authuser", password_hash="hashed_password")
    
    with patch('src.api.services.user_service.get_user_by_username', return_value=mock_user) as mock_get_user_by_username:
        with patch('src.api.services.user_service.bcrypt') as mock_bcrypt:
            mock_bcrypt.verify.return_value = False

            user = authenticate_user(mock_db, "authuser", "wrongpassword")

            mock_get_user_by_username.assert_called_once_with(mock_db, "authuser")
            mock_bcrypt.verify.assert_called_once_with("wrongpassword", "hashed_password")
            assert user is None

def test_authenticate_user_not_found(mock_db):
    with patch('src.api.services.user_service.get_user_by_username', return_value=None) as mock_get_user_by_username:
        with patch('src.api.services.user_service.bcrypt') as mock_bcrypt:
            user = authenticate_user(mock_db, "nonexistent", "password")

            mock_get_user_by_username.assert_called_once_with(mock_db, "nonexistent")
            mock_bcrypt.verify.assert_not_called()
            assert user is None

def test_authenticate_user_db_exception(mock_db):
    with patch('src.api.services.user_service.get_user_by_username', side_effect=Exception("DB Error")) as mock_get_user_by_username:
        user = authenticate_user(mock_db, "testuser", "password")

        assert user is None
        mock_get_user_by_username.assert_called_once()

# Test cases for get_user_stats function
def test_get_user_stats_success(mock_db):
    mock_user = MagicMock(spec=User, id=1, username="statsuser", email="stats@example.com", created_at="2023-01-01")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    stats = get_user_stats(mock_db, 1)

    mock_db.query.assert_called_once_with(User)
    mock_db.query.return_value.filter.assert_called_once()
    assert stats["id"] == 1
    assert stats["username"] == "statsuser"

def test_get_user_stats_not_found(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    stats = get_user_stats(mock_db, 999)

    assert stats is None

def test_get_user_stats_db_exception(mock_db):
    mock_db.query.side_effect = Exception("DB Error")

    stats = get_user_stats(mock_db, 1)

    assert stats is None
    mock_db.query.assert_called_once()

# Test cases for UserService class methods
def test_get_user_by_telegram_id_found(mock_db):
    user_service = UserService()
    mock_user = MagicMock(spec=User, id=1, telegram_id=12345, username="telegramuser")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    user = user_service.get_user_by_telegram_id(mock_db, 12345)

    mock_db.query.assert_called_once_with(User)
    mock_db.query.return_value.filter.assert_called_once()
    assert user.telegram_id == 12345

def test_get_user_by_telegram_id_not_found(mock_db):
    user_service = UserService()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    user = user_service.get_user_by_telegram_id(mock_db, 99999)

    assert user is None

def test_create_user_from_telegram_success(mock_db):
    user_service = UserService()
    
    with patch('src.api.services.user_service.User') as MockUser:
        mock_user_instance = MockUser.return_value
        mock_user_instance.id = 2
        mock_user_instance.telegram_id = 54321
        mock_user_instance.username = "telegram_new"
        mock_user_instance.first_name = "Telegram"
        mock_user_instance.last_name = "User"

        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda x: x

        user = user_service.create_user_from_telegram(mock_db, 54321, "telegram_new", "Telegram", "User")

        mock_db.add.assert_called_once_with(mock_user_instance)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_user_instance)
        assert user.telegram_id == 54321
        assert user.username == "telegram_new"

def test_create_user_from_telegram_db_exception(mock_db):
    user_service = UserService()
    mock_db.add.side_effect = Exception("DB Error")

    with patch('src.api.services.user_service.User') as MockUser:
        with pytest.raises(Exception) as exc_info:
            user_service.create_user_from_telegram(mock_db, 54321, "telegram_new", "Telegram", "User")
        assert "DB Error" in str(exc_info.value)
        mock_db.add.assert_called_once()
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()

def test_get_user_by_id_found(mock_db):
    user_service = UserService()
    mock_user = MagicMock(spec=User, id=1, username="iduser")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    user = user_service.get_user_by_id(mock_db, 1)

    mock_db.query.assert_called_once_with(User)
    mock_db.query.return_value.filter.assert_called_once()
    assert user.id == 1

def test_get_user_by_id_not_found(mock_db):
    user_service = UserService()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    user = user_service.get_user_by_id(mock_db, 999)

    assert user is None
