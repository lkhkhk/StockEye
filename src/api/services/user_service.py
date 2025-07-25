import logging
from sqlalchemy.orm import Session
from src.api.models.user import User
from src.api.schemas.user import UserCreate
from passlib.hash import bcrypt
from typing import Optional

logger = logging.getLogger(__name__)

def create_user(db: Session, user: UserCreate):
    logger.debug(f"Attempting to create user: username={user.username}, email={user.email}")
    try:
        db_user = User(
            username=user.username,
            email=user.email,
            password_hash=bcrypt.hash(user.password)
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.debug(f"User created successfully: user_id={db_user.id}, username={db_user.username}")
        return db_user
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create user {user.username}: {str(e)}", exc_info=True)
        raise

def get_user_by_username(db: Session, username: str):
    logger.debug(f"Attempting to retrieve user by username: {username}")
    try:
        user = db.query(User).filter(User.username == username).first()
        if user:
            logger.debug(f"User found: user_id={user.id}, username={user.username}")
        else:
            logger.debug(f"User not found for username: {username}")
        return user
    except Exception as e:
        logger.error(f"Failed to retrieve user by username {username}: {str(e)}", exc_info=True)
        return None

def authenticate_user(db: Session, username: str, password: str):
    logger.debug(f"Attempting to authenticate user: username={username}")
    try:
        user = get_user_by_username(db, username)
        if user and bcrypt.verify(password, user.password_hash):
            logger.debug(f"User authenticated successfully: user_id={user.id}")
            return user
        logger.debug(f"User authentication failed for username: {username}")
        return None
    except Exception as e:
        logger.error(f"Failed to authenticate user {username}: {str(e)}", exc_info=True)
        return None

def get_user_stats(db: Session, user_id: int):
    logger.debug(f"Attempting to get user stats for user_id: {user_id}")
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User stats retrieval failed: user_id={user_id} not found")
            return None
        stats = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at
        }
        logger.debug(f"User stats retrieved for user_id={user_id}: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Failed to get user stats for user_id {user_id}: {str(e)}", exc_info=True)
        return None

class UserService:
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
        try:
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
            logger.debug(f"User created from telegram successfully: user_id={new_user.id}, telegram_id={new_user.telegram_id}")
            return new_user
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create user from telegram (telegram_id={telegram_id}): {str(e)}", exc_info=True)
            raise

