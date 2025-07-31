import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.api.services.predict_service import PredictService

@patch('src.api.routers.predict.PredictService.predict_stock_movement')
def test_predict_price(mock_predict_stock_movement, client: TestClient, test_stock_master):
    """주가 예측 엔드포인트 테스트"""
    # Mock the predict_stock_movement method
    mock_predict_stock_movement.return_value = {
        "prediction": "상승",
        "confidence": 85,
        "reason": "이동평균선이 정배열입니다."
    }

    response = client.post("/predict", json={"symbol": "005930"})
    
    assert response.status_code == 200 
    data = response.json()
    assert data["symbol"] == "005930"
    assert data["prediction"] == "상승"
    assert data["confidence"] == 85
    assert data["reason"] == "이동평균선이 정배열입니다."
    mock_predict_stock_movement.assert_called_once()


def test_predict_invalid_symbol(client: TestClient):
    payload = {"symbol": "INVALID"}
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] == "예측 불가"
    assert "confidence" in data
    assert data["confidence"] == 0


def test_predict_missing_symbol(client: TestClient):
    payload = {}
    response = client.post("/predict", json=payload)
    assert response.status_code == 422  # 필수값 누락시 FastAPI validation error 