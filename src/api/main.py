from fastapi import FastAPI
from src.api.routers import user_router, notification_router, predict_router, watchlist_router, simulated_trade_router, prediction_history_router, admin_router, symbols_router
from src.api.models import Base
from src.api.db import engine, get_db
import sys
# APScheduler 추가
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from datetime import datetime
from src.api.services.price_alert_service import PriceAlertService
from src.api.services.stock_service import StockService
from apscheduler.triggers.interval import IntervalTrigger
from src.common.notify_service import send_telegram_message
from src.api.models.user import User
from src.api.models.price_alert import PriceAlert
from sqlalchemy import text
from logging.handlers import RotatingFileHandler
import os

# 로그 디렉토리 생성 (없으면)
LOG_DIR = "/logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
os.makedirs(LOG_DIR, exist_ok=True)

# 로깅 설정 (stdout + 파일)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 디버깅: Base.metadata.tables, DB 연결 정보 출력
print('Base.metadata.tables:', list(Base.metadata.tables.keys()))
print('DB 연결 정보:', engine.url)
# DB 테이블 자동 생성
Base.metadata.create_all(bind=engine)
# 디버깅: 실제 DB 내 테이블 목록 출력
with engine.connect() as conn:
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public';"))
    print('DB 내 테이블 목록:', [row[0] for row in result])

app = FastAPI()

# APScheduler 인스턴스 생성 및 샘플 잡 등록
scheduler = BackgroundScheduler()

def sample_job():
    logger.info(f"[APScheduler] 샘플 잡 실행: {datetime.now()} - FastAPI 스케줄러 정상 동작")

def update_stock_master_job():
    """종목마스터 정보 갱신 잡"""
    logger.info(f"[APScheduler] 종목마스터 갱신 잡 실행: {datetime.now()}")
    try:
        from src.api.services.stock_service import StockService
        stock_service = StockService()
        db = next(get_db())
        result = stock_service.update_stock_master(db)
        if result["success"]:
            logger.info(f"종목마스터 갱신 완료: {result['updated_count']}개 종목")
        else:
            logger.error(f"종목마스터 갱신 실패: {result['error']}")
    except Exception as e:
        logger.error(f"종목마스터 갱신 잡 실행 중 오류: {str(e)}")

def update_daily_price_job():
    """일별시세 갱신 잡"""
    logger.info(f"[APScheduler] 일별시세 갱신 잡 실행: {datetime.now()}")
    try:
        from src.api.services.stock_service import StockService
        stock_service = StockService()
        db = next(get_db())
        result = stock_service.update_daily_prices(db)
        if result["success"]:
            logger.info(f"일별시세 갱신 완료: {result['updated_count']}개 데이터")
        else:
            logger.error(f"일별시세 갱신 실패: {result['error']}")
    except Exception as e:
        logger.error(f"일별시세 갱신 잡 실행 중 오류: {str(e)}")

# 스케줄러에 잡 등록
scheduler.add_job(sample_job, 'interval', minutes=1, id='sample_job', replace_existing=True)
scheduler.add_job(update_stock_master_job, 'cron', hour=9, minute=0, id='update_master_job', replace_existing=True)  # 매일 오전 9시
scheduler.add_job(update_daily_price_job, 'cron', hour=18, minute=0, id='update_price_job', replace_existing=True)  # 매일 오후 6시

alert_service = PriceAlertService()
stock_service = StockService()

# 가격 알림 체크 잡
def check_price_alerts_job():
    db = next(get_db())
    # 모든 활성화된 알림의 종목 목록 추출
    symbols = set([a.symbol for a in db.query(PriceAlert).all()])
    for symbol in symbols:
        current_price = stock_service.get_current_price(symbol, db)
        triggered_alerts = alert_service.check_alerts(db, symbol, current_price)
        for alert in triggered_alerts:
            user = db.query(User).filter(User.id == alert.user_id).first()
            if user and user.telegram_id and user.is_active:
                msg = f"[가격알림] {alert.symbol} {current_price}원 ({'이상' if alert.condition == 'gte' else '이하'} {alert.target_price})"
                send_telegram_message(user.telegram_id, msg)
            print(f"[알림] 사용자 {alert.user_id} - {alert.symbol} {current_price}원, 조건: {alert.condition} {alert.target_price}")
            alert.is_active = False
            db.commit()

scheduler.add_job(
    check_price_alerts_job,
    trigger=IntervalTrigger(minutes=1),
    id="check_price_alerts",
    name="가격 알림 조건 체크",
    replace_existing=True
)

scheduler.start()
logger.info("APScheduler 시작됨")

app.include_router(user_router)
app.include_router(notification_router)
app.include_router(predict_router)
app.include_router(watchlist_router)
app.include_router(simulated_trade_router)
app.include_router(prediction_history_router)
app.include_router(admin_router)
app.include_router(symbols_router)

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

print('=== FastAPI 라우트 목록 ===')
for route in app.routes:
    print(route.path)
sys.stdout.flush() 