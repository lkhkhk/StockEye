from pydantic import BaseModel
from typing import Optional

class StockPredictionRequest(BaseModel):
    symbol: str
    telegram_id: Optional[int] = None

class StockPredictionResponse(BaseModel):
    symbol: str
    prediction: str
    confidence: int
    reason: str 