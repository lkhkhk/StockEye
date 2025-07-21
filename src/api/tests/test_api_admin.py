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

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"

def test_admin_stats():
    response = client.get("/admin/admin_stats")
    assert response.status_code == 200
    data = response.json()
    assert "user_count" in data
    assert "trade_count" in data
    assert "prediction_count" in data 