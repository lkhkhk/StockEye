
import pytest
from src.common.models.user import User

def test_user_model_creation():
    """
    User 모델 객체가 정상적으로 생성되고,
    속성이 올바르게 설정되는지 테스트합니다.
    """
    # Given
    username = "testuser"
    hashed_password = "testpassword"
    email = "test@example.com"
    nickname = "tester"
    full_name = "Test User"
    role = "admin"
    is_active = False
    telegram_id = 123456789

    # When
    user = User(
        username=username,
        hashed_password=hashed_password,
        email=email,
        nickname=nickname,
        full_name=full_name,
        role=role,
        is_active=is_active,
        telegram_id=telegram_id
    )

    # Then
    assert user.username == username
    assert user.hashed_password == hashed_password
    assert user.email == email
    assert user.nickname == nickname
    assert user.full_name == full_name
    assert user.role == role
    assert user.is_active == is_active
    assert user.telegram_id == telegram_id
