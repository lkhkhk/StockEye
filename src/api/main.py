from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
# 라우터 임포트 수정 및 추가
from src.api.routers import user, price_alert_router, disclosure_alert_router, predict, watchlist, simulated_trade, prediction_history, admin, stock_master, bot_router, auth
from src.common.database.db_connector import Base, engine, SessionLocal
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice # 추가
import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta # timedelta 추가

APP_ENV = os.getenv("APP_ENV", "development")

# 로깅 레벨 설정
LOGGING_LEVEL = logging.DEBUG if APP_ENV == "development" else logging.INFO

# 로그 디렉토리 생성
LOG_DIR = "/logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
os.makedirs(LOG_DIR, exist_ok=True)

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
    ]
)
logging.getLogger("src.api.routers.price_alert_router").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

# Define the security scheme for JWT Bearer token
security_scheme = HTTPBearer()

app = FastAPI(
    # Define security schemes for OpenAPI (Swagger UI)
    security=[{"BearerAuth": []}], # Apply globally, or per-route with Depends(security_scheme)
    # Define components for security schemes
    components={
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter your JWT token in the format **Bearer &lt;token>**"
            }
        }
    }
)

def seed_test_data(db: Session):
    """테스트용 StockMaster 및 DailyPrice 데이터를 시딩하는 함수"""
    try:
        logger.info("개발 환경: 모든 테이블을 드롭하고 다시 생성합니다.")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        logger.info("개발 환경: StockMaster 테이블에 테스트 데이터를 시딩합니다.")
        stocks = [
            StockMaster(symbol="005930", name="삼성전자", market="KOSPI"),
            StockMaster(symbol="000660", name="SK하이닉스", market="KOSPI"),
                        StockMaster(symbol="035720", name="카카오", market="KOSPI"),
                        StockMaster(symbol="005380", name="현대차", market="KOSPI"),
                        StockMaster(symbol="000270", name="기아", market="KOSPI"),
            # StockMaster(symbol="GOOG", name="Alphabet Inc.", market="NASDAQ"),
            # StockMaster(symbol="AAPL", name="Apple Inc.", market="NASDAQ"),
            # StockMaster(symbol="MSFT", name="Microsoft Corp.", market="NASDAQ"),
            # StockMaster(symbol="AMZN", name="Amazon.com Inc.", market="NASDAQ"),
            # StockMaster(symbol="NFLX", name="Netflix Inc.", market="NASDAQ"),
        ]
        db.add_all(stocks)
        db.commit()
        logger.info("테스트 StockMaster 데이터 시딩 완료.")

        # DailyPrice 데이터 시딩 추가
        logger.info("개발 환경: DailyPrice 테이블에 테스트 데이터를 시딩합니다.")
        daily_prices = []
        today = datetime.now().date()
        # 삼성전자 (005930)에 대한 30일치 가상 데이터
        for i in range(30):
            date = today - timedelta(days=i)
            # 간단한 가상 가격 데이터 (실제와 유사하게 변동)
            close_price = 100 + (i % 5) * 2 - (i // 5) * 1
            open_price = close_price + (i % 3) - 1
            high_price = max(open_price, close_price) + (i % 2)
            low_price = min(open_price, close_price) - (i % 2)
            volume = 1000000 + (i % 10) * 100000

            daily_prices.append(
                DailyPrice(
                    symbol="005930",
                    date=date,
                    open=float(open_price),
                    high=float(high_price),
                    low=float(low_price),
                    close=float(close_price),
                    volume=int(volume)
                )
            )
        db.add_all(daily_prices)
        db.commit()
        logger.info("테스트 DailyPrice 데이터 시딩 완료.")

    except Exception as e:
        logger.error(f"테스트 데이터 시딩 중 오류 발생: {e}", exc_info=True)
        db.rollback()

@app.on_event("startup")
def on_startup():
    # Ensure tables are created for all environments
    Base.metadata.create_all(bind=engine)
    
    if APP_ENV == "development":
        db = SessionLocal()
        seed_test_data(db)
        db.close()

# --- Routers ---
app.include_router(user.router, prefix="/api/v1")
app.include_router(price_alert_router, prefix="/api/v1")
app.include_router(disclosure_alert_router, prefix="/api/v1")
app.include_router(predict.router, prefix="/api/v1")
app.include_router(watchlist.router, prefix="/api/v1")
app.include_router(simulated_trade.router, prefix="/api/v1")
app.include_router(prediction_history.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(stock_master.router, prefix="/api/v1")
app.include_router(bot_router.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1") # 새로 추가한 auth 라우터 등록

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

@app.get("/super_simple_test")
async def super_simple_test():
    print("Reached super_simple_test endpoint!")
    return {"message": "Super simple test successful!"}