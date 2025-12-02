import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.api.services.predict_service import PredictService

@patch('src.api.routers.predict.PredictService.predict_stock_movement')
def test_predict_price(mock_predict_stock_movement, client: TestClient, test_stock_master_data):
    """주가 예측 엔드포인트 테스트"""
    # MOCK: src.api.routers.predict.PredictService.predict_stock_movement
    # PredictService.predict_stock_stock_movement 메서드를 모의합니다. 이 메서드는 비동기적으로 동작합니다.
    mock_predict_stock_movement.return_value = {
        "prediction": "상승",
        "confidence": 85,
        "reason": "이동평균선이 정배열입니다."
    }

    response = client.post("/api/v1/predict", json={"symbol": "005930"})
    
    assert response.status_code == 200 
    data = response.json()
    assert data["symbol"] == "005930"
    assert data["prediction"] == "상승"
    assert data["confidence"] == 85
    assert data["reason"] == "이동평균선이 정배열입니다."
    # mock_predict_stock_movement (AsyncMock)이 한 번 호출되었는지 확인합니다.
    mock_predict_stock_movement.assert_called_once()


def test_predict_invalid_symbol(client: TestClient):
    payload = {"symbol": "INVALID"}
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 404 # Changed from 200 to 404
    data = response.json()
    assert data["detail"] == "종목을 찾을 수 없습니다: INVALID"
    


def test_predict_missing_symbol(client: TestClient):
    payload = {}
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 422  # 필수값 누락시 FastAPI validation error
