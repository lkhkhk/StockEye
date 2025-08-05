import pytest
from fastapi.testclient import TestClient
from src.api.models.user import User

from src.api.tests.helpers import create_test_user # helpers에서 create_test_user 임포트

def test_add_and_get_watchlist(client: TestClient, real_db, test_stock_master_data):
    """관심 종목 추가 및 조회 테스트"""
    # GIVEN
    user = create_test_user(real_db)
    symbol = "005930"
    
    # WHEN: 관심 종목 추가
    add_payload = {"user_id": user.id, "symbol": symbol}
    response = client.post("/watchlist/add", json=add_payload)
    
    # THEN: 추가 성공
    assert response.status_code == 200
    assert response.json()["message"] == "이미 관심 목록에 있는 종목입니다." or response.json()["message"] == "종목이 관심 목록에 추가되었습니다."

    # WHEN: 관심 종목 조회
    response = client.get(f"/watchlist/get/{user.id}")
    
    # THEN: 조회 성공 및 데이터 확인
    assert response.status_code == 200
    data = response.json()
    assert "watchlist" in data
    assert symbol in data["watchlist"]

def test_remove_watchlist_success(client: TestClient, real_db, test_stock_master_data):
    """관심 종목 삭제 테스트"""
    user = create_test_user(real_db)
    symbol = "005930"

    # 관심 종목 추가
    add_payload = {"user_id": user.id, "symbol": symbol}
    client.post("/watchlist/add", json=add_payload)

    # 관심 종목 삭제
    remove_payload = {"user_id": user.id, "symbol": symbol}
    response = client.post("/watchlist/remove", json=remove_payload)

    assert response.status_code == 200
    assert response.json()["message"] == "종목이 관심 목록에서 제거되었습니다."

    # 조회하여 삭제 확인
    response = client.get(f"/watchlist/get/{user.id}")
    data = response.json()
    assert symbol not in data["watchlist"]

def test_add_watchlist_duplicate(client: TestClient, real_db, test_stock_master_data):
    """관심 종목 중복 추가 테스트"""
    user = create_test_user(real_db)
    symbol = "005930"

    add_payload = {"user_id": user.id, "symbol": symbol}
    client.post("/watchlist/add", json=add_payload)

    response = client.post("/watchlist/add", json=add_payload)
    assert response.status_code == 200
    assert response.json()["message"] == "이미 관심 목록에 있는 종목입니다."

def test_add_watchlist_invalid_user(client: TestClient):
    """존재하지 않는 사용자 ID로 관심 종목 추가 테스트"""
    add_payload = {"user_id": 99999, "symbol": "005930"}
    response = client.post("/watchlist/add", json=add_payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_get_watchlist_invalid_user(client: TestClient):
    """존재하지 않는 사용자 ID로 관심 종목 조회 테스트"""
    response = client.get("/watchlist/get/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_remove_watchlist_invalid_user(client: TestClient):
    """존재하지 않는 사용자 ID로 관심 종목 삭제 테스트"""
    remove_payload = {"user_id": 99999, "symbol": "005930"}
    response = client.post("/watchlist/remove", json=remove_payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_add_watchlist_invalid_symbol(client: TestClient, real_db, test_stock_master_data):
    """유효하지 않은 심볼로 관심 종목 추가 테스트"""
    user = create_test_user(real_db)
    add_payload = {"user_id": user.id, "symbol": "INVALID_SYMBOL"}
    response = client.post("/watchlist/add", json=add_payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Stock not found" 