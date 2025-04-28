from datetime import datetime
from pydantic import BaseModel, StringConstraints, validator, Field
from typing import Annotated, Optional

class Stock(BaseModel):
    code: str = Field(..., description="6자리 숫자 종목코드")
    name: str
    corp_code: Optional[str] = None
    added_at: datetime = datetime.now()

    @validator('code')
    def code_must_be_6_digits(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError('종목코드는 6자리 숫자여야 합니다.')
        return v

    class Config:
        from_attributes = True

class UserStock(BaseModel):
    user_id: str
    stock_code: Annotated[str, StringConstraints(pattern=r'^\d{6}$')]
    added_at: datetime = datetime.now()

    class Config:
        from_attributes = True 