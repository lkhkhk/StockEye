import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.worker.scheduler_instance import scheduler # Import scheduler from the new file
import asyncio
# from src.worker.main import run_historical_price_update_task # Removed this import

router = APIRouter(prefix="/scheduler", tags=["scheduler"])
logger = logging.getLogger(__name__)

class TriggerJobRequest(BaseModel):
    chat_id: Optional[int] = None

class HistoricalPriceUpdateRequest(BaseModel):
    chat_id: Optional[int] = None
    start_date: str
    end_date: str
    stock_identifier: Optional[str] = None

@router.get("/status")
async def get_scheduler_status():
    """Get the status of the scheduler and its jobs."""
    if not scheduler.running:
        return {"is_running": False, "jobs": []}
    
    jobs = []
    for job in scheduler.get_jobs():
        logger.debug(f"Job: {job.id}, Name: {job.name}")
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return {"is_running": scheduler.running, "jobs": jobs}

@router.post("/trigger/{job_id}")
async def trigger_scheduler_job(job_id: str, request: TriggerJobRequest):
    """Trigger a specific scheduler job to run immediately."""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    
    try:
        # Modify the job to run immediately and pass chat_id
        now = datetime.now(job.next_run_time.tzinfo) # Use the job's timezone
        new_kwargs = job.kwargs.copy()
        if request.chat_id:
            new_kwargs['chat_id'] = request.chat_id
        job.modify(next_run_time=now, kwargs=new_kwargs)
        return {"job_id": job.id, "message": f"Job '{job.id}' triggered to run now.", "triggered_at": now.isoformat()}
    except Exception as e:
        logger.error(f"Failed to trigger job '{job_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger job '{job_id}': {str(e)}")

@router.post("/trigger_historical_prices_update")
async def trigger_historical_prices_update(request: HistoricalPriceUpdateRequest):
    """과거 일별 시세 갱신 작업을 비동기적으로 트리거합니다."""
    # Moved import inside the function to resolve circular dependency
    from src.worker.main import run_historical_price_update_task 

    logger.info(f"과거 일별 시세 갱신 요청 수신: {request.start_date} ~ {request.end_date}, chat_id: {request.chat_id}, stock_identifier: {request.stock_identifier}")
    try:
        parsed_start_date = datetime.strptime(request.start_date, '%Y-%m-%d')
        parsed_end_date = datetime.strptime(request.end_date, '%Y-%m-%d')

        # 비동기 작업을 생성하고 즉시 응답
        asyncio.create_task(run_historical_price_update_task(
            chat_id=request.chat_id,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            stock_identifier=request.stock_identifier
        ))
        return {"message": "과거 일별 시세 갱신 작업이 성공적으로 트리거되었습니다.", "status": "triggered"}
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해주세요.")
    except Exception as e:
        logger.error(f"과거 일별 시세 갱신 트리거 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"과거 일별 시세 갱신 트리거 실패: {str(e)}")