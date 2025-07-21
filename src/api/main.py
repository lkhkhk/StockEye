from fastapi import FastAPI
from src.api.routers.user import router as user_router
from src.api.routers.notification import router as notification_router
from src.api.routers.predict import router as predict_router
from src.api.routers.watchlist import router as watchlist_router
from src.api.routers.simulated_trade import router as simulated_trade_router
from src.api.routers.prediction_history import router as prediction_history_router
from src.api.routers.admin import router as admin_router
from src.api.routers.stock_master import router as symbols_router # 'symbols_router'가 stock_master.py에 있을 경우
from src.api.routers.bot_router import router as bot_router

from src.common.db_connector import Base, engine, get_db
import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# APScheduler
from apscheduler.schedulers.background import BackgroundScheduler

# Services
from src.api.services.price_alert_service import PriceAlertService
from src.api.services.stock_service import StockService
from src.api.models.system_config import SystemConfig

# 로그 디렉토리 생성
LOG_DIR = "/logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
os.makedirs(LOG_DIR, exist_ok=True)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# DB 테이블 자동 생성
try:
    Base.metadata.create_all(bind=engine)
    logger.info("DB 테이블이 성공적으로 생성되었거나 이미 존재합니다.")
except Exception as e:
    logger.error(f"DB 테이블 생성 중 오류 발생: {e}", exc_info=True)


app = FastAPI()

# --- Scheduler Jobs ---

def update_stock_master_job(stock_service: StockService, *args, **kwargs):
    """종목마스터 정보 갱신 잡"""
    logger.info(f"[APScheduler] 종목마스터 갱신 잡 실행: {datetime.now()}")
    db_gen = get_db()
    db = next(db_gen)
    try:
        stock_service.update_stock_master(db)
    except Exception as e:
        logger.error(f"종목마스터 갱신 잡 실행 중 오류: {e}", exc_info=True)
    finally:
        next(db_gen, None)

def update_daily_price_job(stock_service: StockService, *args, **kwargs):
    """일별시세 갱신 잡"""
    logger.info(f"[APScheduler] 일별시세 갱신 잡 실행: {datetime.now()}")
    db_gen = get_db()
    db = next(db_gen)
    try:
        stock_service.update_all_daily_prices(db)
    except Exception as e:
        logger.error(f"일별시세 갱신 잡 실행 중 오류: {e}", exc_info=True)
    finally:
        next(db_gen, None)

def check_disclosures_job(stock_service: StockService, *args, **kwargs):
    """최신 공시 확인 및 알림 잡"""
    logger.info(f"[APScheduler] 최신 공시 확인 잡 실행: {datetime.now()}")
    db_gen = get_db()
    db = next(db_gen)
    try:
        stock_service.check_and_notify_new_disclosures(db)
    except Exception as e:
        logger.error(f"최신 공시 확인 잡 실행 중 오류: {e}", exc_info=True)
    finally:
        next(db_gen, None)

def check_price_alerts_job(alert_service: PriceAlertService, *args, **kwargs):
    """가격 알림 조건 확인 및 알림 잡"""
    logger.info(f"[APScheduler] 가격 알림 체크 잡 실행: {datetime.now()}")
    db_gen = get_db()
    db = next(db_gen)
    try:
        alert_service.check_alerts(db)
    except Exception as e:
        logger.error(f"가격 알림 체크 잡 실행 중 오류: {e}", exc_info=True)
    finally:
        next(db_gen, None)

# --- Scheduler Setup ---

scheduler = BackgroundScheduler(timezone='Asia/Seoul')

# 서비스 인스턴스 생성
stock_service = StockService()
alert_service = PriceAlertService()

# 스케줄러에 잡 등록
scheduler.add_job(update_stock_master_job, 'cron', hour=7, minute=0, id='update_stock_master_job', replace_existing=True, kwargs={'stock_service': stock_service})
scheduler.add_job(update_daily_price_job, 'cron', hour=18, minute=0, id='update_daily_price_job', replace_existing=True, kwargs={'stock_service': stock_service})
scheduler.add_job(check_disclosures_job, 'interval', minutes=60, id='check_disclosures_job', replace_existing=True, kwargs={'stock_service': stock_service})
scheduler.add_job(check_price_alerts_job, 'interval', minutes=1, id='check_price_alerts_job', replace_existing=True, kwargs={'alert_service': alert_service})


@app.on_event("startup")
def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler (startup 이벤트) 시작됨")
        logger.info("등록된 잡 목록:")
        for job in scheduler.get_jobs():
            logger.info(f"- Job ID: {job.id}, Trigger: {job.trigger}")

@app.on_event("shutdown")
def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler가 정상적으로 종료되었습니다.")

# --- Routers ---
app.include_router(user_router)
app.include_router(notification_router)
app.include_router(predict_router)
app.include_router(watchlist_router)
app.include_router(simulated_trade_router)
app.include_router(prediction_history_router)
app.include_router(admin_router)
app.include_router(symbols_router)
app.include_router(bot_router)

# --- Basic Endpoints ---
@app.get("/")
def read_root():
    return {"message": "API 서비스 정상 동작"}

@app.get("/health")
def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scheduler_running": scheduler.running
    } 