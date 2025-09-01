# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from src.common.database.db_connector import get_db, Base, engine
from src.common.models.user import User
from src.api.auth.jwt_handler import get_current_active_admin_user
from src.common.models.simulated_trade import SimulatedTrade
from src.common.models.prediction_history import PredictionHistory
from src.common.models.stock_master import StockMaster
from src.common.services.stock_master_service import StockMasterService
from src.common.services.market_data_service import MarketDataService
from src.common.services.disclosure_service import DisclosureService
from datetime import datetime
import os
import httpx

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)

APP_ENV = os.getenv("APP_ENV", "development")
WORKER_HOST = os.getenv("WORKER_HOST", "localhost")
WORKER_PORT = 8001
WORKER_API_URL = f"http://{WORKER_HOST}:{WORKER_PORT}/api/v1"

class TriggerJobRequest(BaseModel):
    chat_id: Optional[int] = None

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

@router.post("/update_master", tags=["admin"])
async def update_master(
    db: Session = Depends(get_db), 
    stock_master_service: StockMasterService = Depends(StockMasterService),
    user: User = Depends(get_current_active_admin_user)
):
    """종목마스터 갱신"""
    try:
        result = await stock_master_service.update_stock_master(db)
        if result["success"]:
            return {
                "message": "종목마스터 갱신 완료",
                "updated_count": result["updated_count"],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"종목마스터 갱신 실패: {result.get('error', '알 수 없는 오류')}")
    except Exception as e:
        logger.error(f"update_master 엔드포인트에서 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.post("/update_price", tags=["admin"])
async def update_price(
    db: Session = Depends(get_db), 
    market_data_service: MarketDataService = Depends(MarketDataService),
    user: User = Depends(get_current_active_admin_user)
):
    """일별시세 갱신"""
    try:
        result = await market_data_service.update_daily_prices(db)
        if result["success"]:
            return {
                "message": f"일별시세 갱신 완료: {result['updated_count']}개 데이터 처리. 오류: {len(result['errors'])}개 종목",
                "updated_count": result["updated_count"],
                "error_stocks": result["errors"],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"일별시세 갱신 실패: {result.get('error', '알 수 없는 오류')}")
    except Exception as e:
        logger.error(f"update_price 엔드포인트에서 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.post("/update_disclosure", tags=["admin"])
async def update_disclosure(
    code_or_name: str = Query(None),
    db: Session = Depends(get_db),
    stock_master_service: StockMasterService = Depends(StockMasterService),
    disclosure_service: DisclosureService = Depends(DisclosureService),
    user: User = Depends(get_current_active_admin_user)
):
    """공시 이력 갱신 (전체 또는 특정 종목)"""
    try:
        if not code_or_name:
            # 전체 종목 대상
            result = await disclosure_service.update_disclosures_for_all_stocks(db)
            if result["success"]:
                return {
                    "message": f"전체 종목 공시 이력 갱신 완료: {result['inserted']}건 추가, {result['skipped']}건 중복",
                    "inserted": result["inserted"],
                    "skipped": result["skipped"],
                    "errors": result["errors"]
                }
            else:
                raise HTTPException(status_code=500, detail=f"전체 공시 갱신 실패: {result['errors']}")
        else:
            # 특정 종목 대상
            stock = stock_master_service.search_stocks(code_or_name, db, limit=1)
            if not stock or not stock[0].corp_code:
                raise HTTPException(status_code=404, detail=f"'{code_or_name}'에 해당하는 종목을 찾을 수 없거나 DART 고유번호(corp_code)가 없습니다.")
            
            target_stock = stock[0]
            result = await disclosure_service.update_disclosures(db, corp_code=target_stock.corp_code, stock_code=target_stock.symbol, stock_name=target_stock.name)
            if result["success"]:
                return {
                    "message": f"'{target_stock.name}' 공시 이력 갱신 완료: {result['inserted']}건 추가, {result['skipped']}건 중복",
                    "inserted": result["inserted"],
                    "skipped": result["skipped"],
                    "errors": result["errors"]
                }
            else:
                raise HTTPException(status_code=500, detail=f"'{target_stock.name}' 공시 갱신 실패: {result['errors']}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"update_disclosure 엔드포인트에서 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.get("/schedule/status", tags=["admin"])
async def get_schedule_status(user: User = Depends(get_current_active_admin_user)):
    """워커의 스케줄러 상태 및 잡 목록 조회"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{WORKER_API_URL}/scheduler/status")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"워커 스케줄러 상태 조회 실패: {e}")
        raise HTTPException(status_code=502, detail="워커 서비스에 연결할 수 없습니다.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

@router.post("/schedule/trigger/{job_id}", tags=["admin"])
async def trigger_schedule_job(job_id: str, request: TriggerJobRequest, user: User = Depends(get_current_active_admin_user)):
    """워커의 특정 스케줄러 잡 수동 실행"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{WORKER_API_URL}/scheduler/trigger/{job_id}", json=request.dict())
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"워커 잡 실행 실패: {e}")
        raise HTTPException(status_code=502, detail="워커 서비스에 연결할 수 없습니다.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

# [참고] 아래는 복잡한 의존성 주입 테스트 시 멈춤 현상(hang)을 디버깅하기 위한 임시 엔드포인트입니다.
# 평상시에는 비활성화된 관련 테스트(@pytest.mark.skip)와 함께 유지하여, 유사 문제 발생 시 재사용할 수 있습니다.
@router.get("/debug/auth_test", tags=["debug"])
def debug_auth_test(user: User = Depends(get_current_active_admin_user)):
    return {"username": user.username}