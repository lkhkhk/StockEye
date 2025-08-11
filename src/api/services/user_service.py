import logging
import os
from sqlalchemy.orm import Session
from src.api.models.user import User
from src.api.schemas.user import UserCreate
from passlib.hash import bcrypt
from typing import Optional

logger = logging.getLogger(__name__)

# ... (기존 함수들은 그대로 유지) ...

class UserService:
    # ... (다른 메서드들은 그대로 유지) ...

    def get_user_by_telegram_id(self, db: Session, telegram_id: int) -> Optional[User]:
        logger.debug(f"Attempting to retrieve user by telegram_id: {telegram_id}")
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            logger.debug(f"User found by telegram_id: user_id={user.id}, telegram_id={telegram_id}")
        else:
            logger.debug(f"User not found for telegram_id: {telegram_id}")
        return user

    def create_user_from_telegram(self, db: Session, telegram_id: int, username: str, first_name: str, last_name: str) -> User:
        logger.debug(f"Attempting to create user from telegram: telegram_id={telegram_id}, username={username}")
        
        # 관리자 ID 환경 변수 확인
        admin_telegram_id = os.getenv("TELEGRAM_ADMIN_ID")
        user_role = "user" # 기본값
        if admin_telegram_id and str(telegram_id) == admin_telegram_id:
            user_role = "admin"
            logger.info(f"Admin user detected. Assigning 'admin' role to telegram_id: {telegram_id}")

        try:
            new_user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                role=user_role  # 역할(role) 설정 추가
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            logger.debug(f"User created from telegram successfully: user_id={new_user.id}, telegram_id={new_user.telegram_id}, role={new_user.role}")
            return new_user
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create user from telegram (telegram_id={telegram_id}): {str(e)}", exc_info=True)
            raise

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        logger.debug(f"Attempting to retrieve user by id: {user_id}")
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            logger.debug(f"User found by id: user_id={user.id}")
        else:
            logger.debug(f"User not found for id: {user_id}")
        return user

# ... (파일의 나머지 부분은 그대로 유지) ...

# 전체 파일 내용을 붙여넣기 위해 기존의 다른 함수/클래스 코드가 이 자리에 와야 합니다.
# 이 예시에서는 핵심 수정사항만 보여드립니다.