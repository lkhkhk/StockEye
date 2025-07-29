import pytest
from fastapi.testclient import TestClient
from src.api.models.user import User

def create_test_user(db):
    """테스트용 사용자를 생성합니다."""
    user = User(username="watchlist_user", email="watchlist@test.com", password_hash="hash")
    db.add(user)
    db.flush() # commit 대신 flush 사용
    db.refresh(user)
    return user

def test_add_and_get_watchlist(client: TestClient, real_db):
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