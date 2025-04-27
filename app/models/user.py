from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    user_id: str
    username: Optional[str] = None
    first_name: str
    registered_at: datetime = datetime.now()

    class Config:
        from_attributes = True 