# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.api.schemas.predict import StockPredictionRequest, StockPredictionResponse
from src.api.services.predict_service import predict_stock_movement
from src.api.models.prediction_history import PredictionHistory
from src.api.db import get_db
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["predict"])

@router.post("/", response_model=StockPredictionResponse, tags=["predict"])
def predict_stock(request: StockPredictionRequest, db: Session = Depends(get_db)):
    symbol = request.symbol
    
    # 예측 수행
    result = predict_stock_movement(db, symbol)
    
    # 예측 이력 저장 (사용자 ID가 있는 경우)
    if hasattr(request, 'user_id') and request.user_id:
        try:
            prediction_history = PredictionHistory(
                user_id=request.user_id,
                symbol=symbol,
                prediction=result["prediction"],
                created_at=datetime.utcnow()
            )
            db.add(prediction_history)
            db.commit()
        except Exception as e:
            # 이력 저장 실패는 예측 결과에 영향을 주지 않음
            db.rollback()
            logger.error(f"예측 이력 저장 실패: {str(e)}", exc_info=True)
    
    return StockPredictionResponse(
        symbol=symbol,
        prediction=result["prediction"],
        reason=result["reason"]
    ) 