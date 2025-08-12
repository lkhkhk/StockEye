import logging
from fastapi import APIRouter, HTTPException
from src.worker.scheduler_instance import scheduler # Import scheduler from the new file

router = APIRouter(prefix="/scheduler", tags=["scheduler"])
logger = logging.getLogger(__name__)

@router.get("/status")
async def get_scheduler_status():
    """Get the status of the scheduler and its jobs."""
    if not scheduler.running:
        return {"is_running": False, "jobs": []}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return {"is_running": scheduler.running, "jobs": jobs}

@router.post("/trigger/{job_id}")
async def trigger_scheduler_job(job_id: str):
    """Trigger a specific scheduler job to run immediately."""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    
    try:
        job.modify(next_run_time=None) # Run immediately
        return {"message": f"Job '{job_id}' triggered successfully."}
    except Exception as e:
        logger.error(f"Failed to trigger job '{job_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger job '{job_id}': {str(e)}")