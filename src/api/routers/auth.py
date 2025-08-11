from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from src.common.db_connector import get_db
# 아래 라인에서 UserService, get_user_service 임포트 제거
# from src.api.services.user_service import UserService, get_user_service 
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
    # get_user_service 의존성을 제거하고 함수 내에서 직접 생성
    _=Depends(verify_bot_secret_key)
):
    """
    텔레그램 ID로 사용자를 찾아 JWT 토큰을 발급합니다. (봇 전용)
    """
    # 함수 내에서 지역적으로 임포트하여 순환 참조 해결
    from src.api.services.user_service import UserService
    user_service = UserService()

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