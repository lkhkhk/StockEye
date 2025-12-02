import logging
from sqlalchemy.orm import Session
from src.common.models.user import User
from src.common.utils.password_utils import verify_password, get_password_hash # 변경된 임포트
from src.api.auth.jwt_handler import create_access_token
from fastapi import HTTPException, status
from datetime import timedelta
from src.common.schemas.user import UserRead
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        pass

    def authenticate_user(self, db: Session, username: str, password: str):
        """사용자 인증"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False
        if not verify_password(password, user.hashed_password):
            logger.debug(f"[AuthService] Password verification failed for {username}. Plain: {password}, Hashed in DB: {user.hashed_password}")
            return False
        return user

    def create_user(self, db: Session, username: str, email: str, password: str, role: str = "user"):
        """새로운 사용자를 생성합니다."""
        # 1. 중복 확인
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )

        # 2. 새 사용자 생성
        hashed_password = get_password_hash(password)
        logger.debug(f"[AuthService] Hashed password for {username}: {hashed_password}")
        db_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role
        )
        db.add(db_user)

        # 3. DB에 반영
        try:
            db.flush()
            db.commit()
            db.refresh(db_user)
        except IntegrityError as e:
            db.rollback()
            logger.error(f"사용자 생성 중 DB 오류 발생: {e}", exc_info=True)
            # IntegrityError는 대부분 중복 등록 시도이므로 400에러를 반환합니다.
            # (autoincrement 이슈 등 다른 원인일 수도 있습니다)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database error during user creation. May be a duplicate entry."
            )
        
        return db_user

    def login_user(self, db: Session, username: str, password: str):
        """사용자 로그인"""
        user = self.authenticate_user(db, username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 액세스 토큰 생성
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role, "user_id": user.id},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserRead.model_validate(user)
        }

    def get_user_by_id(self, db: Session, user_id: int):
        """ID로 사용자 조회"""
        return db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, db: Session, username: str):
        """사용자명으로 사용자 조회"""
        return db.query(User).filter(User.username == username).first()

    def update_user_telegram_id(self, db: Session, user_id: int, telegram_id: str):
        """사용자의 텔레그램 ID 업데이트"""
        user = self.get_user_by_id(db, user_id)
        if not user:
            logger.error(f"User not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        try:
            user.telegram_id = telegram_id
            db.commit()
            db.refresh(user)
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"텔레그램 ID 업데이트 실패: {str(e)}", exc_info=True)
            raise