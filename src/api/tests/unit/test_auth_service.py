import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from src.api.services.auth_service import AuthService
from src.common.models.user import User
from src.common.schemas.user import UserCreate, UserLogin
from src.common.utils.exceptions import UserAlreadyExistsException, InvalidCredentialsException
from fastapi import HTTPException # Added this import

class TestAuthService:
    @pytest.fixture
    def auth_service(self):
        return AuthService()

    @pytest.fixture
    def mock_db_session(self):
        # 모의 DB 세션 픽스처
        # MagicMock: SQLAlchemy Session 객체를 모의합니다. 동기적으로 동작합니다.
        return MagicMock(spec=Session)

    @pytest.fixture
    def mock_user_create_schema(self):
        # 모의 UserCreate 스키마 픽스처
        # UserCreate 스키마의 인스턴스를 모의합니다. 동기적으로 동작합니다.
        return UserCreate(username="testuser", email="test@example.com", password="password123")

    @pytest.fixture
    def mock_user_login_schema(self):
        # 모의 UserLogin 스키마 픽스처
        # UserLogin 스키마의 인스턴스를 모의합니다. 동기적으로 동작합니다.
        return UserLogin(username="testuser", password="password123")

    @pytest.fixture
    def mock_user_model(self):
        # 모의 User 모델 픽스처
        # User 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
        user = MagicMock()
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.hashed_password = "hashed_password" # 실제 해시된 비밀번호
        user.role = "user"
        user.is_active = True
        return user

    @patch('src.api.services.auth_service.get_password_hash') # MOCK: get_password_hash 함수
    @patch('src.api.services.auth_service.verify_password') # MOCK: verify_password 함수
    def test_register_user_success(self, mock_verify, mock_hash, auth_service, mock_db_session, mock_user_create_schema, mock_user_model):
        # Given
        # mock_db_session.query().filter().first() 호출 시 None을 반환하도록 설정하여 사용자가 없음을 모의합니다.
        mock_db_session.query.return_value.filter.return_value.first.return_value = None 
        # mock_hash (MagicMock) 호출 시 "hashed_password"를 반환하도록 설정합니다.
        mock_hash.return_value = "hashed_password"
        # mock_db_session.add (MagicMock) 호출 시 None을 반환하도록 설정합니다.
        mock_db_session.add.return_value = None
        # mock_db_session.commit (MagicMock) 호출 시 None을 반환하도록 설정합니다.
        mock_db_session.commit.return_value = None
        # mock_db_session.refresh (MagicMock) 호출 시 None을 반환하도록 설정합니다.
        mock_db_session.refresh.return_value = None

        # When
        registered_user = auth_service.create_user(mock_db_session, username=mock_user_create_schema.username, email=mock_user_create_schema.email, password=mock_user_create_schema.password)

        # Then
        # mock_db_session.query (MagicMock)가 User 모델로 한 번 호출되었는지 확인합니다.
        mock_db_session.query.assert_called_once_with(User)
        # mock_db_session.add (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db_session.add.assert_called_once()
        # mock_db_session.commit (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db_session.commit.assert_called_once()
        # mock_db_session.refresh (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db_session.refresh.assert_called_once()
        assert registered_user.username == mock_user_create_schema.username
        assert registered_user.email == mock_user_create_schema.email
        assert registered_user.hashed_password == "hashed_password"

    def test_register_user_already_exists(self, auth_service, mock_db_session, mock_user_create_schema, mock_user_model):
        # Given
        # mock_db_session.query().filter().first() 호출 시 mock_user_model을 반환하도록 설정하여 사용자가 이미 존재함을 모의합니다.
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user_model 

        # When / Then
        # HTTPException이 발생하는지 확인합니다.
        with pytest.raises(HTTPException): 
            auth_service.create_user(mock_db_session, username=mock_user_create_schema.username, email=mock_user_create_schema.email, password=mock_user_create_schema.password)
        # mock_db_session.add (MagicMock)가 호출되지 않았는지 확인합니다.
        mock_db_session.add.assert_not_called()
        # mock_db_session.commit (MagicMock)가 호출되지 않았는지 확인합니다.
        mock_db_session.commit.assert_not_called()

    @patch('src.api.services.auth_service.verify_password') # MOCK: verify_password 함수
    def test_authenticate_user_success(self, mock_verify, auth_service, mock_db_session, mock_user_login_schema, mock_user_model):
        # Given
        # mock_db_session.query().filter().first() 호출 시 mock_user_model을 반환하도록 설정합니다.
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user_model
        # mock_verify (MagicMock) 호출 시 True를 반환하도록 설정합니다.
        mock_verify.return_value = True

        # When
        authenticated_user = auth_service.authenticate_user(mock_db_session, mock_user_login_schema.username, mock_user_login_schema.password)

        # Then
        # mock_db_session.query (MagicMock)가 User 모델로 한 번 호출되었는지 확인합니다.
        mock_db_session.query.assert_called_once_with(User)
        # mock_verify (MagicMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        mock_verify.assert_called_once_with(mock_user_login_schema.password, mock_user_model.hashed_password)
        assert authenticated_user == mock_user_model

    @patch('src.api.services.auth_service.verify_password') # MOCK: verify_password 함수
    def test_authenticate_user_not_found(self, mock_verify, auth_service, mock_db_session, mock_user_login_schema):
        # Given
        # mock_db_session.query().filter().first() 호출 시 None을 반환하도록 설정하여 사용자가 없음을 모의합니다.
        mock_db_session.query.return_value.filter.return_value.first.return_value = None 

        # When
        result = auth_service.authenticate_user(mock_db_session, mock_user_login_schema.username, mock_user_login_schema.password)

        # Then
        assert result is False 
        # mock_verify (MagicMock)가 호출되지 않았는지 확인합니다.
        mock_verify.assert_not_called()

    @patch('src.api.services.auth_service.verify_password') # MOCK: verify_password 함수
    def test_authenticate_user_invalid_password(self, mock_verify, auth_service, mock_db_session, mock_user_login_schema, mock_user_model):
        # Given
        # mock_db_session.query().filter().first() 호출 시 mock_user_model을 반환하도록 설정합니다.
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user_model
        # mock_verify (MagicMock) 호출 시 False를 반환하도록 설정하여 비밀번호 불일치를 모의합니다.
        mock_verify.return_value = False 

        # When
        result = auth_service.authenticate_user(mock_db_session, mock_user_login_schema.username, mock_user_login_schema.password)

        # Then
        assert result is False 
        # mock_verify (MagicMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        mock_verify.assert_called_once_with(mock_user_login_schema.password, mock_user_model.hashed_password)