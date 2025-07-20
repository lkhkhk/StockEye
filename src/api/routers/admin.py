# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.api.db import get_db
from src.api.models.user import User
from src.api.models.simulated_trade import SimulatedTrade
from src.api.models.prediction_history import PredictionHistory
from src.api.services.stock_service import StockService
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["admin"])
stock_service = StockService()
logger = logging.getLogger(__name__)

@router.get("/admin_stats", tags=["admin"])
def admin_stats(db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    trade_count = db.query(SimulatedTrade).count()
    prediction_count = db.query(PredictionHistory).count()
    return {
        "user_count": user_count,
        "trade_count": trade_count,
        "prediction_count": prediction_count
    }

@router.post("/update_master", tags=["admin"])
def update_stock_master(db: Session = Depends(get_db)):
    """종목마스터 정보 수동 갱신"""
    try:
        result = stock_service.update_stock_master(db)
        if result["success"]:
            return {
                "message": "종목마스터 갱신 완료",
                "updated_count": result["updated_count"],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"갱신 실패: {result['error']}")
    except Exception as e:
        logger.error(f"/admin/update_master 서버 오류: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.post("/update_price", tags=["admin"])
def update_daily_price(db: Session = Depends(get_db)):
    """일별시세 수동 갱신"""
    try:
        result = stock_service.update_daily_prices(db)
        if result["success"]:
            return {
                "message": "일별시세 갱신 완료",
                "updated_count": result["updated_count"],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"갱신 실패: {result['error']}")
    except Exception as e:
        logger.error(f"/admin/update_price 서버 오류: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.get("/schedule/status", tags=["admin"])
def get_schedule_status():
    """스케줄러 상태 조회"""
    try:
        status = stock_service.get_scheduler_status()
        return {
            "message": "스케줄러 상태 조회 완료",
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 실패: {str(e)}")

@router.post("/schedule/trigger/{job_id}", tags=["admin"])
def trigger_job(job_id: str):
    """특정 잡 수동 실행"""
    try:
        from src.api.main import scheduler
        
        # 잡 존재 확인
        job = scheduler.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"잡을 찾을 수 없습니다: {job_id}")
        
        # 잡 실행
        scheduler.run_job(job_id)
        
        return {
            "message": f"잡 실행 완료: {job_id}",
            "job_id": job_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"잡 실행 실패: {str(e)}") 