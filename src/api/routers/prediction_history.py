from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.api.db import get_db
from src.api.models.prediction_history import PredictionHistory
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter()

class PredictionHistoryRecord(BaseModel):
    id: int
    user_id: int
    symbol: str
    prediction: str
    created_at: datetime

class PredictionHistoryResponse(BaseModel):
    history: List[PredictionHistoryRecord]

@router.get("/prediction/history/{user_id}", response_model=PredictionHistoryResponse)
def get_prediction_history(user_id: int, db: Session = Depends(get_db)):
    records = db.query(PredictionHistory).filter_by(user_id=user_id).order_by(PredictionHistory.created_at.desc()).all()
    return {"history": [PredictionHistoryRecord(
        id=r.id,
        user_id=r.user_id,
        symbol=r.symbol,
        prediction=r.prediction,
        created_at=r.created_at
    ) for r in records]} 