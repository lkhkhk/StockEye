from pydantic import BaseModel, ConfigDict
from datetime import datetime

class StockMasterBase(BaseModel):
    symbol: str
    name: str
    market: str | None = None
    corp_code: str | None = None
    is_delisted: bool = False # New field

class StockMasterCreate(StockMasterBase):
    pass

class StockMasterRead(StockMasterBase):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)