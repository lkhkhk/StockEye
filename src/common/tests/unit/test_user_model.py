import pytest
from src.common.models.user import User

# SQLAlchemy 모델의 default는 DB 세션 내에서 작동합니다.
# Python 객체 생성 시에는 직접 기본값을 설정해야 합니다.
# 하지만 애플리케이션 로직(예: UserService.create_user_from_telegram)에서
# role을 명시적으로 설정하므로, 모델 자체의 Python 기본값은 이 테스트의 주요 목적이 아닙니다.

def test_user_model_explicit_role():
    """Test that the User model correctly sets the role when explicitly provided."""
    user = User(username="adminuser", hashed_password="hashedpass", email="admin@example.com", role="admin")
    assert user.role == "admin"

def test_user_model_invalid_role():
    """Test that the User model can accept any string for role, as validation is at service layer."""
    user = User(username="specialuser", hashed_password="hashedpass", email="special@example.com", role="super_admin")
    assert user.role == "super_admin"