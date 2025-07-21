from pydantic import BaseModel
from typing import List

class WatchlistBase(BaseModel):
    user_id: int
    symbol: str

class WatchlistCreate(WatchlistBase):
    pass

class Watchlist(WatchlistBase):
    class Config:
        orm_mode = True

class WatchlistResponse(BaseModel):
    watchlist: List[str] 