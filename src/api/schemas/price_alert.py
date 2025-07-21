from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PriceAlertBase(BaseModel):
    symbol: str
    target_price: Optional[float] = None
    condition: Optional[str] = None
    notify_on_disclosure: Optional[bool] = False

class PriceAlertCreate(PriceAlertBase):
    pass

class PriceAlertRead(PriceAlertBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PriceAlertUpdate(BaseModel):
    target_price: Optional[float] = None
    condition: Optional[str] = None
    is_active: Optional[bool] = None
    notify_on_disclosure: Optional[bool] = None 