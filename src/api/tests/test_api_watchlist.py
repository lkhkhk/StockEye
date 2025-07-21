import pytest
from fastapi.testclient import TestClient
from src.api.main import app
import json
from src.api.models.user import User
from src.api.models.price_alert import PriceAlert
from src.api.models.watchlist import Watchlist
from src.api.models.stock_master import StockMaster
from src.api.models.daily_price import DailyPrice
from src.api.models.disclosure import Disclosure
from src.api.models.prediction_history import PredictionHistory
from src.api.models.simulated_trade import SimulatedTrade

client = TestClient(app)

def test_add_to_watchlist():
    payload = {"user_id": 1, "symbol": "005930"}
    response = client.post("/watchlist/add", json=payload)
    assert response.status_code == 200
    assert "message" in response.json()

def test_get_watchlist():
    user_id = 1
    response = client.get(f"/watchlist/get/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert "watchlist" in data
    assert isinstance(data["watchlist"], list)

def test_remove_from_watchlist():
    payload = {"user_id": 1, "symbol": "005930"}
    response = client.post("/watchlist/remove", json=payload)
    assert response.status_code == 200
    assert "message" in response.json() 