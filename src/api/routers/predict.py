# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.common.schemas.predict import StockPredictionRequest, StockPredictionResponse
from src.common.models.prediction_history import PredictionHistory
from src.common.database.db_connector import get_db
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

@router.post("/predict", response_model=StockPredictionResponse, tags=["predict"])
def predict_stock(request: StockPredictionRequest, db: Session = Depends(get_db), predict_service: PredictService = Depends(get_predict_service), user_service: UserService = Depends(get_user_service)): # Add user_service dependency
    print(f"Received request: {request}")
    symbol = request.symbol
    
    # 예측 수행
    result = predict_service.predict_stock_movement(db, symbol)
    print(f"Prediction result: {result}")
    print(f"Prediction value for history check: {result['prediction']}")
    
    # 예측 이력 저장 (telegram_id가 있는 경우)
    if request.telegram_id and result["prediction"] not in ["N/A", "예측 불가"]:
        try:
            logger.debug(f"예측 이력 저장 시도: telegram_id={request.telegram_id}, symbol={symbol}, prediction={result['prediction']}")
            # telegram_id로 user_id 조회 또는 생성
            user = user_service.get_user_by_telegram_id(db, request.telegram_id)
            if not user:
                logger.debug(f"사용자 없음, 새로 생성: telegram_id={request.telegram_id}")
                user = user_service.create_user_from_telegram(
                    db,
                    telegram_id=request.telegram_id,
                    username=f"tg_{request.telegram_id}",
                    first_name="Telegram",
                    last_name="User"
                )
            logger.debug(f"사용자 ID 확인: user_id={user.id}")
            
            prediction_history = PredictionHistory(
                user_id=user.id, # Use user.id
                symbol=symbol,
                prediction=result["prediction"],
                created_at=datetime.utcnow()
            )
            db.add(prediction_history)
            db.commit()
            logger.info(f"예측 이력 저장 성공: user_id={user.id}, symbol={symbol}")
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
