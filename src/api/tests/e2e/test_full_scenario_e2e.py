"""
E2E 테스트: 전체 사용자 시나리오

이 파일은 StockEye 애플리케이션의 핵심 사용자 흐름을 엔드-투-엔드(End-to-End) 방식으로 테스트합니다.
실제 API 엔드포인트와 데이터베이스(`real_db` fixture)를 사용하여,
사용자 등록부터 로그인, 관심 종목 추가, 가격 알림 설정, 주가 예측, 모의 거래 기록 및 조회까지의
전체 시나리오가 예상대로 동작하는지 검증합니다.

이 테스트는 시스템의 여러 컴포넌트(인증, 사용자 관리, 종목 관리, 알림, 예측, 모의 거래)가
통합적으로 올바르게 작동하는지 확인하는 데 중점을 둡니다.
"""

import pytest
from fastapi.testclient import TestClient
from src.common.models.user import User
from uuid import uuid4

# 모든 SQLAlchemy 모델을 임포트하여 테스트 DB 스키마를 완전하게 생성
from src.common.models.price_alert import PriceAlert
from src.common.models.watchlist import Watchlist
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice
from src.common.models.disclosure import Disclosure
from src.common.models.prediction_history import PredictionHistory
from src.common.models.simulated_trade import SimulatedTrade
from src.common.models.system_config import SystemConfig

@pytest.mark.asyncio
async def test_e2e_scenario(client: TestClient, real_db, test_stock_master_data):
    """
    - **테스트 대상**: StockEye 애플리케이션의 핵심 사용자 흐름 (E2E)
    - **목적**: 사용자 등록부터 로그인, 관심 종목 추가, 알림 설정, 주가 예측, 모의 거래 기록 및 조회까지의
              전체 시나리오가 예상대로 동작하는지 검증합니다.
    - **시나리오**:
        1. 새로운 사용자를 등록하고 로그인하여 JWT 토큰을 발급받습니다.
        2. 발급받은 토큰으로 인증하여 관심 종목을 추가합니다.
        3. 동일한 종목에 대해 가격 알림을 설정합니다.
        4. 해당 종목에 대한 주가 예측을 요청합니다.
        5. 해당 종목에 대한 모의 매수 거래를 기록합니다.
        6. 모의 거래 내역을 조회하여 기록된 거래가 정상적으로 반환되는지 확인합니다.
    - **Mock 대상**: 없음 (실제 API 및 DB 연동)
    """
    # 1. 사용자 생성
    unique_id = uuid4().hex
    username = f"e2e_user_{unique_id}"
    password = "e2e_password"
    email = f"e2e_{unique_id}@test.com"

    response = client.post("/api/v1/users/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == username

    # 로그인
    response = client.post("/api/v1/users/login", json={"username": username, "password": password})
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
    response = client.post("/api/v1/watchlist/add", json={"user_id": user_id, "symbol": symbol}, headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "종목이 관심 목록에 추가되었습니다."

    # 3. 가격 알림 설정
    response = client.post("/api/v1/alerts/", json={
            "symbol": symbol,
            "target_price": 90000,
            "condition": "gte"
        }, headers=headers)
    assert response.status_code == 200
    alert_data = response.json()
    assert alert_data["symbol"] == symbol
    assert alert_data["target_price"] == 90000

    # 4. 주가 예측
    response = client.post("/api/v1/predict", json={"symbol": symbol, "user_id": user_id}, headers=headers)
    assert response.status_code == 200
    assert response.json()["symbol"] == symbol
    assert "confidence" in response.json()
    assert isinstance(response.json()["confidence"], int)
    assert 0 <= response.json()["confidence"] <= 100

    # 5. 모의 거래
    response = client.post("/api/v1/trade/simulate", json={
        "user_id": user_id,
        "symbol": symbol,
        "trade_type": "buy",
        "price": 85000,
        "quantity": 10
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "모의매매 기록 완료"

    # 6. 거래 내역 확인
    response = client.get(f"/api/v1/trade/history/{user_id}", headers=headers)
    assert response.status_code == 200
    trade_history = response.json()
    assert len(trade_history["trades"]) == 1
    assert trade_history["trades"][0]["symbol"] == symbol
    assert trade_history["trades"][0]["trade_type"] == "buy"
    
    print("E2E 시나리오 테스트 성공")