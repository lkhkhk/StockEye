import pytest
from unittest.mock import patch
from src.common.services.user_service import UserService
from src.common.schemas.user import UserCreate, UserUpdate
from src.common.tests.unit.conftest import TestUser

@pytest.fixture
def user_service():
    with patch('src.common.models.user.User', TestUser), \
         patch('src.common.services.user_service.User', TestUser):
        yield UserService()

def test_update_user(db_session, user_service):
    # 1. 사용자 생성
    user_create = UserCreate(
        username="testuser",
        email="test@example.com",
        password="password",
        nickname="tester"
    )
    created_user = user_service.create_user(db_session, user_create)
    assert created_user is not None
    assert created_user.notification_preferences == {"telegram": True, "email": False} # 기본값 확인

    # 2. 사용자 업데이트 (설정 변경)
    new_preferences = {"telegram": False, "email": True}
    user_update = UserUpdate(
        notification_preferences=new_preferences
    )
    
    updated_user = user_service.update_user(db_session, created_user.id, user_update)
    
    assert updated_user is not None
    assert updated_user.notification_preferences == new_preferences
    
    # DB에서 다시 조회하여 확인
    db_user = user_service.get_user_by_id(db_session, created_user.id)
    assert db_user.notification_preferences == new_preferences

def test_update_user_partial(db_session, user_service):
    # 1. 사용자 생성
    user_create = UserCreate(
        username="testuser2",
        email="test2@example.com",
        password="password"
    )
    created_user = user_service.create_user(db_session, user_create)
    
    # 2. 사용자 업데이트 (이메일만 변경, 설정은 유지)
    user_update = UserUpdate(
        email="updated@example.com"
    )
    
    updated_user = user_service.update_user(db_session, created_user.id, user_update)
    
    assert updated_user.email == "updated@example.com"
    assert updated_user.notification_preferences == {"telegram": True, "email": False} # 기본값 유지

def test_update_user_not_found(db_session, user_service):
    user_update = UserUpdate(notification_preferences={})
    result = user_service.update_user(db_session, 999, user_update)
    assert result is None
