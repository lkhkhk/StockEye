from pydantic import BaseModel, ConfigDict
from typing import List

class WatchlistBase(BaseModel):
    user_id: int
    symbol: str

class WatchlistCreate(WatchlistBase):
    pass

class Watchlist(WatchlistBase):
    model_config = ConfigDict(from_attributes=True)

class WatchlistResponse(BaseModel):
    watchlist: List[str]
 