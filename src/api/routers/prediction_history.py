# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.common.db_connector import get_db
from src.api.models.prediction_history import PredictionHistory
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prediction", tags=["prediction_history"])

class PredictionHistoryRecord(BaseModel):
    id: int
    user_id: int
    symbol: str
    prediction: str
    created_at: datetime

class PredictionHistoryResponse(BaseModel):
    history: List[PredictionHistoryRecord]
    total_count: int
    page: int
    page_size: int

@router.get("/history/{user_id}", response_model=PredictionHistoryResponse, tags=["prediction_history"])
def get_prediction_history(
    user_id: int, 
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(10, ge=1, le=100, description="페이지 크기"),
    symbol: Optional[str] = Query(None, description="종목코드 필터"),
    prediction: Optional[str] = Query(None, description="예측 결과 필터")
):
    """사용자의 예측 이력 조회 (페이지네이션 및 필터링 지원)"""
    logger.debug(f"get_prediction_history 호출: user_id={user_id}, page={page}, page_size={page_size}, symbol={symbol}, prediction={prediction}")
    
    # 기본 쿼리
    query = db.query(PredictionHistory).filter(PredictionHistory.user_id == user_id)
    
    # 필터 적용
    if symbol:
        query = query.filter(PredictionHistory.symbol.like(f"%{symbol}%"))
        logger.debug(f"예측 이력 필터 적용: symbol={symbol}")
    if prediction:
        query = query.filter(PredictionHistory.prediction == prediction)
        logger.debug(f"예측 이력 필터 적용: prediction={prediction}")
    
    # 전체 개수 조회
    total_count = query.count()
    logger.debug(f"예측 이력 총 개수: {total_count}")
    
    # 페이지네이션 적용
    offset = (page - 1) * page_size
    records = query.order_by(PredictionHistory.created_at.desc()).offset(offset).limit(page_size).all()
    logger.debug(f"예측 이력 {len(records)}개 조회됨 (페이지 {page}, 페이지 크기 {page_size}).")
    
    return PredictionHistoryResponse(
        history=[PredictionHistoryRecord(
            id=r.id,
            user_id=r.user_id,
            symbol=r.symbol,
            prediction=r.prediction,
            created_at=r.created_at
        ) for r in records],
        total_count=total_count,
        page=page,
        page_size=page_size
    )