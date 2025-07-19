import sys
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_create_price_alert():
    payload = {
        "user_id": 1,
        "symbol": "AAPL",
        "target_price": 150.0,
        "is_above": True
    }
    response = client.post("/notifications/alerts/price", json=payload)
    assert response.status_code == 200 or response.status_code == 201
    assert "alert_id" in response.json() or "message" in response.json()

def test_get_alert_history():
    user_id = 1
    response = client.get(f"/notifications/history/{user_id}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_price_alert_invalid():
    payload = {
        "user_id": 1,
        "symbol": "AAPL"
        # target_price, is_above 누락
    }
    response = client.post("/notifications/alerts/price", json=payload)
    assert response.status_code == 422 or response.status_code == 400 