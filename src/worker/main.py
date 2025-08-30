import asyncio
import os
import logging
import redis.asyncio as redis
import json
from logging.handlers import RotatingFileHandler
import sys
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.common.database.db_connector import get_db
from src.common.services.price_alert_service import PriceAlertService
from src.common.services.stock_service import StockService
from src.common.models.user import User
from src.common.services.notify_service import send_telegram_message
from src.worker.routers import scheduler as scheduler_router
from src.worker.scheduler_instance import scheduler # Import scheduler from the new file

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


# --- Scheduler Jobs ---

async def update_stock_master_job(chat_id: int = None):
    """종목마스터 정보 갱신 잡"""
    job_name = "종목마스터 갱신"
    logger.info(f"[APScheduler] {job_name} 잡 실행: {datetime.now()}")
    db_gen = get_db()
    db = next(db_gen)
    stock_service = StockService()
    success = False
    try:
        await stock_service.update_stock_master(db)
        success = True
    except Exception as e:
        logger.error(f"{job_name} 잡 실행 중 오류: {e}", exc_info=True)
    finally:
        try:
            next(db_gen, None)
        except StopIteration:
            pass
        if chat_id:
            if success:
                msg = f"✅ 작업 완료: {job_name} 실행을 성공했습니다."
            else:
                msg = f"❌ 작업 실패: {job_name} 실행 중 오류가 발생했습니다."
            r = redis.from_url(f"redis://{REDIS_HOST}")
            await r.publish("notifications", json.dumps({"chat_id": chat_id, "text": msg}, ensure_ascii=False))

async def update_daily_price_job(chat_id: int = None):
    """일별시세 갱신 잡"""
    job_name = "일별시세 갱신"
    logger.info(f"[APScheduler] {job_name} 잡 실행: {datetime.now()}")
    db_gen = get_db()
    db = next(db_gen)
    stock_service = StockService()
    success = False
    try:
        await stock_service.update_daily_prices(db)
        success = True
    except Exception as e:
        logger.error(f"{job_name} 잡 실행 중 오류: {e}", exc_info=True)
    finally:
        try:
            next(db_gen, None)
        except StopIteration:
            pass
        if chat_id:
            if success:
                msg = f"✅ 작업 완료: {job_name} 실행을 성공했습니다."
            else:
                msg = f"❌ 작업 실패: {job_name} 실행 중 오류가 발생했습니다."
            r = redis.from_url(f"redis://{REDIS_HOST}")
            await r.publish("notifications", json.dumps({"chat_id": chat_id, "text": msg}, ensure_ascii=False))

async def check_disclosures_job(chat_id: int = None):
    """최신 공시 확인 및 알림 잡"""
    job_name = "최신 공시 확인"
    logger.info(f"[APScheduler] {job_name} 잡 실행: {datetime.now()}")
    db_gen = get_db()
    db = next(db_gen)
    stock_service = StockService()
    success = False
    try:
        await stock_service.check_and_notify_new_disclosures(db)
        success = True
    except Exception as e:
        logger.error(f"{job_name} 잡 실행 중 오류: {e}", exc_info=True)
    finally:
        try:
            next(db_gen, None)
        except StopIteration:
            pass
        if chat_id:
            if success:
                msg = f"✅ 작업 완료: {job_name} 실행을 성공했습니다."
            else:
                msg = f"❌ 작업 실패: {job_name} 실행 중 오류가 발생했습니다."
            r = redis.from_url(f"redis://{REDIS_HOST}")
            await r.publish("notifications", json.dumps({"chat_id": chat_id, "text": msg}, ensure_ascii=False))

async def check_price_alerts_job(chat_id: int = None):
    """가격 알림 조건 확인 및 알림 잡"""
    job_name = "가격 알림 확인"
    logger.info(f"[APScheduler] {job_name} 잡 실행: {datetime.now()}")
    db_gen = get_db()
    db = next(db_gen)
    alert_service = PriceAlertService()
    stock_service = StockService()
    success = False
    try:
        active_alerts = alert_service.get_all_active_alerts(db)
        alerts_by_symbol = {}
        for alert in active_alerts:
            if alert.symbol not in alerts_by_symbol:
                alerts_by_symbol[alert.symbol] = []
            alerts_by_symbol[alert.symbol].append(alert)

        for symbol, alerts in alerts_by_symbol.items():
            try:
                price_data = stock_service.get_current_price_and_change(symbol, db)
                current_price = price_data.get("current_price")
                if current_price is None:
                    continue

                for alert in alerts:
                    triggered = False
                    if alert.condition == 'gte' and current_price >= alert.target_price:
                        triggered = True
                    elif alert.condition == 'lte' and current_price <= alert.target_price:
                        triggered = True
                    
                    if triggered:
                        user = db.query(User).filter(User.id == alert.user_id).first()
                        if user and user.telegram_id:
                            msg = f"🔔 가격 알림: {alert.symbol}\n현재가 {current_price}원이 목표가 {alert.target_price}({alert.condition})에 도달했습니다."
                            r = redis.from_url(f"redis://{REDIS_HOST}")
                            await r.publish("notifications", json.dumps({"chat_id": user.telegram_id, "text": msg}, ensure_ascii=False))
                        
                        if alert.repeat_interval is None:
                            alert.is_active = False
                            db.add(alert)
                db.commit()
            except Exception as e:
                logger.error(f"가격 알림 확인 중 '{symbol}' 처리 오류: {e}", exc_info=True)
                continue
        db.commit()
        success = True
    except Exception as e:
        logger.error(f"{job_name} 잡 실행 중 상위 레벨 오류: {e}", exc_info=True)
        db.rollback()
    finally:
        try:
            next(db_gen, None)
        except StopIteration:
            pass
        if chat_id:
            if success:
                msg = f"✅ 작업 완료: {job_name} 실행을 성공했습니다."
            else:
                msg = f"❌ 작업 실패: {job_name} 실행 중 오류가 발생했습니다."
            r = redis.from_url(f"redis://{REDIS_HOST}")
            await r.publish("notifications", json.dumps({"chat_id": chat_id, "text": msg}, ensure_ascii=False))

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