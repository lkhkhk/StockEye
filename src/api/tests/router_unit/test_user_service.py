import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from src.api.services.user_service import UserService
from src.common.models.user import User

@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy DB session."""
    return MagicMock(spec=Session)

@pytest.fixture
def user_service():
    """Provide a UserService instance."""
    return UserService()

@patch('os.getenv')
def test_create_user_from_telegram_admin_role(mock_getenv, user_service, mock_db_session):
    """Test that admin role is assigned when telegram_id matches TELEGRAM_ADMIN_ID."""
    mock_getenv.return_value = "123456789" # Simulate TELEGRAM_ADMIN_ID being set

    # Mock the query to simulate no existing user
    mock_db_session.query.return_value.first.return_value = None

    telegram_id = 123456789
    username = "test_admin_user"
    first_name = "Admin"
    last_name = "User"

    user = user_service.create_user_from_telegram(mock_db_session, telegram_id, username, first_name, last_name)

    assert user.role == "admin"
    mock_db_session.add.assert_called_once_with(user)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(user)

@patch('os.getenv')
def test_create_user_from_telegram_user_role_mismatch(mock_getenv, user_service, mock_db_session):
    """Test that user role is assigned when telegram_id does not match TELEGRAM_ADMIN_ID."""
    mock_getenv.return_value = "987654321" # Simulate TELEGRAM_ADMIN_ID being set but not matching

    # Mock the query to simulate no existing user
    mock_db_session.query.return_value.first.return_value = None

    telegram_id = 123456789
    username = "test_normal_user"
    first_name = "Normal"
    last_name = "User"

    user = user_service.create_user_from_telegram(mock_db_session, telegram_id, username, first_name, last_name)

    assert user.role == "user"
    mock_db_session.add.assert_called_once_with(user)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(user)

@patch('os.getenv')
def test_create_user_from_telegram_user_role_no_admin_id(mock_getenv, user_service, mock_db_session):
    """Test that user role is assigned when TELEGRAM_ADMIN_ID is not set."""
    mock_getenv.return_value = None # Simulate TELEGRAM_ADMIN_ID not being set

    # Mock the query to simulate no existing user
    mock_db_session.query.return_value.first.return_value = None

    telegram_id = 123456789
    username = "test_no_admin_id_user"
    first_name = "NoAdmin"
    last_name = "IDUser"

    user = user_service.create_user_from_telegram(mock_db_session, telegram_id, username, first_name, last_name)

    assert user.role == "user"
    mock_db_session.add.assert_called_once_with(user)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(user)