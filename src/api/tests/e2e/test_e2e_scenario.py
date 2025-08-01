import pytest
from fastapi.testclient import TestClient
from src.api.models.user import User
from uuid import uuid4

# 모든 SQLAlchemy 모델을 임포트하여 테스트 DB 스키마를 완전하게 생성
from src.api.models.price_alert import PriceAlert
from src.api.models.watchlist import Watchlist
from src.api.models.stock_master import StockMaster
from src.api.models.daily_price import DailyPrice
from src.api.models.disclosure import Disclosure
from src.api.models.prediction_history import PredictionHistory
from src.api.models.simulated_trade import SimulatedTrade
from src.api.models.system_config import SystemConfig

def test_e2e_scenario(client: TestClient, real_db, test_stock_master_data):
    """
    사용자 생성부터 watchlist 추가, 알림 설정, 예측, 거래까지 이어지는 E2E 시나리오
    """
    # 1. 사용자 생성
    unique_id = uuid4().hex
    username = f"e2e_user_{unique_id}"
    password = "e2e_password"
    email = f"e2e_{unique_id}@test.com"

    response = client.post("/users/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == username

    # 로그인
    response = client.post("/users/login", json={"username": username, "password": password})
    assert response.status_code == 200
    token_data = response.json()
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 사용자 정보 가져오기
    db_user = real_db.query(User).filter(User.username == username).first()
    assert db_user is not None
    user_id = db_user.id
    
    # 2. Watchlist 추가
    symbol = "005930" # 삼성전자
    response = client.post("/watchlist/add", json={"user_id": user_id, "symbol": symbol}, headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "종목이 관심 목록에 추가되었습니다."

    # 3. 가격 알림 설정
    response = client.post("/alerts/", json={
            "symbol": symbol,
            "target_price": 90000,
            "condition": "gte"
        }, headers=headers)
    assert response.status_code == 200
    alert_data = response.json()
    assert alert_data["symbol"] == symbol
    assert alert_data["target_price"] == 90000

    # 4. 주가 예측
    response = client.post("/predict", json={"symbol": symbol, "user_id": user_id}, headers=headers)
    assert response.status_code == 200
    assert response.json()["symbol"] == symbol
    assert "confidence" in response.json()
    assert isinstance(response.json()["confidence"], int)
    assert 0 <= response.json()["confidence"] <= 100

    # 5. 모의 거래
    response = client.post("/trade/simulate", json={
        "user_id": user_id,
        "symbol": symbol,
        "trade_type": "buy",
        "price": 85000,
        "quantity": 10
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "모의매매 기록 완료"

    # 6. 거래 내역 확인
    response = client.get(f"/trade/history/{user_id}", headers=headers)
    assert response.status_code == 200
    trade_history = response.json()
    assert len(trade_history["trades"]) == 1
    assert trade_history["trades"][0]["symbol"] == symbol
    assert trade_history["trades"][0]["trade_type"] == "buy"
    
    print("E2E 시나리오 테스트 성공")