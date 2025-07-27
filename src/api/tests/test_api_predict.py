import pytest
from fastapi.testclient import TestClient

def test_predict_price(client: TestClient):
    """주가 예측 엔드포인트 테스트"""
    # 이 테스트는 StockMaster에 '005930' 종목이 존재해야 합니다.
    # conftest에서 테스트용 기초 데이터를 미리 넣는 것이 좋습니다.
    response = client.post("/predict", json={"symbol": "005930"})
    
    # 예측 모델의 상태에 따라 200 또는 다른 상태 코드를 반환할 수 있습니다.
    # 여기서는 API가 요청을 정상적으로 처리하는지만 확인합니다.
    assert response.status_code == 200 
    assert "symbol" in response.json()
    assert "prediction" in response.json()


def test_predict_invalid_symbol(client: TestClient):
    payload = {"symbol": "INVALID"}
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] == "예측 불가"


def test_predict_missing_symbol(client: TestClient):
    payload = {}
    response = client.post("/predict", json=payload)
    assert response.status_code == 422  # 필수값 누락시 FastAPI validation error 