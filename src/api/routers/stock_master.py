from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.api.models.stock_master import StockMaster
from src.common.db_connector import get_db
from typing import List
from src.api.services.stock_service import StockService

router = APIRouter(prefix="/symbols", tags=["symbols"])

def get_stock_service():
    return StockService()

@router.get("/", response_model=List[dict])
def get_all_symbols(db: Session = Depends(get_db)):
    rows = db.query(StockMaster).all()
    return [{"symbol": r.symbol, "name": r.name, "market": r.market} for r in rows]

@router.get("/search", response_model=List[dict])
def search_symbols(query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    rows = db.query(StockMaster).filter(StockMaster.name.ilike(f"%{query}%") | StockMaster.symbol.ilike(f"%{query}%")).all()
    return [{"symbol": r.symbol, "name": r.name, "market": r.market} for r in rows]

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from src.api.models.stock_master import StockMaster
from src.common.db_connector import get_db
from typing import List
from src.api.services.stock_service import StockService

router = APIRouter(prefix="/symbols", tags=["symbols"])

def get_stock_service():
    return StockService()

@router.get("/", response_model=List[dict])
def get_all_symbols(db: Session = Depends(get_db)):
    rows = db.query(StockMaster).all()
    return [{"symbol": r.symbol, "name": r.name, "market": r.market} for r in rows]

@router.get("/search", response_model=List[dict])
def search_symbols(query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    rows = db.query(StockMaster).filter(StockMaster.name.ilike(f"%{query}%") | StockMaster.symbol.ilike(f"%{query}%")).all()
    return [{"symbol": r.symbol, "name": r.name, "market": r.market} for r in rows]

@router.get("/{symbol}/current_price_and_change", response_model=dict)
def get_current_price_and_change_api(symbol: str, db: Session = Depends(get_db), stock_service: StockService = Depends(get_stock_service)):
    price_data = stock_service.get_current_price_and_change(symbol, db)
    if price_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock price data not found")
    return price_data 