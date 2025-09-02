from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.common.models.user import User
from src.common.schemas.user import UserCreate
from src.api.auth.password_utils import get_password_hash
import logging

logger = logging.getLogger(__name__)

class UserService:
    def get_user_by_id(self, db: Session, user_id: int):
        logger.debug(f"get_user_by_id 호출: user_id={user_id}")
        return db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, db: Session, username: str):
        logger.debug(f"get_user_by_username 호출: username={username}")
        return db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, db: Session, email: str):
        logger.debug(f"get_user_by_email 호출: email={email}")
        return db.query(User).filter(User.email == email).first()

    def get_user_by_telegram_id(self, db: Session, telegram_id: int):
        logger.debug(f"get_user_by_telegram_id 호출: telegram_id={telegram_id}")
        return db.query(User).filter(User.telegram_id == telegram_id).first()

    def create_user(self, db: Session, user: UserCreate):
        logger.debug(f"create_user 호출: username={user.username}, email={user.email}")
        hashed_password = get_password_hash(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            nickname=user.nickname,
            full_name=user.full_name
        )
        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.info(f"사용자 생성 성공: username={user.username}, id={db_user.id}")
            return db_user
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"사용자 생성 실패: {e}", exc_info=True)
            raise

    def create_user_from_telegram(self, db: Session, telegram_id: int, username: str, first_name: str, last_name: str):
        logger.debug(f"create_user_from_telegram 호출: telegram_id={telegram_id}, username={username}")
        full_name = f"{first_name} {last_name}".strip()
        db_user = User(
            telegram_id=telegram_id,
            username=username,
            nickname=username,
            full_name=full_name
        )
        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.info(f"텔레그램 사용자 생성 성공: telegram_id={telegram_id}, id={db_user.id}")
            return db_user
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"텔레그램 사용자 생성 실패: {e}", exc_info=True)
            raise

def get_user_service():
    return UserService()