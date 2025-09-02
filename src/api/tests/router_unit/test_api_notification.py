# src/api/tests/router_unit/test_api_notification.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.orm import Session
from datetime import datetime

from src.api.main import app
from src.common.models.user import User
from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
from src.common.services.price_alert_service import PriceAlertService

# Test data
test_user_data = {"username": "testuser", "email": "test@example.com", "role": "user", "id": 1}
test_user = User(**test_user_data)

@pytest.fixture
def mock_db_session():
    """SQLAlchemy Session의 Mock 객체를 생성합니다."""
    db = MagicMock(spec=Session)
    return db

@pytest.fixture
def client_and_service(mock_db_session):
    """의존성 주입이 Mock된 TestClient와 서비스 Mock을 생성합니다."""
    from src.common.database.db_connector import get_db
    from src.api.auth.jwt_handler import get_current_active_user
    from src.api.routers.notification import get_price_alert_service

    def override_get_db():
        yield mock_db_session

    def override_get_current_active_user():
        return test_user

    mock_price_alert_service = MagicMock(spec=PriceAlertService)
    # 비동기 메서드들을 AsyncMock으로 설정합니다.
    mock_price_alert_service.create_alert = AsyncMock()
    mock_price_alert_service.update_alert = AsyncMock()
    mock_price_alert_service.delete_alert = AsyncMock()

    def override_get_price_alert_service():
        return mock_price_alert_service

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    app.dependency_overrides[get_price_alert_service] = override_get_price_alert_service
    
    with TestClient(app) as c:
        yield c, mock_price_alert_service
    
    # 테스트 종료 후 오버라이드 복원
    app.dependency_overrides = {}

# --- Price Alert Router Unit Tests ---

def test_create_price_alert_success(client_and_service, mock_db_session):
    """가격 알림 생성 성공 테스트"""
    client, mock_price_alert_service = client_and_service
    alert_data = {"symbol": "005930", "target_price": 90000, "condition": "gte"}
    
    mock_price_alert_service.get_alert_by_user_and_symbol.return_value = None
    mock_price_alert_service.create_alert.return_value = MagicMock(
        id=1, user_id=1, is_active=True, notify_on_disclosure=False, 
        created_at=datetime.now(), updated_at=datetime.now(),
        stock_name="삼성전자", change_type=None, repeat_interval=None, **alert_data
    )

    response = client.post("/api/v1/price-alerts/", json=alert_data)

    assert response.status_code == 201
    assert response.json()["symbol"] == "005930"
    mock_price_alert_service.get_alert_by_user_and_symbol.assert_called_once_with(mock_db_session, test_user.id, "005930")
    mock_price_alert_service.create_alert.assert_called_once()

def test_create_price_alert_duplicate(client_and_service, mock_db_session):
    """가격 알림 생성 시 중복 테스트"""
    client, mock_price_alert_service = client_and_service
    alert_data = {"symbol": "005930", "target_price": 90000, "condition": "gte"}
    
    mock_price_alert_service.get_alert_by_user_and_symbol.return_value = MagicMock()
    response = client.post("/api/v1/price-alerts/", json=alert_data)

    assert response.status_code == 409
    assert "이미 해당 종목에 대한 알림이 존재합니다." in response.json()["detail"]
    mock_price_alert_service.get_alert_by_user_and_symbol.assert_called_once_with(mock_db_session, test_user.id, "005930")


def test_get_price_alerts_success(client_and_service, mock_db_session):
    """사용자 가격 알림 목록 조회 성공 테스트"""
    client, mock_price_alert_service = client_and_service
    now = datetime.now()
    mock_alerts = [
        MagicMock(id=1, symbol="005930", target_price=90000, condition="gte", user_id=1, is_active=True, notify_on_disclosure=False, created_at=now, updated_at=now, stock_name="삼성전자", change_type=None, repeat_interval=None, change_percent=None),
        MagicMock(id=2, symbol="000660", target_price=150000, condition="lte", user_id=1, is_active=True, notify_on_disclosure=True, created_at=now, updated_at=now, stock_name="SK하이닉스", change_type=None, repeat_interval=None, change_percent=None)
    ]
    mock_price_alert_service.get_alerts.return_value = mock_alerts
    response = client.get("/api/v1/price-alerts/")

    assert response.status_code == 200
    assert len(response.json()) == 2
    mock_price_alert_service.get_alerts.assert_called_once_with(mock_db_session, test_user.id)

def test_get_price_alerts_empty(client_and_service, mock_db_session):
    """사용자 가격 알림 목록이 비어있을 때 테스트"""
    client, mock_price_alert_service = client_and_service
    mock_price_alert_service.get_alerts.return_value = []
    response = client.get("/api/v1/price-alerts/")

    assert response.status_code == 200
    assert response.json() == []
    mock_price_alert_service.get_alerts.assert_called_once_with(mock_db_session, test_user.id)

def test_get_price_alert_success(client_and_service, mock_db_session):
    """특정 가격 알림 조회 성공 테스트"""
    client, mock_price_alert_service = client_and_service
    alert_id = 1
    mock_alert = MagicMock(id=alert_id, symbol="005930", target_price=90000, condition="gte", user_id=test_user.id, created_at=datetime.now(), updated_at=datetime.now(), stock_name="삼성전자", notify_on_disclosure=False, change_type=None, repeat_interval=None, change_percent=None)
    mock_price_alert_service.get_alert_by_id.return_value = mock_alert
    response = client.get(f"/api/v1/price-alerts/{alert_id}")

    assert response.status_code == 200
    assert response.json()["id"] == alert_id
    mock_price_alert_service.get_alert_by_id.assert_called_once_with(mock_db_session, alert_id)

def test_get_price_alert_not_found(client_and_service, mock_db_session):
    """존재하지 않는 가격 알림 조회 테스트 (404)"""
    client, mock_price_alert_service = client_and_service
    alert_id = 999
    mock_price_alert_service.get_alert_by_id.return_value = None
    response = client.get(f"/api/v1/price-alerts/{alert_id}")

    assert response.status_code == 404
    mock_price_alert_service.get_alert_by_id.assert_called_once_with(mock_db_session, alert_id)

def test_get_price_alert_not_owned(client_and_service, mock_db_session):
    """다른 사용자의 가격 알림 조회 테스트 (404)"""
    client, mock_price_alert_service = client_and_service
    alert_id = 1
    mock_alert = MagicMock(id=alert_id, user_id=2) # 다른 사용자의 알림
    mock_price_alert_service.get_alert_by_id.return_value = mock_alert
    response = client.get(f"/api/v1/price-alerts/{alert_id}")

    assert response.status_code == 404
    mock_price_alert_service.get_alert_by_id.assert_called_once_with(mock_db_session, alert_id)

def test_update_price_alert_success(client_and_service, mock_db_session):
    """가격 알림 수정 성공 테스트"""
    client, mock_price_alert_service = client_and_service
    alert_id = 1
    update_data = {"target_price": 95000, "is_active": False}
    
    mock_alert = MagicMock(id=alert_id, user_id=test_user.id)
    mock_price_alert_service.get_alert_by_id.return_value = mock_alert
    mock_price_alert_service.update_alert.return_value = MagicMock(id=alert_id, symbol="005930", **update_data, user_id=test_user.id, created_at=datetime.now(), updated_at=datetime.now(), notify_on_disclosure=False, stock_name="삼성전자", condition="gte", change_type=None, repeat_interval=None, change_percent=None)

    response = client.put(f"/api/v1/price-alerts/{alert_id}", json=update_data)

    assert response.status_code == 200
    assert response.json()["target_price"] == 95000
    mock_price_alert_service.get_alert_by_id.assert_called_once_with(mock_db_session, alert_id)
    mock_price_alert_service.update_alert.assert_called_once()

def test_update_price_alert_not_found(client_and_service, mock_db_session):
    """존재하지 않는 가격 알림 수정 테스트 (404)"""
    client, mock_price_alert_service = client_and_service
    alert_id = 999
    update_data = {"target_price": 95000}
    mock_price_alert_service.get_alert_by_id.return_value = None
    response = client.put(f"/api/v1/price-alerts/{alert_id}", json=update_data)

    assert response.status_code == 404
    mock_price_alert_service.get_alert_by_id.assert_called_once_with(mock_db_session, alert_id)

def test_update_price_alert_not_owned(client_and_service, mock_db_session):
    """다른 사용자의 가격 알림 수정 테스트 (404)"""
    client, mock_price_alert_service = client_and_service
    alert_id = 1
    update_data = {"target_price": 95000}
    mock_alert = MagicMock(id=alert_id, user_id=2) # 다른 사용자의 알림
    mock_price_alert_service.get_alert_by_id.return_value = mock_alert
    response = client.put(f"/api/v1/price-alerts/{alert_id}", json=update_data)

    assert response.status_code == 404
    mock_price_alert_service.get_alert_by_id.assert_called_once_with(mock_db_session, alert_id)

def test_delete_price_alert_success(client_and_service, mock_db_session):
    """가격 알림 삭제 성공 테스트"""
    client, mock_price_alert_service = client_and_service
    alert_id = 1
    mock_alert = MagicMock(id=alert_id, user_id=test_user.id)
    mock_price_alert_service.get_alert_by_id.return_value = mock_alert

    response = client.delete(f"/api/v1/price-alerts/{alert_id}")

    assert response.status_code == 204
    mock_price_alert_service.get_alert_by_id.assert_called_once_with(mock_db_session, alert_id)
    mock_price_alert_service.delete_alert.assert_called_once_with(mock_db_session, alert_id)

def test_delete_price_alert_not_found(client_and_service, mock_db_session):
    """존재하지 않는 가격 알림 삭제 테스트 (404)"""
    client, mock_price_alert_service = client_and_service
    alert_id = 999
    mock_price_alert_service.get_alert_by_id.return_value = None
    response = client.delete(f"/api/v1/price-alerts/{alert_id}")

    assert response.status_code == 404
    mock_price_alert_service.get_alert_by_id.assert_called_once_with(mock_db_session, alert_id)

def test_delete_price_alert_not_owned(client_and_service, mock_db_session):
    """다른 사용자의 가격 알림 삭제 테스트 (404)"""
    client, mock_price_alert_service = client_and_service
    alert_id = 1
    mock_alert = MagicMock(id=alert_id, user_id=2) # 다른 사용자의 알림
    mock_price_alert_service.get_alert_by_id.return_value = mock_alert
    response = client.delete(f"/api/v1/price-alerts/{alert_id}")

    assert response.status_code == 404
    mock_price_alert_service.get_alert_by_id.assert_called_once_with(mock_db_session, alert_id)
