import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_simulate_trade():
    payload = {
        "user_id": 1,
        "symbol": "005930",
        "trade_type": "buy",
        "price": 10000.0,
        "quantity": 10
    }
    response = client.post("/trade/simulate", json=payload)
    assert response.status_code == 200
    assert "message" in response.json()

def test_get_trade_history():
    user_id = 1
    response = client.get(f"/trade/history/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert "trades" in data
    assert isinstance(data["trades"], list) 