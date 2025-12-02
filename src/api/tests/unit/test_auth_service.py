import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError # Import IntegrityError

# Explicitly import the module to be tested for coverage
from src.api.services import auth_service as auth_service_module

from src.api.services.auth_service import AuthService
from src.common.models.user import User
from src.common.schemas.user import UserCreate, UserLogin, UserRead
from fastapi import HTTPException

class TestAuthService:
    @pytest.fixture
    def auth_service(self):
        return AuthService()

    @pytest.fixture
    def mock_db_session(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def mock_user_create_schema(self):
        return UserCreate(username="testuser", email="test@example.com", password="password123", nickname="testnick", full_name="Test User")

    @pytest.fixture
    def mock_user_login_schema(self):
        return UserLogin(username="testuser", password="password123")

    @pytest.fixture
    def mock_user_model(self):
        user = MagicMock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.hashed_password = "hashed_password"
        user.role = "user"
        user.is_active = True
        user.notification_preferences = {"telegram": True, "email": False}
        return user

    @patch('src.api.services.auth_service.get_password_hash')
    def test_create_user_success(self, mock_get_password_hash, auth_service, mock_db_session, mock_user_create_schema):
        # Given
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        mock_get_password_hash.return_value = "hashed_password"

        # When
        registered_user = auth_service.create_user(mock_db_session, username=mock_user_create_schema.username, email=mock_user_create_schema.email, password=mock_user_create_schema.password, role='user')

        # Then
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
        assert registered_user.username == mock_user_create_schema.username

    def test_create_user_already_exists(self, auth_service, mock_db_session, mock_user_create_schema, mock_user_model):
        # Given
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user_model

        # When / Then
        with pytest.raises(HTTPException):
            auth_service.create_user(mock_db_session, username=mock_user_create_schema.username, email=mock_user_create_schema.email, password=mock_user_create_schema.password)

    @patch('src.api.services.auth_service.verify_password', return_value=True)
    def test_authenticate_user_success(self, mock_verify_password, auth_service, mock_db_session, mock_user_model):
        # Given
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user_model

        # When
        authenticated_user = auth_service.authenticate_user(mock_db_session, "testuser", "password123")

        # Then
        assert authenticated_user == mock_user_model

    def test_authenticate_user_not_found(self, auth_service, mock_db_session):
        # Given
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # When
        result = auth_service.authenticate_user(mock_db_session, "wronguser", "password123")

        # Then
        assert result is False

    @patch('src.api.services.auth_service.verify_password', return_value=False)
    def test_authenticate_user_invalid_password(self, mock_verify_password, auth_service, mock_db_session, mock_user_model):
        # Given
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user_model

        # When
        result = auth_service.authenticate_user(mock_db_session, "testuser", "wrongpassword")

        # Then
        assert result is False

    @patch('src.api.services.auth_service.create_access_token', return_value="test_token")
    def test_login_user_success(self, mock_create_token, auth_service, mock_db_session, mock_user_model):
        # Given
        with patch.object(auth_service, 'authenticate_user', return_value=mock_user_model) as mock_authenticate:
            # When
            result = auth_service.login_user(mock_db_session, "testuser", "password123")

            # Then
            mock_authenticate.assert_called_once_with(mock_db_session, "testuser", "password123")
            mock_create_token.assert_called_once()
            assert result["access_token"] == "test_token"
            assert result["token_type"] == "bearer"
            assert isinstance(result["user"], UserRead)

    def test_login_user_failure(self, auth_service, mock_db_session):
        # Given
        with patch.object(auth_service, 'authenticate_user', return_value=False) as mock_authenticate:
            # When / Then
            with pytest.raises(HTTPException) as exc_info:
                auth_service.login_user(mock_db_session, "testuser", "wrongpassword")
            assert exc_info.value.status_code == 401

    def test_update_user_telegram_id_success(self, auth_service, mock_db_session, mock_user_model):
        # Given
        user_id = 1
        telegram_id = "123456789"
        with patch.object(auth_service, 'get_user_by_id', return_value=mock_user_model) as mock_get_user:
            # When
            updated_user = auth_service.update_user_telegram_id(mock_db_session, user_id, telegram_id)

            # Then
            mock_get_user.assert_called_once_with(mock_db_session, user_id)
            assert mock_user_model.telegram_id == telegram_id
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once_with(mock_user_model)
            assert updated_user == mock_user_model

    def test_update_user_telegram_id_not_found(self, auth_service, mock_db_session):
        # Given
        user_id = 999
        telegram_id = "123456789"
        with patch.object(auth_service, 'get_user_by_id', return_value=None) as mock_get_user:
            # When / Then
            with pytest.raises(HTTPException) as exc_info:
                auth_service.update_user_telegram_id(mock_db_session, user_id, telegram_id)
            assert exc_info.value.status_code == 404

    @patch('src.api.services.auth_service.get_password_hash')
    def test_create_user_integrity_error(self, mock_get_password_hash, auth_service, mock_db_session, mock_user_create_schema):
        # Given
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        mock_get_password_hash.return_value = "hashed_password"
        mock_db_session.commit.side_effect = IntegrityError("test_integrity_error", {}, None)

        # When / Then
        with pytest.raises(HTTPException) as exc_info:
            auth_service.create_user(mock_db_session, username=mock_user_create_schema.username, email=mock_user_create_schema.email, password=mock_user_create_schema.password, role='user')
        assert exc_info.value.status_code == 400
        assert "Database error during user creation" in exc_info.value.detail
        mock_db_session.rollback.assert_called_once()

    @patch('src.api.services.auth_service.create_access_token', return_value="test_token")
    def test_login_user_success_user_read_validation(self, mock_create_token, auth_service, mock_db_session, mock_user_model):
        # Given
        with patch.object(auth_service, 'authenticate_user', return_value=mock_user_model) as mock_authenticate:
            # When
            result = auth_service.login_user(mock_db_session, "testuser", "password123")

            # Then
            mock_authenticate.assert_called_once_with(mock_db_session, "testuser", "password123")
            mock_create_token.assert_called_once()
            assert result["access_token"] == "test_token"
            assert result["token_type"] == "bearer"
            assert isinstance(result["user"], UserRead) # Explicitly check UserRead type

    def test_update_user_telegram_id_exception(self, auth_service, mock_db_session, mock_user_model):
        # Given
        user_id = 1
        telegram_id = "123456789"
        with patch.object(auth_service, 'get_user_by_id', return_value=mock_user_model) as mock_get_user:
            mock_db_session.commit.side_effect = Exception("Database connection lost")

            # When / Then
            with pytest.raises(Exception) as exc_info:
                auth_service.update_user_telegram_id(mock_db_session, user_id, telegram_id)
            assert "Database connection lost" in str(exc_info.value) and exc_info.type == Exception
            mock_db_session.rollback.assert_called_once()
