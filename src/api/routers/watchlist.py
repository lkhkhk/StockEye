# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from src.api.db import get_db
from src.api.models.watchlist import WatchList
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

class WatchListItem(BaseModel):
    user_id: int
    symbol: str

@router.post("/add", tags=["watchlist"])
def add_to_watchlist(item: WatchListItem, db: Session = Depends(get_db)):
    exists = db.query(WatchList).filter_by(user_id=item.user_id, symbol=item.symbol).first()
    if exists:
        return {"message": "이미 관심 목록에 있는 종목입니다."}
    db.add(WatchList(user_id=item.user_id, symbol=item.symbol))
    db.commit()
    return {"message": "종목이 관심 목록에 추가되었습니다."}

@router.get("/get/{user_id}", tags=["watchlist"])
def get_watchlist(user_id: int, db: Session = Depends(get_db)):
    rows = db.query(WatchList).filter_by(user_id=user_id).all()
    return {"watchlist": [row.symbol for row in rows]}

@router.post("/remove", tags=["watchlist"])
def remove_from_watchlist(item: WatchListItem, db: Session = Depends(get_db)):
    row = db.query(WatchList).filter_by(user_id=item.user_id, symbol=item.symbol).first()
    if not row:
        return {"message": "관심 목록에 없는 종목입니다."}
    db.delete(row)
    db.commit()
    return {"message": "종목이 관심 목록에서 제거되었습니다."} 