# src/api/tests/integration/test_api_watchlist_integration.py
"""
API 통합 테스트: 관심 종목 API

이 파일은 `/watchlist/` 엔드포인트 그룹에 대한 통합 테스트를 포함합니다.
사용자의 관심 종목을 추가, 조회, 삭제하는 기능을 검증합니다.

`TestClient`를 사용하여 API 요청을 보내고, `real_db`와 `test_stock_master_data` fixture를
통해 실제 데이터베이스와의 상호작용을 검증합니다.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.tests.helpers import create_test_user


def test_add_and_get_watchlist(client: TestClient, real_db, test_stock_master_data):
    """
    - **테스트 대상**: `POST /watchlist/add`, `GET /watchlist/get/{user_id}`
    - **목적**: 관심 종목을 성공적으로 추가하고, 추가된 종목이 조회되는지 확인합니다.
    - **시나리오**:
        1. 테스트용 사용자를 생성합니다.
        2. 특정 종목을 관심 목록에 추가 요청합니다.
        3. 200 OK 응답을 확인합니다.
        4. 해당 사용자의 관심 목록을 조회합니다.
        5. 200 OK 응답과 함께, 방금 추가한 종목이 목록에 포함되어 있는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    user = create_test_user(real_db)
    symbol = "005930"

    # When: 관심 종목 추가
    add_response = client.post("/watchlist/add", json={"user_id": user.id, "symbol": symbol})
    assert add_response.status_code == 200
    assert add_response.json()["message"] == "종목이 관심 목록에 추가되었습니다."

    # When: 관심 종목 조회
    get_response = client.get(f"/watchlist/get/{user.id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert "watchlist" in data
    assert symbol in data["watchlist"]


def test_remove_watchlist_success(client: TestClient, real_db, test_stock_master_data):
    """
    - **테스트 대상**: `POST /watchlist/remove`
    - **목적**: 관심 종목을 성공적으로 삭제하는지 확인합니다.
    - **시나리오**:
        1. 테스트 사용자의 관심 목록에 종목을 미리 추가합니다.
        2. 해당 종목을 관심 목록에서 삭제 요청합니다.
        3. 200 OK 응답과 성공 메시지를 확인합니다.
        4. 관심 목록을 다시 조회하여 해당 종목이 삭제되었는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    user = create_test_user(real_db)
    symbol = "005930"
    client.post("/watchlist/add", json={"user_id": user.id, "symbol": symbol})

    # When: 관심 종목 삭제
    remove_response = client.post("/watchlist/remove", json={"user_id": user.id, "symbol": symbol})
    assert remove_response.status_code == 200
    assert remove_response.json()["message"] == "종목이 관심 목록에서 제거되었습니다."

    # Then: 조회하여 삭제 확인
    get_response = client.get(f"/watchlist/get/{user.id}")
    data = get_response.json()
    assert symbol not in data["watchlist"]


def test_add_watchlist_duplicate(client: TestClient, real_db, test_stock_master_data):
    """
    - **테스트 대상**: `POST /watchlist/add`
    - **목적**: 이미 추가된 종목을 다시 추가하려고 할 때, 중복 추가되지 않고 정상 처리되는지 확인합니다.
    - **시나리오**:
        1. 특정 종목을 관심 목록에 추가합니다.
        2. 동일한 종목을 다시 추가 요청합니다.
        3. 200 OK 응답과 함께, "이미 관심 목록에 있는 종목입니다." 메시지를 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    user = create_test_user(real_db)
    symbol = "005930"
    client.post("/watchlist/add", json={"user_id": user.id, "symbol": symbol})

    # When: 중복 추가 요청
    duplicate_response = client.post("/watchlist/add", json={"user_id": user.id, "symbol": symbol})
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["message"] == "이미 관심 목록에 있는 종목입니다."


def test_add_watchlist_invalid_user(client: TestClient):
    """
    - **테스트 대상**: `POST /watchlist/add`
    - **목적**: 존재하지 않는 사용자로 관심 종목 추가 시, 404 에러를 반환하는지 확인합니다.
    - **시나리오**:
        1. 존재하지 않는 `user_id`로 추가를 요청합니다.
        2. 404 Not Found 응답을 확인합니다.
    - **Mock 대상**: 없음
    """
    response = client.post("/watchlist/add", json={"user_id": 99999, "symbol": "005930"})
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_get_watchlist_invalid_user(client: TestClient):
    """
    - **테스트 대상**: `GET /watchlist/get/{user_id}`
    - **목적**: 존재하지 않는 사용자로 관심 종목 조회 시, 404 에러를 반환하는지 확인합니다.
    - **시나리오**:
        1. 존재하지 않는 `user_id`로 조회를 요청합니다.
        2. 404 Not Found 응답을 확인합니다.
    - **Mock 대상**: 없음
    """
    response = client.get("/watchlist/get/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_add_watchlist_invalid_symbol(client: TestClient, real_db):
    """
    - **테스트 대상**: `POST /watchlist/add`
    - **목적**: 존재하지 않는 종목 코드로 관심 종목 추가 시, 404 에러를 반환하는지 확인합니다.
    - **시나리오**:
        1. 테스트 사용자를 생성합니다.
        2. 존재하지 않는 `symbol`로 추가를 요청합니다.
        3. 404 Not Found 응답을 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    user = create_test_user(real_db)

    # When
    response = client.post("/watchlist/add", json={"user_id": user.id, "symbol": "INVALID_SYMBOL"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Stock not found"