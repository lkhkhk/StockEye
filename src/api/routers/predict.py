# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.api.schemas.predict import StockPredictionRequest, StockPredictionResponse
from src.api.models.prediction_history import PredictionHistory
from src.common.db_connector import get_db
from datetime import datetime
from typing import Callable
from src.api.services.predict_service import PredictService
from src.api.services.user_service import UserService # Import UserService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["predict"])

def get_predict_service() -> PredictService:
    return PredictService()

def get_user_service() -> UserService:
    return UserService()

@router.post("/", response_model=StockPredictionResponse, tags=["predict"])
def predict_stock(request: StockPredictionRequest, db: Session = Depends(get_db), predict_service: PredictService = Depends(get_predict_service), user_service: UserService = Depends(get_user_service)): # Add user_service dependency
    print(f"Received request: {request}")
    symbol = request.symbol
    
    # 예측 수행
    result = predict_service.predict_stock_movement(db, symbol)
    print(f"Prediction result: {result}")
    
    # 예측 이력 저장 (telegram_id가 있는 경우)
    if request.telegram_id and result["prediction"] != "N/A":
        try:
            # telegram_id로 user_id 조회 또는 생성
            user = user_service.get_user_by_telegram_id(db, request.telegram_id)
            if not user:
                user = user_service.create_user_from_telegram(
                    db,
                    telegram_id=request.telegram_id,
                    username=f"tg_{request.telegram_id}",
                    first_name="Telegram",
                    last_name="User"
                )
            
            prediction_history = PredictionHistory(
                user_id=user.id, # Use user.id
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
        confidence=result["confidence"],
        reason=result["reason"]
    )