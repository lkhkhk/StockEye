from fastapi import APIRouter, HTTPException
from src.api.main import scheduler  # main 모듈에서 scheduler 직접 임포트

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)

@router.get("/scheduler-status")
def get_scheduler_status():
    """APScheduler의 현재 상태와 잡 목록을 반환합니다."""
    if not scheduler or not scheduler.running:
        raise HTTPException(status_code=503, detail="스케줄러가 실행 중이지 않거나 사용할 수 없습니다.")
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "scheduler_running": scheduler.running,
        "job_count": len(jobs),
        "jobs": jobs
    } 