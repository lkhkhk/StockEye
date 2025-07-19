from pydantic import BaseModel

class StockPredictionRequest(BaseModel):
    symbol: str

class StockPredictionResponse(BaseModel):
    symbol: str
    prediction: str
    reason: str 