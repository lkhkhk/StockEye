from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DisclosureAlertBase(BaseModel):
    symbol: str

class DisclosureAlertCreate(DisclosureAlertBase):
    is_active: Optional[bool] = True

class DisclosureAlertRead(DisclosureAlertBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DisclosureAlertUpdate(BaseModel):
    is_active: Optional[bool] = None
