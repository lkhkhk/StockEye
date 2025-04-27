from datetime import datetime
from pydantic import BaseModel, StringConstraints
from typing import Annotated

class Stock(BaseModel):
    code: Annotated[str, StringConstraints(pattern=r'^\d{6}$')]
    name: str
    added_at: datetime = datetime.now()

    class Config:
        from_attributes = True

class UserStock(BaseModel):
    user_id: str
    stock_code: Annotated[str, StringConstraints(pattern=r'^\d{6}$')]
    added_at: datetime = datetime.now()

    class Config:
        from_attributes = True 