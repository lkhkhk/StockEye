import pytest
from fastapi.testclient import TestClient
from src.api.main import app
import json

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