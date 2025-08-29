# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from src.common.db_connector import get_db
from src.common.models.watchlist import Watchlist
from src.common.schemas.watchlist import WatchlistCreate, Watchlist as WatchlistSchema
from pydantic import BaseModel
from typing import List
import logging
from src.api.services.user_service import UserService # UserService 임포트
from src.common.services.stock_service import StockService # StockService 임포트

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

class WatchListItem(BaseModel):
    user_id: int
    symbol: str

def get_user_service():
    return UserService()

def get_stock_service():
    return StockService()

@router.post("/add", tags=["watchlist"])
def add_to_watchlist(item: WatchListItem, db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service), stock_service: StockService = Depends(get_stock_service)):
    logger.debug(f"관심 종목 추가 시도: user_id={item.user_id}, symbol={item.symbol}")
    # 사용자 존재 여부 확인
    user = user_service.get_user_by_id(db, item.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 종목 존재 여부 확인
    stock = stock_service.get_stock_by_symbol(item.symbol, db)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    exists = db.query(Watchlist).filter(Watchlist.user_id == item.user_id, Watchlist.symbol == item.symbol).first()
    if exists:
        logger.info(f"관심 종목 이미 존재: user_id={item.user_id}, symbol={item.symbol}")
        return {"message": "이미 관심 목록에 있는 종목입니다."}
    try:
        db.add(Watchlist(user_id=item.user_id, symbol=item.symbol))
        db.commit()
        logger.info(f"관심 종목 추가 성공: user_id={item.user_id}, symbol={item.symbol}")
        return {"message": "종목이 관심 목록에 추가되었습니다."}
    except Exception as e:
        db.rollback()
        logger.error(f"관심 종목 추가 실패: user_id={item.user_id}, symbol={item.symbol}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"관심 종목 추가 실패: {e}")

@router.get("/get/{user_id}", tags=["watchlist"])
def get_watchlist(user_id: int, db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service)):
    logger.debug(f"관심 종목 조회 시도: user_id={user_id}")
    # 사용자 존재 여부 확인
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    rows = db.query(Watchlist).filter(Watchlist.user_id == user_id).all()
    watchlist_symbols = [row.symbol for row in rows]
    logger.debug(f"관심 종목 조회 성공: user_id={user_id}, {len(watchlist_symbols)}개 종목.")
    return {"watchlist": watchlist_symbols}

@router.post("/remove", tags=["watchlist"])
def remove_from_watchlist(item: WatchListItem, db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service)):
    logger.debug(f"관심 종목 제거 시도: user_id={item.user_id}, symbol={item.symbol}")
    # 사용자 존재 여부 확인
    user = user_service.get_user_by_id(db, item.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    row = db.query(Watchlist).filter(Watchlist.user_id == item.user_id, Watchlist.symbol == item.symbol).first()
    if not row:
        logger.info(f"관심 목록에 없는 종목: user_id={item.user_id}, symbol={item.symbol}")
        return {"message": "관심 목록에 없는 종목입니다."}
    try:
        db.delete(row)
        db.commit()
        logger.info(f"관심 종목 제거 성공: user_id={item.user_id}, symbol={item.symbol}")
        return {"message": "종목이 관심 목록에서 제거되었습니다."}
    except Exception as e:
        db.rollback()
        logger.error(f"관심 종목 제거 실패: user_id={item.user_id}, symbol={item.symbol}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"관심 종목 제거 실패: {e}")