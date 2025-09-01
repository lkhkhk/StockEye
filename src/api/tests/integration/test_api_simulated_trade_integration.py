# src/api/tests/integration/test_api_simulated_trade_integration.py
"""
API 통합 테스트: 모의 거래 API

이 파일은 `/trade/` 엔드포인트 그룹에 대한 통합 테스트를 포함합니다.
모의 거래를 기록하고, 거래 이력 및 통계를 조회하는 기능을 검증합니다.
`TestClient`를 사용하여 API 요청을 보내고, `real_db` fixture를 통해 실제 데이터베이스와의
상호작용을 검증합니다. 서비스 계층에 대한 모의(Mock)는 사용하지 않습니다.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.tests.helpers import create_test_user


def test_simulate_trade_and_get_history(client: TestClient, real_db):
    """
    - **테스트 대상**: `POST /trade/simulate`, `GET /trade/history/{user_id}`
    - **목적**: 모의 거래를 성공적으로 기록하고, 해당 거래가 이력 조회 시 정상적으로 반환되는지 확인합니다.
    - **시나리오**:
        1. 테스트용 사용자를 생성합니다.
        2. 모의 매수 거래를 요청합니다.
        3. 200 OK 응답을 확인합니다.
        4. 거래 이력 조회를 요청합니다.
        5. 200 OK 응답과 함께, 방금 기록한 거래가 포함된 이력이 반환되는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given: 테스트용 사용자 생성
    user = create_test_user(real_db)

    # When: 모의 매수 거래 기록
    trade_payload = {"user_id": user.id, "symbol": "005930", "trade_type": "buy", "price": 80000, "quantity": 10}
    response = client.post("/trade/simulate", json=trade_payload)
    assert response.status_code == 200
    assert response.json()["message"] == "모의매매 기록 완료"

    # Then: 거래 이력 조회로 확인
    history_response = client.get(f"/trade/history/{user.id}")
    assert history_response.status_code == 200
    data = history_response.json()
    assert len(data["trades"]) == 1
    assert data["trades"][0]["symbol"] == "005930"


def test_simulate_trade_sell(client: TestClient, real_db):
    """
    - **테스트 대상**: `POST /trade/simulate` (매도 시나리오)
    - **목적**: 모의 매도 거래가 정상적으로 기록되는지 확인합니다.
    - **시나리오**:
        1. 테스트용 사용자를 생성하고, 매수 거래를 먼저 기록합니다.
        2. 동일 종목에 대해 매도 거래를 요청합니다.
        3. 200 OK 응답을 확인합니다.
        4. 거래 이력을 조회하여 매수와 매도 거래가 모두 기록되었는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given: 테스트용 사용자 및 매수 거래 생성
    user = create_test_user(real_db)
    client.post("/trade/simulate", json={"user_id": user.id, "symbol": "005930", "trade_type": "buy", "price": 80000, "quantity": 10})

    # When: 모의 매도 거래 기록
    sell_payload = {"user_id": user.id, "symbol": "005930", "trade_type": "sell", "price": 85000, "quantity": 5}
    response = client.post("/trade/simulate", json=sell_payload)
    assert response.status_code == 200

    # Then: 거래 이력 조회로 확인
    history_response = client.get(f"/trade/history/{user.id}")
    data = history_response.json()
    assert len(data["trades"]) == 2
    assert data["trades"][0]["trade_type"] == "sell"  # 최신순 정렬 확인


def test_get_trade_history_multiple_trades(client: TestClient, real_db):
    """
    - **테스트 대상**: `GET /trade/history/{user_id}`
    - **목적**: 여러 건의 모의 거래가 기록되었을 때, 이력 조회 기능이 정상적으로 동작하는지 확인합니다.
    - **시나리오**:
        1. 여러 건의 매수/매도 거래를 기록합니다.
        2. 거래 이력을 조회합니다.
        3. 200 OK 응답과 함께, 모든 거래가 최신순으로 정렬되어 반환되는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given: 여러 건의 모의 거래 기록
    user = create_test_user(real_db)
    trades = [
        {"user_id": user.id, "symbol": "005930", "trade_type": "buy", "price": 80000, "quantity": 10},
        {"user_id": user.id, "symbol": "035720", "trade_type": "buy", "price": 50000, "quantity": 5},
        {"user_id": user.id, "symbol": "005930", "trade_type": "sell", "price": 85000, "quantity": 5},
    ]
    for trade in trades:
        client.post("/trade/simulate", json=trade)

    # When: 거래 이력 조회
    response = client.get(f"/trade/history/{user.id}")

    # Then: 결과 검증
    assert response.status_code == 200
    data = response.json()
    assert len(data["trades"]) == 3
    assert data["trades"][0]["symbol"] == "005930"
    assert data["trades"][0]["trade_type"] == "sell"


def test_get_trade_stats_success(client: TestClient, real_db):
    """
    - **테스트 대상**: `GET /trade/history/{user_id}` (통계 부분)
    - **목적**: 거래 이력 조회 시, 통계 정보가 정상적으로 계산되어 반환되는지 확인합니다.
    - **시나리오**:
        1. 수익과 손실이 모두 발생하는 여러 거래를 기록합니다.
        2. 거래 이력을 조회합니다.
        3. 200 OK 응답과 함께, `statistics` 필드에 총 손익, 승률 등의 정보가 포함되어 있는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given: 여러 건의 모의 거래 기록
    user = create_test_user(real_db)
    client.post("/trade/simulate", json={"user_id": user.id, "symbol": "005930", "trade_type": "buy", "price": 80000, "quantity": 10})
    client.post("/trade/simulate", json={"user_id": user.id, "symbol": "005930", "trade_type": "sell", "price": 85000, "quantity": 5})
    client.post("/trade/simulate", json={"user_id": user.id, "symbol": "035720", "trade_type": "buy", "price": 50000, "quantity": 5})
    client.post("/trade/simulate", json={"user_id": user.id, "symbol": "035720", "trade_type": "sell", "price": 45000, "quantity": 5})

    # When: 거래 이력 조회
    response = client.get(f"/trade/history/{user.id}")

    # Then: 통계 정보 검증
    assert response.status_code == 200
    stats = response.json()["statistics"]
    assert "total_profit_loss" in stats
    assert "win_rate" in stats
    assert "total_trades" in stats
    assert stats["total_trades"] == 4


def test_simulate_trade_invalid_user(client: TestClient):
    """
    - **테스트 대상**: `POST /trade/simulate`
    - **목적**: 존재하지 않는 사용자로 모의 거래 요청 시, 404 에러를 반환하는지 확인합니다.
    - **시나리오**:
        1. 존재하지 않는 `user_id`로 거래를 요청합니다.
        2. 404 Not Found 응답을 확인합니다.
    - **Mock 대상**: 없음
    """
    response = client.post("/trade/simulate", json={"user_id": 99999, "symbol": "005930", "trade_type": "buy", "price": 80000, "quantity": 10})
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_get_trade_history_invalid_user(client: TestClient):
    """
    - **테스트 대상**: `GET /trade/history/{user_id}`
    - **목적**: 존재하지 않는 사용자로 거래 이력 조회 요청 시, 404 에러를 반환하는지 확인합니다.
    - **시나리오**:
        1. 존재하지 않는 `user_id`로 이력 조회를 요청합니다.
        2. 404 Not Found 응답을 확인합니다.
    - **Mock 대상**: 없음
    """
    response = client.get("/trade/history/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_get_trade_stats_invalid_user(client: TestClient):
    """
    - **테스트 대상**: `GET /trade/history/{user_id}` (통계 부분)
    - **목적**: 존재하지 않는 사용자로 통계 조회 요청 시, 404 에러를 반환하는지 확인합니다.
    - **시나리오**:
        1. 존재하지 않는 `user_id`로 이력/통계 조회를 요청합니다.
        2. 404 Not Found 응답을 확인합니다.
    - **Mock 대상**: 없음
    """
    # 참고: 현재 통계는 이력 조회(/trade/history/{user_id})에 포함되어 반환됩니다.
    # 따라서 이 테스트는 `test_get_trade_history_invalid_user`와 동일한 동작을 검증합니다.
    response = client.get("/trade/history/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_simulate_trade_invalid_input(client: TestClient, real_db):
    """
    - **테스트 대상**: `POST /trade/simulate`
    - **목적**: 유효하지 않은 입력값으로 모의 거래 요청 시, 422 에러를 반환하는지 확인합니다.
    - **시나리오**:
        1. `trade_type`에 허용되지 않는 값을 넣어 요청하고 422 응답을 확인합니다.
        2. 필수 필드(`quantity`)를 누락하여 요청하고 422 응답을 확인합니다.
    - **Mock 대상**: 없음
    """
    user = create_test_user(real_db)

    # 시나리오 1: 유효하지 않은 trade_type
    invalid_payload = {"user_id": user.id, "symbol": "005930", "trade_type": "invalid_type", "price": 80000, "quantity": 10}
    response = client.post("/trade/simulate", json=invalid_payload)
    assert response.status_code == 422

    # 시나리오 2: 필수 필드 누락
    missing_field_payload = {"user_id": user.id, "symbol": "005930", "trade_type": "buy", "price": 80000}
    response = client.post("/trade/simulate", json=missing_field_payload)
    assert response.status_code == 422