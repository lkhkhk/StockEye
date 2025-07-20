import logging
from sqlalchemy.orm import Session
from src.api.models.user import User
from src.api.auth.jwt_handler import verify_password, get_password_hash, create_access_token
from fastapi import HTTPException, status
from datetime import timedelta
from src.api.schemas.user import UserRead

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        pass

    def authenticate_user(self, db: Session, username: str, password: str):
        """사용자 인증"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False
        if not verify_password(password, user.password_hash):
            return False
        return user

    def create_user(self, db: Session, username: str, email: str, password: str, role: str = "user"):
        """새 사용자 생성"""
        try:
            # 중복 확인
            existing_user = db.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            if existing_user:
                logger.error(f"이미 등록된 사용자: {username}, {email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username or email already registered"
                )
            # 비밀번호 해싱
            hashed_password = get_password_hash(password)
            # 새 사용자 생성
            user = User(
                username=username,
                email=email,
                password_hash=hashed_password,
                role=role
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"사용자 생성 실패: {str(e)}", exc_info=True)
            raise

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