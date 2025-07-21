# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.common.db_connector import get_db
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

@router.post("/update_disclosure", tags=["admin"])
def update_disclosure(db: Session = Depends(get_db), code_or_name: str = ''):
    """종목코드(6자리), 종목명, 또는 corp_code(8자리)로 공시 이력 수동 갱신. 미입력시 전체."""
    try:
        results = []
        from src.api.models.stock_master import StockMaster
        if not code_or_name:
            # 전체 종목 대상
            stocks = db.query(StockMaster).filter(StockMaster.corp_code != None, StockMaster.corp_code != '').all()
            for stock in stocks:
                try:
                    res = stock_service.update_disclosures(db, corp_code=stock.corp_code, stock_code=stock.symbol, stock_name=stock.name)
                    results.append({"stock_code": stock.symbol, "corp_code": stock.corp_code, **res})
                except Exception as e:
                    results.append({"stock_code": stock.symbol, "corp_code": stock.corp_code, "success": False, "error": str(e)})
            total_inserted = sum(r.get('inserted', 0) for r in results if r.get('success'))
            total_skipped = sum(r.get('skipped', 0) for r in results if r.get('success'))
            total_errors = [r.get('error') for r in results if not r.get('success')]
            return {
                "message": f"전체 종목 공시 이력 갱신 완료: {total_inserted}건 추가, {total_skipped}건 중복, {len(total_errors)}건 에러",
                "inserted": total_inserted,
                "skipped": total_skipped,
                "errors": total_errors
            }
        # 단일 종목 처리
        code = code_or_name.strip()
        corp_code = None
        stock_code = None
        stock_name = None
        # 8자리 숫자면 corp_code로 간주
        if code.isdigit() and len(code) == 8:
            corp_code = code
            stock = db.query(StockMaster).filter(StockMaster.corp_code == corp_code).first()
            if stock:
                stock_code = stock.symbol
                stock_name = stock.name
        # 6자리 숫자면 종목코드
        elif code.isdigit() and len(code) == 6:
            stock = db.query(StockMaster).filter(StockMaster.symbol == code).first()
            if stock:
                corp_code = stock.corp_code
                stock_code = stock.symbol
                stock_name = stock.name
        # 그 외는 종목명(부분일치)
        else:
            stock = db.query(StockMaster).filter(StockMaster.name.like(f"%{code}%")).first()
            if stock:
                corp_code = stock.corp_code
                stock_code = stock.symbol
                stock_name = stock.name
        if not corp_code:
            raise HTTPException(status_code=404, detail="해당 입력에 대한 corp_code(고유번호)를 찾을 수 없습니다. 마스터 갱신 후 다시 시도하세요.")
        result = stock_service.update_disclosures(db, corp_code=corp_code, stock_code=stock_code or '', stock_name=stock_name or '')
        if result['success']:
            return {
                "message": f"공시 이력 갱신 완료: {result['inserted']}건 추가, {result['skipped']}건 중복",
                "inserted": result['inserted'],
                "skipped": result['skipped'],
                "errors": result['errors']
            }
        else:
            raise HTTPException(status_code=500, detail=f"공시 갱신 실패: {result['errors']}")
    except Exception as e:
        logger.error(f"/admin/update_disclosure 서버 오류: {str(e)}", exc_info=True)
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
    import traceback
    try:
        from src.api.main import scheduler
        # 잡 존재 확인
        job = scheduler.get_job(job_id)
        if not job:
            logger.error(f"[trigger_job] 잡을 찾을 수 없습니다: {job_id}")
            raise HTTPException(status_code=404, detail=f"잡을 찾을 수 없습니다: {job_id}")
        # 잡 직접 실행
        job.func(*job.args, **job.kwargs)
        logger.info(f"[trigger_job] 잡 직접 실행 성공: {job_id}")
        return {
            "message": f"잡 실행 완료: {job_id}",
            "job_id": job_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"[trigger_job] 잡 실행 실패: {job_id} - {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"잡 실행 실패: {str(e)}")

@router.post("/trigger/check_disclosures", tags=["admin_trigger"])
def trigger_check_disclosures_job(db: Session = Depends(get_db)):
    """(테스트용) 최신 공시 확인 및 알림 잡을 즉시 실행합니다."""
    try:
        logger.info("관리자에 의해 공시 확인 잡이 수동으로 트리거되었습니다.")
        stock_service.check_and_notify_new_disclosures(db)
        return {"message": "공시 확인 잡이 성공적으로 실행되었습니다."}
    except Exception as e:
        logger.error(f"공시 확인 잡 수동 실행 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 