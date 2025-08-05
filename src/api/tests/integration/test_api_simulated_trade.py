import pytest
from fastapi.testclient import TestClient
from src.api.models.user import User

from src.api.tests.helpers import create_test_user # helpers에서 create_test_user 임포트

def test_simulate_trade_and_get_history(client: TestClient, real_db):
    """모의 거래 및 이력 조회 엔드포인트 테스트"""
    # GIVEN: 테스트용 사용자 생성
    user = create_test_user(real_db)
    
    # WHEN: 모의 거래 실행
    trade_payload = {
        "user_id": user.id,
        "symbol": "005930",
        "trade_type": "buy",
        "price": 80000,
        "quantity": 10
    }
    response = client.post("/trade/simulate", json=trade_payload)
    assert response.status_code == 200
    assert response.json()["message"] == "모의매매 기록 완료"
    
    # WHEN: 모의 거래 이력 조회
    response = client.get(f"/trade/history/{user.id}")
    assert response.status_code == 200
    data = response.json()
    assert "trades" in data
    assert len(data["trades"]) == 1
    assert data["trades"][0]["symbol"] == "005930"

def test_simulate_trade_sell(client: TestClient, real_db):
    """모의 매도 거래 엔드포인트 테스트"""
    user = create_test_user(real_db)

    # 매수 거래 기록
    buy_payload = {
        "user_id": user.id,
        "symbol": "005930",
        "trade_type": "buy",
        "price": 80000,
        "quantity": 10
    }
    client.post("/trade/simulate", json=buy_payload)

    # 매도 거래 기록
    sell_payload = {
        "user_id": user.id,
        "symbol": "005930",
        "trade_type": "sell",
        "price": 85000,
        "quantity": 5
    }
    response = client.post("/trade/simulate", json=sell_payload)
    assert response.status_code == 200
    assert response.json()["message"] == "모의매매 기록 완료"

    # 이력 조회로 확인
    history_response = client.get(f"/trade/history/{user.id}")
    history_data = history_response.json()
    assert len(history_data["trades"]) == 2
    assert history_data["trades"][0]["trade_type"] == "sell"
    assert history_data["trades"][1]["trade_type"] == "buy"

def test_get_trade_history_multiple_trades(client: TestClient, real_db):
    """여러 모의 거래 기록 후 이력 조회 테스트"""
    user = create_test_user(real_db)

    trades = [
        {"user_id": user.id, "symbol": "005930", "trade_type": "buy", "price": 80000, "quantity": 10},
        {"user_id": user.id, "symbol": "035720", "trade_type": "buy", "price": 50000, "quantity": 5},
        {"user_id": user.id, "symbol": "005930", "trade_type": "sell", "price": 85000, "quantity": 5},
    ]

    for trade in trades:
        client.post("/trade/simulate", json=trade)

    response = client.get(f"/trade/history/{user.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["trades"]) == 3
    # 최신순 정렬 확인
    assert data["trades"][0]["trade_type"] == "sell"
    assert data["trades"][0]["symbol"] == "005930"

def test_get_trade_stats_success(client: TestClient, real_db):
    """모의 거래 통계 조회 엔드포인트 테스트"""
    user = create_test_user(real_db)

    # 거래 기록
    client.post("/trade/simulate", json={"user_id": user.id, "symbol": "005930", "trade_type": "buy", "price": 80000, "quantity": 10})
    client.post("/trade/simulate", json={"user_id": user.id, "symbol": "005930", "trade_type": "sell", "price": 85000, "quantity": 5})
    client.post("/trade/simulate", json={"user_id": user.id, "symbol": "035720", "trade_type": "buy", "price": 50000, "quantity": 5})
    client.post("/trade/simulate", json={"user_id": user.id, "symbol": "035720", "trade_type": "sell", "price": 45000, "quantity": 5})

    response = client.get(f"/trade/history/{user.id}")
    assert response.status_code == 200
    data = response.json()["statistics"]
    assert "total_profit_loss" in data
    assert "win_rate" in data
    assert "total_trades" in data
    assert data["total_trades"] == 4

def test_simulate_trade_invalid_user(client: TestClient):
    """존재하지 않는 사용자 ID로 모의 거래 시도 테스트"""
    trade_payload = {
        "user_id": 99999,
        "symbol": "005930",
        "trade_type": "buy",
        "price": 80000,
        "quantity": 10
    }
    response = client.post("/trade/simulate", json=trade_payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_get_trade_history_invalid_user(client: TestClient):
    """존재하지 않는 사용자 ID로 모의 거래 이력 조회 테스트"""
    response = client.get("/trade/history/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_get_trade_stats_invalid_user(client: TestClient):
    """존재하지 않는 사용자 ID로 모의 거래 통계 조회 테스트"""
    response = client.get("/trade/history/99999") # get_trade_stats 대신 get_trade_history 호출
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_simulate_trade_invalid_input(client: TestClient, real_db):
    """유효하지 않은 입력으로 모의 거래 시도 테스트"""
    user = create_test_user(real_db)

    # 유효하지 않은 trade_type
    invalid_payload = {
        "user_id": user.id,
        "symbol": "005930",
        "trade_type": "invalid_type",
        "price": 80000,
        "quantity": 10
    }
    response = client.post("/trade/simulate", json=invalid_payload)
    assert response.status_code == 422

    # 필수 필드 누락
    missing_field_payload = {
        "user_id": user.id,
        "symbol": "005930",
        "trade_type": "buy",
        "price": 80000
        # quantity 누락
    }
    response = client.post("/trade/simulate", json=missing_field_payload)
    assert response.status_code == 422 