import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.main import app, get_db
from src.common.db_connector import Base
from src.api.models.user import User
from src.api.models.price_alert import PriceAlert
from src.api.models.watchlist import Watchlist
from src.api.models.stock_master import StockMaster
from src.api.models.daily_price import DailyPrice
from src.api.models.disclosure import Disclosure
from src.api.models.prediction_history import PredictionHistory
from src.api.models.simulated_trade import SimulatedTrade

# 테스트용 데이터베이스 설정
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 테스트 데이터베이스 의존성 오버라이드
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def db_session():
    # 테스트 시작 전 DB 테이블 생성
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    # 테스트 종료 후 DB 테이블 삭제
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client():
    # 테스트 클라이언트 생성
    with TestClient(app) as c:
        yield c

# ===================================
#  테스트 케이스
# ===================================

def test_auto_create_user_and_toggle_disclosure_alert(client, db_session):
    """
    사용자가 존재하지 않을 때, 공시 알림 토글 시 사용자가 자동 생성되고
    알림이 정상적으로 등록되는지 테스트
    """
    # GIVEN: 존재하지 않는 사용자 ID와 종목 코드
    test_telegram_user_id = 123456789
    test_symbol = "005930" # 삼성전자

    # WHEN: 공시 알림 토글 API를 호출
    response = client.post(
        "/bot/alert/disclosure-toggle",
        json={
            "telegram_user_id": test_telegram_user_id,
            "telegram_username": "testuser",
            "telegram_first_name": "Test",
            "telegram_last_name": "User",
            "symbol": test_symbol
        }
    )

    # THEN: API 응답이 성공(200)이어야 함
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["message"] == "공시 알림이 켜졌습니다."

    # THEN: 데이터베이스에 사용자가 생성되었는지 확인
    user = db_session.query(User).filter(User.telegram_user_id == test_telegram_user_id).first()
    assert user is not None
    assert user.telegram_username == "testuser"

    # THEN: 데이터베이스에 공시 알림이 생성되었는지 확인
    alert = db_session.query(PriceAlert).filter(
        PriceAlert.user_id == user.id,
        PriceAlert.symbol == test_symbol
    ).first()
    assert alert is not None
    assert alert.notify_on_disclosure is True


def test_set_price_alert_for_existing_user(client, db_session):
    """
    기존 사용자에게 가격 알림을 설정하는 기능 테스트
    """
    # GIVEN: 기존 사용자 및 알림 생성
    user = User(telegram_user_id=987654321, telegram_username="existinguser")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    test_symbol = "000660" # SK하이닉스
    test_target_price = 150000
    test_condition = "이상"

    # WHEN: 가격 알림 설정 API 호출
    response = client.post(
        "/bot/alert/price",
        json={
            "telegram_user_id": user.telegram_user_id,
            "symbol": test_symbol,
            "target_price": test_target_price,
            "condition": test_condition
        }
    )

    # THEN: API 응답이 성공(200)이어야 함
    assert response.status_code == 200
    assert "가격 알림이 설정되었습니다." in response.json()["message"]

    # THEN: 데이터베이스에 가격 알림이 올바르게 설정되었는지 확인
    alert = db_session.query(PriceAlert).filter(
        PriceAlert.user_id == user.id,
        PriceAlert.symbol == test_symbol
    ).first()
    assert alert is not None
    assert alert.target_price == test_target_price
    assert alert.condition == test_condition
    assert alert.notify_on_disclosure is False # 기본값 확인


def test_get_alerts_for_user(client, db_session):
    """
    특정 사용자의 모든 알림 목록을 조회하는 기능 테스트
    """
    # GIVEN: 사용자 및 여러 알림 생성
    user = User(telegram_user_id=11223344, telegram_username="alertlistuser")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    alert1 = PriceAlert(user_id=user.id, symbol="005930", target_price=90000, condition="이상", notify_on_disclosure=True)
    alert2 = PriceAlert(user_id=user.id, symbol="035720", notify_on_disclosure=True) # 카카오, 공시만
    alert3 = PriceAlert(user_id=user.id, symbol="000660", target_price=120000, condition="이하")

    db_session.add_all([alert1, alert2, alert3])
    db_session.commit()

    # WHEN: 해당 사용자의 알림 목록 API 호출
    response = client.get(f"/alerts/user/{user.id}")

    # THEN: API 응답이 성공(200)이어야 함
    assert response.status_code == 200
    alerts = response.json()
    
    # THEN: 알림 개수가 일치해야 함
    assert len(alerts) == 3

    # THEN: 각 알림의 내용이 올바른지 확인 (symbol 기준 정렬 후 비교)
    sorted_alerts = sorted(alerts, key=lambda x: x['symbol'])
    assert sorted_alerts[0]["symbol"] == "000660"
    assert sorted_alerts[1]["symbol"] == "005930"
    assert sorted_alerts[1]["notify_on_disclosure"] is True
    assert sorted_alerts[2]["symbol"] == "035720"
    assert sorted_alerts[2]["target_price"] is None 