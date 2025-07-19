from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.api.schemas.predict import StockPredictionRequest, StockPredictionResponse
from src.api.services.predict_service import predict_stock_movement
from src.api.db import get_db

router = APIRouter()

@router.post("/predict", response_model=StockPredictionResponse)
def predict_stock(request: StockPredictionRequest, db: Session = Depends(get_db)):
    symbol = request.symbol
    result = predict_stock_movement(db, symbol)
    return StockPredictionResponse(
        symbol=symbol,
        prediction=result["prediction"],
        reason=result["reason"]
    ) 