from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.api.models.stock_master import StockMaster
from src.api.db import get_db
from typing import List

router = APIRouter(prefix="/symbols", tags=["symbols"])

@router.get("/", response_model=List[dict])
def get_all_symbols(db: Session = Depends(get_db)):
    rows = db.query(StockMaster).all()
    return [{"symbol": r.symbol, "name": r.name, "market": r.market} for r in rows]

@router.get("/search", response_model=List[dict])
def search_symbols(query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    rows = db.query(StockMaster).filter(StockMaster.name.ilike(f"%{query}%") | StockMaster.symbol.ilike(f"%{query}%")).all()
    return [{"symbol": r.symbol, "name": r.name, "market": r.market} for r in rows] 