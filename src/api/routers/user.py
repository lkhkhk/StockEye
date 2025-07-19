from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.api.schemas.user import UserCreate, UserRead
from src.api.services.user_service import create_user, get_user_by_username
from src.api.models.user import User
from src.api.db import get_db
from src.api.schemas.user import UserLogin
from src.api.services.user_service import authenticate_user, get_user_stats

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserRead)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="이미 존재하는 사용자입니다.")
    return create_user(db, user)

@router.post("/register", response_model=UserRead)
def register_user_register(user: UserCreate, db: Session = Depends(get_db)):
    return register_user(user, db)

@router.post("/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    auth_user = authenticate_user(db, user.username, user.password)
    if not auth_user:
        raise HTTPException(status_code=401, detail="인증 실패")
    return {"id": auth_user.id, "username": auth_user.username, "email": auth_user.email}

@router.get("/stats/{user_id}")
def user_stats(user_id: int, db: Session = Depends(get_db)):
    stats = get_user_stats(db, user_id)
    if not stats:
        raise HTTPException(status_code=404, detail="사용자 없음")
    return stats 