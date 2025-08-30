from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PriceAlertBase(BaseModel):
    symbol: str
    target_price: Optional[float] = None
    condition: Optional[str] = None # 'gte', 'lte'
    change_percent: Optional[float] = None # N% 변동률
    change_type: Optional[str] = None # 'up', 'down' (변동률 조건과 함께 사용)
    notify_on_disclosure: bool = True
    repeat_interval: Optional[str] = None

class PriceAlertCreate(PriceAlertBase):
    telegram_id: Optional[int] = None
    is_active: Optional[bool] = True

class PriceAlertRead(PriceAlertBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    notify_on_disclosure: bool # Explicitly define as bool to ensure it's not Optional
    stock_name: Optional[str] = None

    class Config:
        from_attributes = True

class PriceAlertUpdate(BaseModel):
    target_price: Optional[float] = None
    condition: Optional[str] = None
    change_percent: Optional[float] = None
    change_type: Optional[str] = None
    is_active: Optional[bool] = None
    notify_on_disclosure: Optional[bool] = None
    repeat_interval: Optional[str] = None