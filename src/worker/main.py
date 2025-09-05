import asyncio
import os
import logging
import redis.asyncio as redis
import json
from logging.handlers import RotatingFileHandler
import sys
from datetime import datetime
from contextlib import asynccontextmanager
import multiprocessing

from fastapi import FastAPI

from src.common.services.notify_service import send_telegram_message
from src.worker.routers import scheduler as scheduler_router
from src.worker.scheduler_instance import scheduler
from src.worker import tasks

# 로깅 설정
APP_ENV = os.getenv("APP_ENV", "development")
LOGGING_LEVEL = logging.DEBUG if APP_ENV == "development" else logging.INFO
LOG_DIR = "/logs"
LOG_FILE = os.path.join(LOG_DIR, "worker.log")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=LOGGING_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 환경 변수
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting worker service...")
    
    # Add scheduler jobs
    scheduler.add_job(update_stock_master_job, 'cron', hour=7, minute=0, id='update_stock_master_job', name='종목 마스터 갱신')
    scheduler.add_job(update_daily_price_job, 'cron', hour=18, minute=0, id='update_daily_price_job', name='일별 시세 갱신')
    scheduler.add_job(check_disclosures_job, 'interval', minutes=240, id='check_disclosures_job', name='최신 공시 확인')
    scheduler.add_job(check_price_alerts_job, 'interval', minutes=1, id='check_price_alerts_job', name='가격 알림 확인')
    
    # Start scheduler
    scheduler.start()
    logger.info("APScheduler started.")

    # Start notification listener
    redis_listener_task = asyncio.create_task(notification_listener())
    
    yield
    
    logger.info("Shutting down worker service...")
    scheduler.shutdown()
    redis_listener_task.cancel()

app = FastAPI(lifespan=lifespan)
app.include_router(scheduler_router.router, prefix="/api/v1")


# --- Scheduler Jobs (Process Triggers) ---

async def update_stock_master_job(chat_id: int = None):
    """종목마스터 정보 갱신 잡을 별도 프로세스로 실행합니다."""
    logger.info(f"[Trigger] 'update_stock_master_task' process for chat_id: {chat_id}")
    p = multiprocessing.Process(target=tasks.update_stock_master_task, args=(chat_id,))
    p.start()

async def update_daily_price_job(chat_id: int = None):
    """일별시세 갱신 잡을 별도 프로세스로 실행합니다."""
    logger.info(f"[Trigger] 'update_daily_price_task' process for chat_id: {chat_id}")
    p = multiprocessing.Process(target=tasks.update_daily_price_task, args=(chat_id,))
    p.start()

async def run_historical_price_update_task(chat_id: int, start_date: datetime, end_date: datetime):
    """과거 일별 시세 갱신 작업을 별도 프로세스로 실행합니다."""
    logger.info(f"[Trigger] 'run_historical_price_update_task' process for chat_id: {chat_id}")
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    p = multiprocessing.Process(target=tasks.run_historical_price_update_task, args=(chat_id, start_date_str, end_date_str))
    p.start()

async def check_disclosures_job(chat_id: int = None):
    """최신 공시 확인 및 알림 잡을 별도 프로세스로 실행합니다."""
    logger.info(f"[Trigger] 'check_disclosures_task' process for chat_id: {chat_id}")
    p = multiprocessing.Process(target=tasks.check_disclosures_task, args=(chat_id,))
    p.start()

async def check_price_alerts_job(chat_id: int = None):
    """가격 알림 조건 확인 및 알림 잡을 별도 프로세스로 실행합니다."""
    logger.info(f"[Trigger] 'check_price_alerts_task' process for chat_id: {chat_id}")
    p = multiprocessing.Process(target=tasks.check_price_alerts_task, args=(chat_id,))
    p.start()

async def notification_listener():
    """Redis 'notifications' 채널을 구독하고 메시지를 처리합니다."""
    logger.info("[Listener] Starting notification listener...")
    r = None
    try:
        logger.info(f"[Listener] Connecting to Redis at {REDIS_HOST}...")
        r = await redis.from_url(f"redis://{REDIS_HOST}", decode_responses=True)
        logger.info("[Listener] Redis connection successful.")
        
        pubsub = r.pubsub()
        await pubsub.subscribe("notifications")
        logger.info(f"Subscribed to 'notifications' channel on {REDIS_HOST}")

        while True:
            try:
                logger.debug("[Listener] Waiting for message...")
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    logger.info(f"[Listener] Received message: {message['data']}")
                    data = json.loads(message['data'])
                    chat_id = data.get('chat_id')
                    text = data.get('text')
                    if chat_id and text and TELEGRAM_BOT_TOKEN:
                        await send_telegram_message(chat_id, text)
                        logger.info(f"[Listener] Sent message to {chat_id}: {text}")
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                logger.info("[Listener] Notification listener task cancelled.")
                break
            except Exception as e:
                logger.error(f"[Listener] Error processing message: {e}", exc_info=True)
                await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.info("[Listener] Main listener task cancelled.")
    except Exception as e:
        logger.error(f"[Listener] A critical error occurred: {e}", exc_info=True)
    finally:
        if r:
            await r.close()
            logger.info("[Listener] Redis connection closed.")

@app.get("/")
def read_root():
    return {"message": "Worker service is running"}