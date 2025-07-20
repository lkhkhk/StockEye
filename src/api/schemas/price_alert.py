from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PriceAlertCreate(BaseModel):
    symbol: str
    target_price: float
    condition: str  # 'gte' 또는 'lte'

class PriceAlertRead(BaseModel):
    id: int
    user_id: int
    symbol: str
    target_price: float
    condition: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PriceAlertUpdate(BaseModel):
    target_price: Optional[float] = None
    condition: Optional[str] = None
    is_active: Optional[bool] = None 