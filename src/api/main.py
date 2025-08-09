from fastapi import FastAPI
from src.api.routers import user, notification, predict, watchlist, simulated_trade, prediction_history, admin, stock_master, bot_router
from src.common.db_connector import Base, engine
import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

APP_ENV = os.getenv("APP_ENV", "development")

# 로깅 레벨 설정
LOGGING_LEVEL = logging.DEBUG if APP_ENV == "development" else logging.INFO

# 로그 디렉토리 생성
LOG_DIR = "/logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
os.makedirs(LOG_DIR, exist_ok=True)

# 로깅 설정
logging.basicConfig(
    level=LOGGING_LEVEL,
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

# --- Routers ---
app.include_router(user.router, prefix="/api/v1")
app.include_router(notification.router, prefix="/api/v1")
app.include_router(predict.router, prefix="/api/v1")
app.include_router(watchlist.router, prefix="/api/v1")
app.include_router(simulated_trade.router, prefix="/api/v1")
app.include_router(prediction_history.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(stock_master.router, prefix="/api/v1")
app.include_router(bot_router.router, prefix="/api/v1")

# --- Basic Endpoints ---
@app.get("/")
def read_root():
    return {"message": "API 서비스 정상 동작"}

@app.get("/health")
def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }