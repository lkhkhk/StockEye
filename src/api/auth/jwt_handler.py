from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import logging
from sqlalchemy.orm import Session

from src.common.models.user import User
from src.common.database.db_connector import get_db
from src.common.services.user_service import UserService

logger = logging.getLogger(__name__)

# JWT 설정
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 보안
security = HTTPBearer()

def get_user_service():
    return UserService()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    signing_secret_key = os.getenv("JWT_SECRET_KEY")
    logger.debug(f"JWT_SECRET_KEY used for signing: {signing_secret_key}") # DEBUG LINE for signing
    encoded_jwt = jwt.encode(to_encode, signing_secret_key, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    try:
        jwt_secret_key = os.getenv("JWT_SECRET_KEY")
        logger.debug(f"JWT_SECRET_KEY used for verification: {jwt_secret_key}") # DEBUG LINE for verification
        payload = jwt.decode(token, jwt_secret_key, algorithms=[ALGORITHM])
        logger.debug(f"JWT Payload: {payload}")
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError as e:
        logger.error(f"JWTError during token verification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_active_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service)):
    """현재 활성 사용자 정보 반환"""
    # --- TEMPORARY DEBUGGING: Bypass JWT validation ---
    # logger.warning("Bypassing JWT validation for debugging purposes!")
    # dummy_user = User(id=1, username="debug_user", email="debug@example.com", hashed_password="dummy_hash", is_active=True, role="user")
    # return dummy_user
    # --- END TEMPORARY DEBUGGING ---

    token = credentials.credentials
    payload = verify_token(token)
    user_id: int = payload.get("user_id")

    user = user_service.get_user_by_id(db, user_id)
    logger.debug(f"get_current_active_user: user_id={user_id}, user={user}, is_active={user.is_active if user else 'N/A'}")
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user

def get_current_active_admin_user(current_user: User = Depends(get_current_active_user)):
    """현재 활성 관리자 사용자 정보 반환"""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user