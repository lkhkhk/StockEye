from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from src.common.models.stock_master import StockMaster
from src.common.database.db_connector import get_db
from typing import List
from src.common.services.stock_master_service import StockMasterService
from src.common.services.market_data_service import MarketDataService
import logging

router = APIRouter(prefix="/symbols", tags=["symbols"])
logger = logging.getLogger(__name__)

def get_stock_master_service():
    return StockMasterService()

def get_market_data_service():
    return MarketDataService()

@router.get("/", response_model=dict)
def get_all_symbols(limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    total_count = db.query(StockMaster).count()
    rows = db.query(StockMaster).offset(offset).limit(limit).all()
    return {
        "items": [{"symbol": r.symbol, "name": r.name, "market": r.market} for r in rows],
        "total_count": total_count
    }

@router.get("/search", response_model=dict)
def search_symbols(query: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), stock_master_service: StockMasterService = Depends(get_stock_master_service)):
    # 기존의 직접 쿼리 대신 StockMasterService의 search_stocks 메서드 사용
    stocks = stock_master_service.search_stocks(query, db, limit=limit, offset=offset)
    total_count = db.query(StockMaster).filter(StockMaster.name.ilike(f"%{query}%") | StockMaster.symbol.ilike(f"%{query}%")).count()
    return {
        "items": [{"symbol": r.symbol, "name": r.name, "market": r.market} for r in stocks],
        "total_count": total_count
    }

@router.get("/{symbol_code}", response_model=dict) # New endpoint
def get_symbol_by_code(symbol_code: str, db: Session = Depends(get_db), stock_master_service: StockMasterService = Depends(get_stock_master_service)):
    stock = stock_master_service.get_stock_by_symbol(symbol_code, db)
    if stock is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="종목을 찾을 수 없습니다.")
    return {"symbol": stock.symbol, "name": stock.name, "market": stock.market}

@router.get("/{symbol}/current_price_and_change", response_model=dict)
def get_current_price_and_change_api(symbol: str, db: Session = Depends(get_db), market_data_service: MarketDataService = Depends(get_market_data_service)):
    price_data = market_data_service.get_current_price_and_change(symbol, db)
    if price_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock price data not found")
    return price_data