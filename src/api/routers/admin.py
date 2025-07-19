from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.api.db import get_db
from src.api.models.user import User
from src.api.models.simulated_trade import SimulatedTrade
from src.api.models.prediction_history import PredictionHistory

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/admin_stats")
def admin_stats(db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    trade_count = db.query(SimulatedTrade).count()
    prediction_count = db.query(PredictionHistory).count()
    return {
        "user_count": user_count,
        "trade_count": trade_count,
        "prediction_count": prediction_count
    } 