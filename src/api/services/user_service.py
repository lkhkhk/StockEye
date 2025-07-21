import logging
from sqlalchemy.orm import Session
from src.api.models.user import User
from src.api.schemas.user import UserCreate
from passlib.hash import bcrypt
from typing import Optional

logger = logging.getLogger(__name__)

def create_user(db: Session, user: UserCreate):
    try:
        db_user = User(
            username=user.username,
            email=user.email,
            password_hash=bcrypt.hash(user.password)
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        logger.error(f"사용자 생성 실패: {str(e)}", exc_info=True)
        raise

def get_user_by_username(db: Session, username: str):
    try:
        return db.query(User).filter(User.username == username).first()
    except Exception as e:
        logger.error(f"사용자명으로 조회 실패: {str(e)}", exc_info=True)
        return None

def authenticate_user(db: Session, username: str, password: str):
    try:
        user = get_user_by_username(db, username)
        if user and bcrypt.verify(password, user.password_hash):
            return user
        return None
    except Exception as e:
        logger.error(f"사용자 인증 실패: {str(e)}", exc_info=True)
        return None

def get_user_stats(db: Session, user_id: int):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"사용자 통계 조회 실패: user_id={user_id} 없음")
            return None
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at
        }
    except Exception as e:
        logger.error(f"사용자 통계 조회 실패: {str(e)}", exc_info=True)
        return None

class UserService:
    def get_user_by_telegram_id(self, db: Session, telegram_id: int) -> Optional[User]:
        """텔레그램 ID로 사용자 정보를 조회합니다."""
        return db.query(User).filter(User.telegram_id == telegram_id).first()

    def create_user_from_telegram(self, db: Session, telegram_id: int, username: str, first_name: str, last_name: str) -> User:
        """텔레그램 정보로 새 사용자를 생성합니다."""
        new_user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

user_service = UserService() 