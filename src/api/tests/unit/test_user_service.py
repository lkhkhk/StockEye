import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from src.api.services.user_service import UserService
from src.common.schemas.user import UserCreate
from src.common.models.user import User

# Fixture for a mock database session
@pytest.fixture
def mock_db():
    # MOCK: SQLAlchemy Session 객체
    # SQLAlchemy Session의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    return MagicMock(spec=Session)

# Test cases for UserService class methods
def test_get_user_by_telegram_id_found(mock_db):
    user_service = UserService()
    # MOCK: User 모델 객체
    # User 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_user = MagicMock(spec=User, id=1, telegram_id=12345, username="telegramuser")
    # mock_db.query().filter().first() 호출 시 mock_user를 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    user = user_service.get_user_by_telegram_id(mock_db, 12345)

    # mock_db.query (MagicMock)가 User 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(User)
    # mock_db.query().filter (MagicMock)가 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.assert_called_once()
    assert user.telegram_id == 12345

def test_get_user_by_telegram_id_not_found(mock_db):
    user_service = UserService()
    # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.first.return_value = None

    user = user_service.get_user_by_telegram_id(mock_db, 99999)

    assert user is None

def test_create_user_from_telegram_success(mock_db):
    user_service = UserService()
    
    # MOCK: User 클래스
    # User 생성자를 모의하여 실제 객체 생성 대신 mock_user_instance를 반환하도록 설정합니다.
    with patch('src.api.services.user_service.User') as MockUser:
        # MagicMock: User 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
        mock_user_instance = MockUser.return_value
        mock_user_instance.id = 2
        mock_user_instance.telegram_id = 54321
        mock_user_instance.username = "telegram_new"
        mock_user_instance.first_name = "Telegram"
        mock_user_instance.last_name = "User"

        # MOCK: mock_db.add, mock_db.commit, mock_db.refresh
        # mock_db.add (MagicMock) 호출 시 None을 반환하도록 설정합니다.
        mock_db.add.return_value = None
        # mock_db.commit (MagicMock) 호출 시 None을 반환하도록 설정합니다.
        mock_db.commit.return_value = None
        # mock_db.refresh (MagicMock) 호출 시 입력된 객체를 그대로 반환하도록 설정하여 refresh를 모의합니다.
        mock_db.refresh.side_effect = lambda x: x

        user = user_service.create_user_from_telegram(mock_db, 54321, "telegram_new", "Telegram", "User")

        # mock_db.add (MagicMock)가 mock_user_instance 인자로 한 번 호출되었는지 확인합니다.
        mock_db.add.assert_called_once_with(mock_user_instance)
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()
        # mock_db.refresh (MagicMock)가 mock_user_instance 인자로 한 번 호출되었는지 확인합니다.
        mock_db.refresh.assert_called_once_with(mock_user_instance)
        assert user.telegram_id == 54321
        assert user.username == "telegram_new"

def test_create_user_from_telegram_db_exception(mock_db):
    user_service = UserService()
    # mock_db.add (MagicMock) 호출 시 Exception을 발생시키도록 설정합니다.
    mock_db.add.side_effect = Exception("DB Error")

    # MOCK: User 클래스
    # User 생성자를 모의하여 실제 객체 생성 대신 모의 객체를 반환하도록 설정합니다.
    with patch('src.api.services.user_service.User') as MockUser:
        with pytest.raises(Exception) as exc_info:
            user_service.create_user_from_telegram(mock_db, 54321, "telegram_new", "Telegram", "User")
        assert "DB Error" in str(exc_info.value)
        # mock_db.add (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.add.assert_called_once()
        # mock_db.rollback (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.rollback.assert_called_once()
        # mock_db.commit (MagicMock)이 호출되지 않았는지 확인합니다.
        mock_db.commit.assert_not_called()

def test_get_user_by_id_found(mock_db):
    user_service = UserService()
    # MOCK: User 모델 객체
    # User 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_user = MagicMock(spec=User, id=1, username="iduser")
    # mock_db.query().filter().first() 호출 시 mock_user를 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    user = user_service.get_user_by_id(mock_db, 1)

    # mock_db.query (MagicMock)가 User 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(User)
    # mock_db.query().filter (MagicMock)가 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.assert_called_once()
    assert user.id == 1

def test_get_user_by_id_not_found(mock_db):
    user_service = UserService()
    # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.first.return_value = None

    user = user_service.get_user_by_id(mock_db, 999)

    assert user is None

def test_get_user_by_username_found(mock_db):
    user_service = UserService()
    # MOCK: User 모델 객체
    # User 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_user = MagicMock(spec=User, id=1, username="testuser")
    # mock_db.query().filter().first() 호출 시 mock_user를 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    user = user_service.get_user_by_username(mock_db, "testuser")

    # mock_db.query (MagicMock)가 User 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(User)
    # mock_db.query().filter (MagicMock)가 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.assert_called_once()
    assert user.username == "testuser"

def test_get_user_by_username_not_found(mock_db):
    user_service = UserService()
    # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.first.return_value = None

    user = user_service.get_user_by_username(mock_db, "nonexistent")

    assert user is None

def test_get_user_by_email_found(mock_db):
    user_service = UserService()
    # MOCK: User 모델 객체
    # User 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_user = MagicMock(spec=User, id=1, email="test@example.com")
    # mock_db.query().filter().first() 호출 시 mock_user를 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    user = user_service.get_user_by_email(mock_db, "test@example.com")

    # mock_db.query (MagicMock)가 User 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(User)
    # mock_db.query().filter (MagicMock)가 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.assert_called_once()
    assert user.email == "test@example.com"

def test_get_user_by_email_not_found(mock_db):
    user_service = UserService()
    # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.first.return_value = None

    user = user_service.get_user_by_email(mock_db, "nonexistent@example.com")

    assert user is None