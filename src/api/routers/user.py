# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from src.common.db_connector import get_db
from src.api.schemas.user import UserCreate, UserRead, UserLogin, Token, UserUpdate, TelegramRegister
from src.api.services.auth_service import AuthService
from src.api.auth.jwt_handler import get_current_active_user
from src.api.models.user import User
from src.api.models.simulated_trade import SimulatedTrade
from src.api.models.prediction_history import PredictionHistory
from typing import List

router = APIRouter(prefix="/users", tags=["users"])

def get_auth_service():
    return AuthService()

@router.post("/register", response_model=UserRead, tags=["users"])
def register_user(user: UserCreate, db: Session = Depends(get_db), auth_service: AuthService = Depends(get_auth_service)):
    """사용자 등록"""
    return auth_service.create_user(
        db=db,
        username=user.username,
        email=user.email,
        password=user.password,
        role=user.role
    )

@router.post("/login", response_model=Token, tags=["users"])
def login_user(user_credentials: UserLogin, db: Session = Depends(get_db), auth_service: AuthService = Depends(get_auth_service)):
    """사용자 로그인"""
    return auth_service.login_user(
        db=db,
        username=user_credentials.username,
        password=user_credentials.password
    )

@router.get("/me", response_model=UserRead, tags=["users"])
def get_current_user_info(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db), auth_service: AuthService = Depends(get_auth_service)):
    """현재 사용자 정보 조회"""
    user = auth_service.get_user_by_id(db, current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/me", response_model=UserRead, tags=["users"])
def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """현재 사용자 정보 업데이트"""
    user = auth_service.get_user_by_id(db, current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 업데이트할 필드들
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.telegram_id is not None:
        user.telegram_id = user_update.telegram_id
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    db.commit()
    db.refresh(user)
    return user

@router.put("/telegram_register", tags=["users"])
def telegram_register(
    register_data: TelegramRegister,
    db: Session = Depends(get_db)
):
    """텔레그램 알림 동의/해제 (telegram_id로만 처리, 인증 없음)"""
    # telegram_id를 int로 변환하여 사용
    telegram_id_int = int(register_data.telegram_id)
    user = db.query(User).filter(User.telegram_id == telegram_id_int).first()
    if not user:
        # 신규 등록: 임시 사용자 생성 (실제 서비스에서는 인증 필요)
        user = User(
            username=f"tg_{register_data.telegram_id}",
            email=f"tg_{register_data.telegram_id}@example.com",
            password_hash="dummy",
            telegram_id=telegram_id_int, # int로 변환된 값 사용
            is_active=register_data.is_active
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"result": "registered", "is_active": register_data.is_active}
    else:
        user.is_active = register_data.is_active
        db.commit()
        return {"result": "updated", "is_active": register_data.is_active}

@router.get("/stats/{user_id}", tags=["users"])
def get_user_stats(user_id: int, db: Session = Depends(get_db), auth_service: AuthService = Depends(get_auth_service)):
    """사용자 통계 조회"""
    # 사용자 존재 확인
    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 통계 계산
    trade_count = db.query(SimulatedTrade).filter(SimulatedTrade.user_id == user_id).count()
    prediction_count = db.query(PredictionHistory).filter(PredictionHistory.user_id == user_id).count()
    
    return {
        "user_id": user_id,
        "username": user.username,
        "trade_count": trade_count,
        "prediction_count": prediction_count,
        "created_at": user.created_at
    }

@router.get("/", response_model=List[UserRead], tags=["users"])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """모든 사용자 조회 (관리자만)"""
    # 관리자 권한 확인
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    users = db.query(User).offset(skip).limit(limit).all()
    return users 