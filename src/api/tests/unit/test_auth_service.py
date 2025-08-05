import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from src.api.services.auth_service import AuthService
from src.api.models.user import User
from src.api.schemas.user import UserCreate, UserLogin
from src.common.exceptions import UserAlreadyExistsException, InvalidCredentialsException

class TestAuthService:
    @pytest.fixture
    def auth_service(self):
        return AuthService()

    @pytest.fixture
    def mock_db_session(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def mock_user_create_schema(self):
        return UserCreate(username="testuser", email="test@example.com", password="password123")

    @pytest.fixture
    def mock_user_login_schema(self):
        return UserLogin(username="testuser", password="password123")

    @pytest.fixture
    def mock_user_model(self):
        user = MagicMock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.password_hash = "hashed_password" # 실제 해시된 비밀번호
        return user

    @patch('src.api.services.auth_service.pwd_context.hash')
    @patch('src.api.services.auth_service.pwd_context.verify')
    def test_register_user_success(self, mock_verify, mock_hash, auth_service, mock_db_session, mock_user_create_schema, mock_user_model):
        # Given
        mock_db_session.query.return_value.filter.return_value.first.return_value = None # 사용자 없음
        mock_hash.return_value = "hashed_password"
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # When
        registered_user = auth_service.register_user(mock_db_session, mock_user_create_schema)

        # Then
        mock_db_session.query.assert_called_once_with(User)
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
        assert registered_user.username == mock_user_create_schema.username
        assert registered_user.email == mock_user_create_schema.email
        assert registered_user.password_hash == "hashed_password"

    def test_register_user_already_exists(self, auth_service, mock_db_session, mock_user_create_schema, mock_user_model):
        # Given
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user_model # 사용자 이미 존재

        # When / Then
        with pytest.raises(UserAlreadyExistsException):
            auth_service.register_user(mock_db_session, mock_user_create_schema)
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()

    @patch('src.api.services.auth_service.pwd_context.verify')
    def test_authenticate_user_success(self, mock_verify, auth_service, mock_db_session, mock_user_login_schema, mock_user_model):
        # Given
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user_model
        mock_verify.return_value = True

        # When
        authenticated_user = auth_service.authenticate_user(mock_db_session, mock_user_login_schema.username, mock_user_login_schema.password)

        # Then
        mock_db_session.query.assert_called_once_with(User)
        mock_verify.assert_called_once_with(mock_user_login_schema.password, mock_user_model.password_hash)
        assert authenticated_user == mock_user_model

    @patch('src.api.services.auth_service.pwd_context.verify')
    def test_authenticate_user_not_found(self, mock_verify, auth_service, mock_db_session, mock_user_login_schema):
        # Given
        mock_db_session.query.return_value.filter.return_value.first.return_value = None # 사용자 없음

        # When / Then
        with pytest.raises(InvalidCredentialsException):
            auth_service.authenticate_user(mock_db_session, mock_user_login_schema.username, mock_user_login_schema.password)
        mock_verify.assert_not_called()

    @patch('src.api.services.auth_service.pwd_context.verify')
    def test_authenticate_user_invalid_password(self, mock_verify, auth_service, mock_db_session, mock_user_login_schema, mock_user_model):
        # Given
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user_model
        mock_verify.return_value = False # 비밀번호 불일치

        # When / Then
        with pytest.raises(InvalidCredentialsException):
            auth_service.authenticate_user(mock_db_session, mock_user_login_schema.username, mock_user_login_schema.password)
        mock_verify.assert_called_once_with(mock_user_login_schema.password, mock_user_model.password_hash)
