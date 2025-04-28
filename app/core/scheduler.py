import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.dart_updater import update_corp_codes_from_dart

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone='Asia/Seoul')

def setup_scheduler():
    """스케줄러 설정 및 작업 추가"""
    try:
        # 매일 새벽 4시에 DART 고유번호 정보 갱신 작업 추가
        scheduler.add_job(
            update_corp_codes_from_dart,
            trigger=CronTrigger(hour=4, minute=0),
            id='update_dart_corp_codes_daily',
            name='Update DART Corp Codes Daily at 4 AM',
            replace_existing=True
        )
        logger.info("스케줄러 작업 추가 완료: DART 고유번호 일일 갱신 (매일 04:00)")
    except Exception as e:
        logger.error(f"스케줄러 작업 추가 중 오류 발생: {e}")

def start_scheduler():
    """스케줄러 시작"""
    if not scheduler.running:
        scheduler.start()
        logger.info("스케줄러 시작됨.")
    else:
        logger.info("스케줄러가 이미 실행 중입니다.")

def stop_scheduler():
    """스케줄러 종료"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("스케줄러 종료됨.") 