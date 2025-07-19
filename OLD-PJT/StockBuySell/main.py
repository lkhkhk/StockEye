from fastapi import FastAPI
import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from prediction_logic import predict_stock_movement # prediction_logic 모듈 임포트
from data_collector import init_db_data # data_collector 모듈에서 init_db_data 임포트

app = FastAPI()

DATABASE_URL = "stock_prediction.db"

def get_db():
    db = sqlite3.connect(DATABASE_URL)
    db.row_factory = sqlite3.Row # Allows accessing columns by name
    return db

def init_db():
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watch_list (
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                PRIMARY KEY (user_id, symbol)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulated_trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                trade_type TEXT NOT NULL, -- 'buy' or 'sell'
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                trade_time TEXT NOT NULL -- ISO 8601 format
            )
        """)
        db.commit()

# Initialize the database on startup
init_db()
init_db_data() # data_collector의 데이터 테이블 초기화 함수 호출

class StockPredictionRequest(BaseModel):
    symbol: str

class StockPredictionResponse(BaseModel):
    symbol: str
    prediction: str # "상승" or "하락"
    reason: str

@app.get("/")
async def read_root():
    return {"message": "Stock Prediction API is running"}

@app.post("/predict", response_model=StockPredictionResponse)
async def predict_stock(request: StockPredictionRequest):
    """
    주식 종목에 대한 단기적 상승/하락 예측을 반환합니다.
    """
    stock_symbol = request.symbol

    # 예측 로직 모듈 호출
    prediction_result = predict_stock_movement(stock_symbol)

    # 예측 결과 딕셔너리에서 필요한 값 추출 및 자연어 응답 구성
    prediction = prediction_result.get("prediction", "예측 불가")
    trend = prediction_result.get("trend", "정보 부족")
    trend_duration = prediction_result.get("trend_duration", "N/A")
    movement_type = prediction_result.get("movement_type", "정보 부족")
    volume_trend_duration = prediction_result.get("volume_trend_duration", "N/A") # Extract volume_trend_duration
    trend_count = prediction_result.get("trend_count", {"up": 0, "down": 0})
    original_reason = prediction_result.get("reason", "상세 근거 없음")

    # 자연어 응답 문자열 구성 (더 자연스럽게)
    reason_string = f"{stock_symbol} 종목에 대한 분석 결과입니다.\n"
    reason_string += f"예측: {prediction} 추천.\n"
    reason_string += f"주가 추세: 현재 {trend} 추세이며, {trend_duration} 동안 지속되었습니다.\n"
    reason_string += f"금일 변동: {movement_type} 상태입니다.\n"
    reason_string += f"거래량 추세: 거래량은 {volume_trend_duration} 동안 같은 방향으로 움직였습니다.\n"
    reason_string += f"최근 20일간 주가 변동: 상승일 {trend_count['up']}회, 하락일 {trend_count['down']}회.\n"
    reason_string += f"상세 근거: {original_reason}"

    return StockPredictionResponse(
        symbol=stock_symbol,
        prediction=prediction, # prediction 값은 그대로 사용
        reason=reason_string # 상세하게 구성된 자연어 응답 사용
    )

# TODO: 데이터 수집 모듈 연동 (크론 스케줄러 등)

class WatchlistItem(BaseModel):
    user_id: int
    symbol: str

@app.post("/watchlist/add")
async def add_to_watchlist(item: WatchlistItem):
    """
    사용자의 관심 종목 목록에 종목을 추가합니다.
    """
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO watch_list (user_id, symbol) VALUES (?, ?)",
                (item.user_id, item.symbol)
            )
            db.commit()
        return {"message": "종목이 관심 목록에 추가되었습니다."}
    except sqlite3.IntegrityError:
        return {"message": "이미 관심 목록에 있는 종목입니다."}
    except Exception as e:
        return {"message": f"오류 발생: {e}"}

class WatchlistResponse(BaseModel):
    watchlist: list[str]

@app.get("/watchlist/get/{user_id}", response_model=WatchlistResponse)
async def get_watchlist(user_id: int):
    """
    사용자의 관심 종목 목록을 조회합니다.
    """
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                "SELECT symbol FROM watch_list WHERE user_id = ?",
                (user_id,)
            )
            watchlist = [row["symbol"] for row in cursor.fetchall()]
        return WatchlistResponse(watchlist=watchlist)
    except Exception as e:
        return {"message": f"오류 발생: {e}"}

@app.delete("/watchlist/remove")
async def remove_from_watchlist(item: WatchlistItem):
    """
    사용자의 관심 종목 목록에서 종목을 제거합니다.
    """
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                "DELETE FROM watch_list WHERE user_id = ? AND symbol = ?",
                (item.user_id, item.symbol)
            )
            db.commit()
            if cursor.rowcount == 0:
                return {"message": "관심 목록에 없는 종목입니다."}
        return {"message": "종목이 관심 목록에서 제거되었습니다."}
    except Exception as e:
        return {"message": f"오류 발생: {e}"}

class SimulatedTradeItem(BaseModel):
    user_id: int
    symbol: str
    trade_type: str # 'buy' or 'sell'
    price: float
    quantity: int

class SimulatedTradeRecord(SimulatedTradeItem):
    trade_id: int
    trade_time: datetime

class SimulatedTradeHistoryResponse(BaseModel):
    trades: list[SimulatedTradeRecord]

@app.post("/trade/simulate")
async def simulate_trade(item: SimulatedTradeItem):
    """
    모의 매수/매도 거래를 기록합니다.
    """
    if item.trade_type not in ["buy", "sell"]:
        return {"message": "trade_type은 'buy' 또는 'sell'이어야 합니다."}

    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO simulated_trades (user_id, symbol, trade_type, price, quantity, trade_time) VALUES (?, ?, ?, ?, ?, ?)",
                (item.user_id, item.symbol, item.trade_type, item.price, item.quantity, datetime.now().isoformat())
            )
            db.commit()
        return {"message": "모의 거래가 기록되었습니다."}
    except Exception as e:
        return {"message": f"오류 발생: {e}"}

@app.get("/trade/history/{user_id}", response_model=SimulatedTradeHistoryResponse)
async def get_trade_history(user_id: int):
    """
    사용자의 모의 거래 기록을 조회합니다.
    """
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                "SELECT trade_id, user_id, symbol, trade_type, price, quantity, trade_time FROM simulated_trades WHERE user_id = ? ORDER BY trade_time DESC",
                (user_id,)
            )
            trades = []
            for row in cursor.fetchall():
                trade_time_dt = datetime.fromisoformat(row["trade_time"])
                trades.append(SimulatedTradeRecord(
                    trade_id=row["trade_id"],
                    user_id=row["user_id"],
                    symbol=row["symbol"],
                    trade_type=row["trade_type"],
                    price=row["price"],
                    quantity=row["quantity"],
                    trade_time=trade_time_dt
                ))
        return SimulatedTradeHistoryResponse(trades=trades)
    except Exception as e:
        return {"message": f"오류 발생: {e}"}
