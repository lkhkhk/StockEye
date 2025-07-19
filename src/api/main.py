from fastapi import FastAPI
from src.api.routers import user_router, notification_router, predict_router, watchlist_router, simulated_trade_router, prediction_history_router, admin_router, symbols_router
from src.api.models import Base
from src.api.db import engine
import sys

# DB 테이블 자동 생성
Base.metadata.create_all(bind=engine)

app = FastAPI()

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

print('=== FastAPI 라우트 목록 ===')
for route in app.routes:
    print(route.path)
sys.stdout.flush() 