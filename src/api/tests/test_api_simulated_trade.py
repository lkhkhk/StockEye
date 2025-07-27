import pytest
from fastapi.testclient import TestClient
from src.api.models.user import User

def create_test_user(db):
    """테스트용 사용자를 생성합니다."""
    user = User(username="trade_user", email="trade@test.com", password_hash="hash")
    db.add(user)
    db.flush() # commit 대신 flush 사용
    db.refresh(user)
    return user

def test_simulate_trade_and_get_history(client: TestClient, db):
    """모의 거래 및 이력 조회 엔드포인트 테스트"""
    # GIVEN: 테스트용 사용자 생성
    user = create_test_user(db)
    
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