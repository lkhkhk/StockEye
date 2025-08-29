from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from src.common.models.stock_master import StockMaster
from src.common.db_connector import get_db
from typing import List
from src.common.services.stock_service import StockService

router = APIRouter(prefix="/symbols", tags=["symbols"])

def get_stock_service():
    return StockService()

@router.get("/", response_model=dict)
def get_all_symbols(limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    total_count = db.query(StockMaster).count()
    rows = db.query(StockMaster).offset(offset).limit(limit).all()
    return {
        "items": [{"symbol": r.symbol, "name": r.name, "market": r.market} for r in rows],
        "total_count": total_count
    }

@router.get("/search", response_model=dict)
def search_symbols(query: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    base_query = db.query(StockMaster).filter(StockMaster.name.ilike(f"%{query}%") | StockMaster.symbol.ilike(f"%{query}%"))
    total_count = base_query.count()
    rows = base_query.offset(offset).limit(limit).all()
    print(f"Returning rows: {rows}")
    return {
        "items": [{"symbol": r.symbol, "name": r.name, "market": r.market} for r in rows],
        "total_count": total_count
    }

@router.get("/{symbol}/current_price_and_change", response_model=dict)
def get_current_price_and_change_api(symbol: str, db: Session = Depends(get_db), stock_service: StockService = Depends(get_stock_service)):
    price_data = stock_service.get_current_price_and_change(symbol, db)
    if price_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock price data not found")
    return price_data 