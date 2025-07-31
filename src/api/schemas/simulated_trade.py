from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class SimulatedTradeItem(BaseModel):
    user_id: int
    symbol: str
    trade_type: Literal["buy", "sell"]  # 'buy' or 'sell'
    price: float
    quantity: int

class SimulatedTradeResponse(BaseModel):
    trade_id: int
    user_id: int
    symbol: str
    trade_type: str
    price: float
    quantity: int
    trade_time: datetime
    profit_loss: Optional[float] = None
    profit_rate: Optional[float] = None
    current_price: Optional[float] = None

class TradeStatistics(BaseModel):
    total_trades: int
    total_profit_loss: float
    profitable_trades: int
    win_rate: float

class TradeHistoryResponse(BaseModel):
    trades: list[SimulatedTradeResponse]
    statistics: TradeStatistics 