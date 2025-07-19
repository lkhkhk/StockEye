import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from uuid import uuid4

client = TestClient(app)

def test_e2e_scenario():
    # 1. 회원가입
    unique = str(uuid4())[:8]
    user_payload = {"username": f"e2euser_{unique}", "email": f"e2euser_{unique}@example.com", "password": "e2epass"}
    r = client.post("/users/register", json=user_payload)
    assert r.status_code == 200 or r.status_code == 201
    user_id = r.json().get("id")
    assert user_id

    # 2. 관심종목 추가
    watch_payload = {"user_id": user_id, "symbol": "005930"}
    r = client.post("/watchlist/add", json=watch_payload)
    assert r.status_code == 200

    # 3. 관심종목 조회
    r = client.get(f"/watchlist/get/{user_id}")
    assert r.status_code == 200
    assert "005930" in r.json().get("watchlist", [])

    # 4. 예측 요청
    r = client.post("/predict", json={"symbol": "005930"})
    assert r.status_code == 200
    assert "prediction" in r.json()

    # 5. 모의매매 기록
    trade_payload = {"user_id": user_id, "symbol": "005930", "trade_type": "buy", "price": 10000, "quantity": 1}
    r = client.post("/trade/simulate", json=trade_payload)
    assert r.status_code == 200

    # 6. 모의매매 이력 조회
    r = client.get(f"/trade/history/{user_id}")
    assert r.status_code == 200
    assert isinstance(r.json().get("trades", []), list)

    # 7. 예측 이력 조회
    r = client.get(f"/prediction/history/{user_id}")
    assert r.status_code == 200
    assert isinstance(r.json().get("history", []), list)

    # 8. 통계/헬스체크
    r = client.get("/admin_stats")
    assert r.status_code == 200
    r = client.get("/health")
    assert r.status_code == 200 