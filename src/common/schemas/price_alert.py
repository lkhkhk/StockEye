from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional
from datetime import datetime

class PriceAlertBase(BaseModel):
    symbol: str
    target_price: Optional[float] = None
    condition: Optional[str] = None # 'gte', 'lte'
    change_percent: Optional[float] = None # N% 변동률
    change_type: Optional[str] = None # 'up', 'down' (변동률 조건과 함께 사용)
    notify_on_disclosure: Optional[bool] = False  # 공시 알림 여부
    notification_interval_hours: Optional[int] = 24  # 알림 주기 (시간 단위)
    repeat_interval: Optional[str] = None

    @field_validator('condition')
    @classmethod
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
    notify_on_disclosure: bool
    notification_interval_hours: int
    last_notified_at: Optional[datetime] = None
    notification_count: int
    created_at: datetime
    updated_at: datetime
    stock_name: Optional[str] = None
    status_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class PriceAlertUpdate(BaseModel):
    target_price: Optional[float] = None
    condition: Optional[str] = None
    change_percent: Optional[float] = None
    change_type: Optional[str] = None
    notify_on_disclosure: Optional[bool] = None
    notification_interval_hours: Optional[int] = None
    is_active: Optional[bool] = None
    repeat_interval: Optional[str] = None
