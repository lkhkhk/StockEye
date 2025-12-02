# src/api/tests/integration/test_api_bot_router_integration.py
"""
API 통합 테스트: 봇 전용 라우터 API

이 파일은 `/bot/alert/` 엔드포인트 그룹에 대한 통합 테스트를 포함합니다.
이 API는 텔레그램 봇의 다양한 사용자 상호작용(버튼 클릭, 명령어 등)에 대한
백엔드 로직을 처리하는 역할을 합니다.

`TestClient`를 사용하여 API 요청을 보내고, `real_db`와 `test_user` fixture를 통해
실제 데이터베이스 및 사용자 컨텍스트 하에서 테스트를 수행합니다.
테스트 데이터 준비를 위해 서비스 계층(`PriceAlertService`)을 직접 사용하기도 합니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.main import app
from src.common.models.user import User
from src.common.models.price_alert import PriceAlert
from src.common.schemas.price_alert import PriceAlertCreate
from src.common.services.price_alert_service import PriceAlertService

# TestClient 인스턴스 생성 제거 (fixture 사용)
# client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def override_bot_router_dependencies(real_db: Session):
    """
    봇 라우터의 의존성을 오버라이드하는 Fixture.

    - **목적**: 향후 봇 라우터의 서비스 의존성(UserService, PriceAlertService 등)을
              테스트용으로 교체해야 할 경우를 대비한 확장 지점입니다.
              현재는 특별한 오버라이드를 수행하지 않습니다.
    - **적용**: `autouse=True`로 설정되어 이 모듈의 모든 테스트에 자동으로 적용됩니다.
    """
    # 현재는 특별한 오버라이드가 필요 없으므로 pass
    pass


@pytest.mark.asyncio
async def test_toggle_disclosure_alert_new_user_and_alert(client, real_db: Session, test_user: User, test_stock_master_data):
    """
    - **테스트 대상**: `POST /bot/alert/disclosure-toggle`
    - **목적**: 신규 사용자가 특정 종목에 대해 공시 알림을 처음 켰을 때, 알림이 정상적으로 생성되는지 확인합니다.
    - **시나리오**:
        1. `test_user` fixture로 생성된 사용자의 정보와 새로운 종목 코드로 API를 호출합니다.
        2. 200 OK 응답과 함께, `notify_on_disclosure`가 `True`로 설정된 알림 정보가 반환되는지 확인합니다.
    - **Mock 대상**: 없음
    """
    response = client.post(
        "/api/v1/bot/alert/disclosure-toggle",
        json={"telegram_user_id": test_user.telegram_id, "telegram_username": test_user.username, "symbol": "GOOG"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "GOOG"
    assert data["notify_on_disclosure"] is True


@pytest.mark.asyncio
async def test_toggle_disclosure_alert_existing_alert_on_to_off(client, real_db: Session, test_user: User, test_stock_master_data):
    """
    - **테스트 대상**: `POST /bot/alert/disclosure-toggle`
    - **목적**: 기존에 켜져 있던 공시 알림을 껐을 때, `notify_on_disclosure`가 `False`로 업데이트되는지 확인합니다.
    - **시나리오**:
        1. `notify_on_disclosure=True` 상태인 알림을 미리 생성합니다.
        2. 동일한 종목 코드로 API를 호출하여 알림을 토글합니다.
        3. 200 OK 응답과 함께, `notify_on_disclosure`가 `False`로 변경된 정보가 반환되는지 확인합니다.
        4. DB에서도 해당 알림의 상태가 `False`로 변경되었는지 검증합니다.
    - **Mock 대상**: 없음
    """
    # Given: 공시 알림이 켜진 초기 데이터 생성
    price_alert_service = PriceAlertService()
    initial_alert = await price_alert_service.create_alert(
        real_db, user_id=test_user.id, alert_data=PriceAlertCreate(symbol="AMZN", notify_on_disclosure=True, is_active=True)
    )

    # When: API 호출
    response = client.post(
        "/api/v1/bot/alert/disclosure-toggle",
        json={"telegram_user_id": test_user.telegram_id, "symbol": initial_alert.symbol}
    )

    # Then: 결과 검증
    assert response.status_code == 200
    assert response.json()["notify_on_disclosure"] is False
    updated_alert_in_db = real_db.query(PriceAlert).filter(PriceAlert.id == initial_alert.id).first()
    assert updated_alert_in_db.notify_on_disclosure is False


@pytest.mark.asyncio
async def test_set_price_alert_existing_user_new_alert(client, real_db: Session, test_user: User, test_stock_master_data):
    """
    - **테스트 대상**: `POST /bot/alert/price`
    - **목적**: 기존 사용자가 새로운 가격 알림을 설정했을 때, 알림이 정상적으로 생성되는지 확인합니다.
    - **시나리오**:
        1. 가격, 조건 등을 포함한 페이로드로 API를 호출합니다.
        2. 200 OK 응답과 함께, 요청한 내용대로 알림이 생성되었는지 확인합니다.
    - **Mock 대상**: 없음
    """
    response = client.post(
        "/api/v1/bot/alert/price",
        json={
            "telegram_user_id": test_user.telegram_id,
            "telegram_username": test_user.username,
            "symbol": "NVDA",
            "target_price": 1000.0,
            "condition": "lte"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["target_price"] == 1000.0
    assert data["condition"] == "lte"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_set_price_alert_existing_alert_update(client, real_db: Session, test_user: User, test_stock_master_data):
    """
    - **테스트 대상**: `POST /bot/alert/price`
    - **목적**: 기존에 있던 가격 알림을 새로운 정보로 업데이트하는 기능이 정상 동작하는지 확인합니다.
    - **시나리오**:
        1. 초기 가격 알림을 하나 생성합니다.
        2. 동일한 종목에 대해 다른 가격, 조건, 반복 설정으로 API를 호출합니다.
        3. 200 OK 응답과 함께, 알림 정보가 요청한 내용대로 업데이트되었는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given: 초기 가격 알림 생성
    price_alert_service = PriceAlertService()
    await price_alert_service.create_alert(
        real_db, user_id=test_user.id, alert_data=PriceAlertCreate(symbol="GOOGL", target_price=100.0, condition="gte")
    )

    # When: 새로운 정보로 업데이트 요청
    response = client.post(
        "/api/v1/bot/alert/price",
        json={
            "telegram_user_id": test_user.telegram_id,
            "symbol": "GOOGL",
            "target_price": 110.0,
            "condition": "lte",
            "repeat_interval": "weekly"
        }
    )

    # Then: 결과 검증
    assert response.status_code == 200
    data = response.json()
    assert data["target_price"] == 110.0
    assert data["condition"] == "lte"
    assert data["repeat_interval"] == "weekly"
    assert data["is_active"] is True  # 업데이트 시 활성화 상태가 되어야 함


@pytest.mark.asyncio
async def test_list_alerts_for_bot(client, real_db: Session, test_user: User, test_stock_master_data):
    """
    - **테스트 대상**: `POST /bot/alert/list`
    - **목적**: 특정 사용자의 모든 알림 목록을 정상적으로 조회하는지 확인합니다.
    - **시나리오**:
        1. 테스트 사용자에 대해 여러 종류의 알림(가격, 공시)을 생성합니다.
        2. 해당 사용자의 `telegram_id`로 목록 조회 API를 호출합니다.
        3. 200 OK 응답과 함께, 생성된 모든 알림이 포함된 리스트가 반환되는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given: 테스트용 알림 2개 생성
    price_alert_service = PriceAlertService()
    await price_alert_service.create_alert(real_db, user_id=test_user.id, alert_data=PriceAlertCreate(symbol="AAPL", target_price=150.0, condition="gte"))
    await price_alert_service.create_alert(real_db, user_id=test_user.id, alert_data=PriceAlertCreate(symbol="GOOG", notify_on_disclosure=True))

    # When: 목록 조회 API 호출
    response = client.post("/api/v1/bot/alert/list", json={"telegram_user_id": test_user.telegram_id})

    # Then: 결과 검증
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(a["symbol"] == "AAPL" for a in data)
    assert any(a["symbol"] == "GOOG" for a in data)


def test_list_alerts_for_bot_no_alerts(client, real_db: Session, test_user: User, test_stock_master_data):
    """
    - **테스트 대상**: `POST /bot/alert/list`
    - **목적**: 알림이 없는 사용자에 대해 빈 리스트를 정상적으로 반환하는지 확인합니다.
    - **시나리오**:
        1. 알림이 없는 사용자의 `telegram_id`로 목록 조회 API를 호출합니다.
        2. 200 OK 응답과 함께 빈 리스트가 반환되는지 확인합니다.
    - **Mock 대상**: 없음
    """
    response = client.post("/api/v1/bot/alert/list", json={"telegram_user_id": test_user.telegram_id})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_remove_alert_for_bot_success(client, real_db: Session, test_user: User, test_stock_master_data):
    """
    - **테스트 대상**: `POST /bot/alert/remove`
    - **목적**: 특정 알림을 ID를 통해 성공적으로 삭제하는지 확인합니다.
    - **시나리오**:
        1. 삭제할 알림을 미리 생성합니다.
        2. 해당 알림의 ID로 삭제 API를 호출합니다.
        3. 200 OK 응답과 성공 메시지를 확인합니다.
        4. 알림 목록을 다시 조회하여 해당 알림이 삭제되었는지 최종 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given: 삭제할 알림 생성
    price_alert_service = PriceAlertService()
    alert = await price_alert_service.create_alert(real_db, user_id=test_user.id, alert_data=PriceAlertCreate(symbol="AAPL", target_price=100.0))

    # When: 삭제 API 호출
    response = client.post("/api/v1/bot/alert/remove", json={"telegram_user_id": test_user.telegram_id, "alert_id": alert.id})

    # Then: 결과 검증
    assert response.status_code == 200
    assert response.json()["message"] == f"Alert {alert.id} removed successfully"
    list_response = client.post("/api/v1/bot/alert/list", json={"telegram_user_id": test_user.telegram_id})
    assert len(list_response.json()) == 0


def test_remove_alert_for_bot_not_found(client, real_db: Session):
    """
    - **테스트 대상**: `POST /bot/alert/remove`
    - **목적**: 존재하지 않는 사용자나 알림에 대해 삭제 시도 시 404 에러를 반환하는지 확인합니다.
    - **시나리오**:
        1. 존재하지 않는 `telegram_user_id`와 `alert_id`로 삭제 API를 호출합니다.
        2. 404 Not Found 응답을 확인합니다.
    - **Mock 대상**: 없음
    """
    response = client.post("/api/v1/bot/alert/remove", json={"telegram_user_id": 99999, "alert_id": 99999})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_alert_for_bot_unauthorized(client, real_db: Session, test_user: User, test_stock_master_data):
    """
    - **테스트 대상**: `POST /bot/alert/remove`
    - **목적**: 다른 사용자의 알림을 삭제하려고 할 때, 권한 없음(또는 찾을 수 없음) 오류를 반환하는지 확인합니다.
    - **시나리오**:
        1. 별도의 사용자(`other_user`)와 그 사용자의 알림을 생성합니다.
        2. `test_user`의 `telegram_id`를 사용하여 `other_user`의 알림 삭제를 시도합니다.
        3. 404 Not Found 응답과 "Alert not found or not authorized" 메시지를 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given: 다른 사용자와 그의 알림 생성
    other_user = User(telegram_id=98765, username="other_user")
    real_db.add(other_user)
    real_db.commit()
    price_alert_service = PriceAlertService()
    alert = await price_alert_service.create_alert(real_db, user_id=other_user.id, alert_data=PriceAlertCreate(symbol="AAPL", notify_on_disclosure=True))

    # When: test_user가 other_user의 알림 삭제 시도
    response = client.post("/api/v1/bot/alert/remove", json={"telegram_user_id": test_user.telegram_id, "alert_id": alert.id})

    # Then: 결과 검증
    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found or not authorized"


@pytest.mark.asyncio
async def test_deactivate_alert_for_bot_success(client, real_db: Session, test_user: User, test_stock_master_data):
    """
    - **테스트 대상**: `POST /bot/alert/deactivate`
    - **목적**: 특정 알림을 성공적으로 비활성화하는지 확인합니다.
    - **시나리오**:
        1. 활성화된 알림을 미리 생성합니다.
        2. 해당 알림의 ID로 비활성화 API를 호출합니다.
        3. 200 OK 응답과 함께, `is_active`가 `False`로 변경된 알림 정보가 반환되는지 확인합니다.
        4. DB에서도 해당 알림이 비활성화되었는지 검증합니다.
    - **Mock 대상**: 없음
    """
    # Given: 활성화된 알림 생성
    price_alert_service = PriceAlertService()
    alert = await price_alert_service.create_alert(real_db, user_id=test_user.id, alert_data=PriceAlertCreate(symbol="AAPL", is_active=True, notify_on_disclosure=True))

    # When: 비활성화 API 호출
    response = client.post("/api/v1/bot/alert/deactivate", json={"telegram_user_id": test_user.telegram_id, "alert_id": alert.id})

    # Then: 결과 검증
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    deactivated_alert = real_db.query(PriceAlert).filter(PriceAlert.id == alert.id).first()
    assert deactivated_alert.is_active is False