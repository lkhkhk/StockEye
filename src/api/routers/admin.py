# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from src.common.db_connector import get_db, Base, engine
from src.api.models.user import User
from src.api.auth.jwt_handler import get_current_active_admin_user
from src.api.models.simulated_trade import SimulatedTrade
from src.api.models.prediction_history import PredictionHistory
from src.api.models.stock_master import StockMaster
from src.api.services.stock_service import StockService
from datetime import datetime
import os

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)

APP_ENV = os.getenv("APP_ENV", "development")

def get_stock_service():
    return StockService()

@router.post("/debug/reset-database", tags=["debug"])
def reset_database(db: Session = Depends(get_db)):
    if APP_ENV != "development":
        raise HTTPException(status_code=403, detail="이 기능은 개발 환경에서만 사용할 수 있습니다.")

    try:
        logger.info("DB 초기화를 시작합니다.")
        # 모든 테이블의 데이터 삭제
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        
        # 시딩 함수 호출
        from src.api.main import seed_test_data
        seed_test_data(db)
        
        db.commit()
        logger.info("DB 초기화 및 데이터 시딩이 완료되었습니다.")
        return {"message": "DB 초기화 및 데이터 시딩이 완료되었습니다."}
    except Exception as e:
        db.rollback()
        logger.error(f"DB 초기화 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DB 초기화 실패: {str(e)}")

@router.get("/admin_stats", tags=["admin"])
def admin_stats(db: Session = Depends(get_db), user: User = Depends(get_current_active_admin_user)):
    user_count = db.query(User).count()
    trade_count = db.query(SimulatedTrade).count()
    prediction_count = db.query(PredictionHistory).count()
    return {
        "user_count": user_count,
        "trade_count": trade_count,
        "prediction_count": prediction_count
    }

# ... (기존 코드는 그대로 유지)
