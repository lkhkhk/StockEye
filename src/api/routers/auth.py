from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from src.common.database.db_connector import get_db
from src.common.services.user_service import UserService, get_user_service
from src.api.auth.jwt_handler import create_access_token
from pydantic import BaseModel
import os

router = APIRouter(prefix="/auth", tags=["auth"])

# --- Schemas ---
class TokenRequest(BaseModel):
    telegram_id: int

# --- Security ---
API_KEY_HEADER = APIKeyHeader(name="X-Bot-Secret-Key")
BOT_SECRET_KEY = os.getenv("BOT_SECRET_KEY")

async def verify_bot_secret_key(api_key: str = Security(API_KEY_HEADER)):
    """요청 헤더의 X-Bot-Secret-Key가 서버의 환경변수와 일치하는지 확인"""
    if not BOT_SECRET_KEY or api_key != BOT_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bot secret key"
        )

# --- Endpoints ---
@router.post("/bot/token")
def get_token_for_bot(
    token_request: TokenRequest,
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
    _=Depends(verify_bot_secret_key)
):
    """
    텔레그램 ID로 사용자를 찾아 JWT 토큰을 발급합니다. (봇 전용)
    """
    user = user_service.get_user_by_telegram_id(db, token_request.telegram_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with telegram_id {token_request.telegram_id} not found"
        )
    
    # JWT 토큰 생성
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/bot/token/admin")
def get_admin_token_for_bot(
    token_request: TokenRequest,
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
    _=Depends(verify_bot_secret_key)
):
    """
    관리자 권한을 가진 사용자에 대해 JWT 토큰을 발급합니다. (봇 전용)
    """
    user = user_service.get_user_by_telegram_id(db, token_request.telegram_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with telegram_id {token_request.telegram_id} not found"
        )
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not an admin"
        )
    
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": "admin"}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}