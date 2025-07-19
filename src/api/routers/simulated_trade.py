from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.api.db import get_db
from src.api.models.simulated_trade import SimulatedTrade
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter()

class SimulatedTradeItem(BaseModel):
    user_id: int
    symbol: str
    trade_type: str  # 'buy' or 'sell'
    price: float
    quantity: int

class SimulatedTradeRecord(BaseModel):
    trade_id: int
    user_id: int
    symbol: str
    trade_type: str
    price: float
    quantity: int
    trade_time: datetime

class SimulatedTradeHistoryResponse(BaseModel):
    trades: List[SimulatedTradeRecord]

@router.post("/trade/simulate")
def simulate_trade(item: SimulatedTradeItem, db: Session = Depends(get_db)):
    trade = SimulatedTrade(
        user_id=item.user_id,
        symbol=item.symbol,
        trade_type=item.trade_type,
        price=item.price,
        quantity=item.quantity,
        trade_time=datetime.utcnow()
    )
    db.add(trade)
    db.commit()
    return {"message": "모의 거래가 기록되었습니다."}

@router.get("/trade/history/{user_id}", response_model=SimulatedTradeHistoryResponse)
def get_trade_history(user_id: int, db: Session = Depends(get_db)):
    trades = db.query(SimulatedTrade).filter_by(user_id=user_id).order_by(SimulatedTrade.trade_time.desc()).all()
    return {"trades": [SimulatedTradeRecord(
        trade_id=t.trade_id,
        user_id=t.user_id,
        symbol=t.symbol,
        trade_type=t.trade_type,
        price=t.price,
        quantity=t.quantity,
        trade_time=t.trade_time
    ) for t in trades]} 