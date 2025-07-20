import pytest
from fastapi.testclient import TestClient
from src.api.main import app

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