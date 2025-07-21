import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.models.user import User
from src.api.models.price_alert import PriceAlert
from src.api.models.watchlist import Watchlist
from src.api.models.stock_master import StockMaster
from src.api.models.daily_price import DailyPrice
from src.api.models.disclosure import Disclosure
from src.api.models.prediction_history import PredictionHistory
from src.api.models.simulated_trade import SimulatedTrade
from src.api.models.system_config import SystemConfig

client = TestClient(app)

def test_predict_success():
    payload = {"symbol": "005930"}
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "symbol" in data
    assert "prediction" in data
    assert "reason" in data


def test_predict_invalid_symbol():
    payload = {"symbol": "INVALID"}
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] == "예측 불가"


def test_predict_missing_symbol():
    payload = {}
    response = client.post("/predict", json=payload)
    assert response.status_code == 422  # 필수값 누락시 FastAPI validation error 