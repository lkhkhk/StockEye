from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from src.api.db import get_db
from src.api.models.watchlist import WatchList
from pydantic import BaseModel
from typing import List

router = APIRouter()

class WatchListItem(BaseModel):
    user_id: int
    symbol: str

class WatchListResponse(BaseModel):
    watchlist: List[str]

@router.post("/watchlist/add")
def add_to_watchlist(item: WatchListItem, db: Session = Depends(get_db)):
    exists = db.query(WatchList).filter_by(user_id=item.user_id, symbol=item.symbol).first()
    if exists:
        return {"message": "이미 관심 목록에 있는 종목입니다."}
    db.add(WatchList(user_id=item.user_id, symbol=item.symbol))
    db.commit()
    return {"message": "종목이 관심 목록에 추가되었습니다."}

@router.get("/watchlist/get/{user_id}", response_model=WatchListResponse)
def get_watchlist(user_id: int, db: Session = Depends(get_db)):
    rows = db.query(WatchList).filter_by(user_id=user_id).all()
    return {"watchlist": [row.symbol for row in rows]}

@router.post("/watchlist/remove")
def remove_from_watchlist(item: WatchListItem, db: Session = Depends(get_db)):
    row = db.query(WatchList).filter_by(user_id=item.user_id, symbol=item.symbol).first()
    if not row:
        return {"message": "관심 목록에 없는 종목입니다."}
    db.delete(row)
    db.commit()
    return {"message": "종목이 관심 목록에서 제거되었습니다."} 