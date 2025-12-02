import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from fastapi.testclient import TestClient
from src.api.main import app
from src.common.models.user import User
from src.common.models.price_alert import PriceAlert
from src.common.models.watchlist import Watchlist
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice
from src.common.models.disclosure import Disclosure
from src.common.models.prediction_history import PredictionHistory
from src.common.models.simulated_trade import SimulatedTrade
from src.common.models.system_config import SystemConfig

def test_read_root():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "API 서비스 정상 동작"} 