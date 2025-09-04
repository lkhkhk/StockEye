from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class PriceAlertBase(BaseModel):
    symbol: str
    target_price: Optional[float] = None
    condition: Optional[str] = None # 'gte', 'lte'
    change_percent: Optional[float] = None # N% 변동률
    change_type: Optional[str] = None # 'up', 'down' (변동률 조건과 함께 사용)
    repeat_interval: Optional[str] = None

    @validator('condition')
    def validate_condition(cls, v):
        if v is not None and v not in ['gte', 'lte']:
            raise ValueError("condition must be 'gte' or 'lte'")
        return v

class PriceAlertCreate(PriceAlertBase):
    is_active: Optional[bool] = True

class PriceAlertRead(PriceAlertBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    stock_name: Optional[str] = None
    status_message: Optional[str] = None

    class Config:
        from_attributes = True

class PriceAlertUpdate(BaseModel):
    target_price: Optional[float] = None
    condition: Optional[str] = None
    change_percent: Optional[float] = None
    change_type: Optional[str] = None
    is_active: Optional[bool] = None
    repeat_interval: Optional[str] = None
