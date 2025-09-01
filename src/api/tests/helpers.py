from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from src.common.models.user import User
from src.api.auth.jwt_handler import create_access_token, get_password_hash
from datetime import timedelta


def create_test_user(db: Session, role: str = "user", is_active: bool = True, telegram_id: int = None) -> User:
    """테스트용 사용자를 생성하고 DB에 저장합니다."""
    unique_id = uuid4().hex
    hashed_password = get_password_hash("password123") # 테스트용 비밀번호 해싱
    user = User(
        username=f"test_{unique_id}",
        email=f"test_{unique_id}@example.com",
        hashed_password=hashed_password,
        role=role,
        is_active=is_active,
        telegram_id=telegram_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_auth_headers(user: User) -> dict[str, str]:
    """사용자 객체로부터 인증 헤더를 생성합니다."""
    # jwt_handler의 create_access_token 함수를 직접 사용
    access_token_expires = timedelta(minutes=30)
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id},
        expires_delta=access_token_expires
    )
    return {"Authorization": f"Bearer {token}"}