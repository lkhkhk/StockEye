import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, ANY, MagicMock
from src.api.main import app
from src.common.models.user import User
from src.common.models.price_alert import PriceAlert
from src.api.routers.bot_router import get_user_service, get_price_alert_service # Import the actual dependency functions
from datetime import datetime # Added this import

client = TestClient(app)

# 테스트용 데이터
mock_user = User(id=1, telegram_id=12345, username="testuser")
# Ensure all fields are present and valid for Pydantic validation
mock_alert = PriceAlert(
    id=1, user_id=1, symbol="005930", notify_on_disclosure=False, is_active=True,
    created_at=datetime.now(), updated_at=datetime.now(),
    target_price=None, condition=None, change_percent=None, change_type=None, repeat_interval=None
)
mock_updated_alert = PriceAlert(
    id=1, user_id=1, symbol="005930", notify_on_disclosure=True, is_active=True,
    created_at=datetime.now(), updated_at=datetime.now(),
    target_price=None, condition=None, change_percent=None, change_type=None, repeat_interval=None
)

def test_toggle_disclosure_alert_for_bot_existing_user_and_alert():
    """기존 사용자 및 알림이 있을 때 공시 알림 토글 테스트"""
    mock_user_service_instance = MagicMock()
    mock_price_alert_service_instance = MagicMock()

    app.dependency_overrides[get_user_service] = lambda: mock_user_service_instance
    app.dependency_overrides[get_price_alert_service] = lambda: mock_price_alert_service_instance

    mock_user_service_instance.get_user_by_telegram_id.return_value = mock_user
    mock_price_alert_service_instance.get_alert_by_user_and_symbol.return_value = mock_alert
    mock_price_alert_service_instance.update_alert = AsyncMock(return_value=mock_updated_alert)

    response = client.post(
        "/api/v1/bot/alert/disclosure-toggle",
        json={"telegram_user_id": 12345, "symbol": "005930"}
    )

    assert response.status_code == 200
    assert response.json()["notify_on_disclosure"] is True
    mock_user_service_instance.get_user_by_telegram_id.assert_called_once_with(ANY, 12345)
    mock_price_alert_service_instance.get_alert_by_user_and_symbol.assert_called_once_with(ANY, user_id=1, symbol="005930")
    mock_price_alert_service_instance.update_alert.assert_awaited_once()

    app.dependency_overrides.clear()

def test_toggle_disclosure_alert_for_bot_new_user():
    """신규 사용자일 때 공시 알림 생성 테스트"""
    mock_user_service_instance = MagicMock()
    mock_price_alert_service_instance = MagicMock()

    app.dependency_overrides[get_user_service] = lambda: mock_user_service_instance
    app.dependency_overrides[get_price_alert_service] = lambda: mock_price_alert_service_instance

    mock_user_service_instance.get_user_by_telegram_id.return_value = None
    mock_user_service_instance.create_user_from_telegram.return_value = mock_user
    mock_price_alert_service_instance.get_alert_by_user_and_symbol.return_value = None
    mock_price_alert_service_instance.create_alert = AsyncMock(return_value=mock_updated_alert)

    response = client.post(
        "/api/v1/bot/alert/disclosure-toggle",
        json={"telegram_user_id": 12345, "telegram_username": "newuser", "symbol": "005930", "notify_on_disclosure": True}
    )

    assert response.status_code == 200
    assert response.json()["notify_on_disclosure"] is True
    mock_user_service_instance.get_user_by_telegram_id.assert_called_once_with(ANY, 12345)
    mock_user_service_instance.create_user_from_telegram.assert_called_once()
    mock_price_alert_service_instance.get_alert_by_user_and_symbol.assert_called_once_with(ANY, user_id=1, symbol="005930")
    mock_price_alert_service_instance.create_alert.assert_awaited_once()

    app.dependency_overrides.clear()

def test_set_price_alert_for_bot_existing_alert():
    """기존 알림이 있을 때 가격 알림 업데이트 테스트"""
    mock_user_service_instance = MagicMock()
    mock_price_alert_service_instance = MagicMock()

    app.dependency_overrides[get_user_service] = lambda: mock_user_service_instance
    app.dependency_overrides[get_price_alert_service] = lambda: mock_price_alert_service_instance
    
    mock_user_service_instance.get_user_by_telegram_id.return_value = mock_user
    mock_price_alert_service_instance.get_alert_by_user_and_symbol.return_value = mock_alert
    
    updated_price_alert = PriceAlert(
        id=1, user_id=1, symbol="005930", target_price=80000.0, condition="above",
        created_at=datetime.now(), updated_at=datetime.now(),
        notify_on_disclosure=False, is_active=True, change_percent=None, change_type=None, repeat_interval=None
    )
    mock_price_alert_service_instance.update_alert = AsyncMock(return_value=updated_price_alert)

    response = client.post(
        "/api/v1/bot/alert/price",
        json={"telegram_user_id": 12345, "symbol": "005930", "target_price": 80000.0, "condition": "above"}
    )
    
    assert response.status_code == 200
    assert response.json()["target_price"] == 80000.0
    mock_price_alert_service_instance.update_alert.assert_awaited_once()

    app.dependency_overrides.clear()

def test_list_alerts_for_bot_user_not_found():
    """사용자를 찾을 수 없을 때 알림 목록 조회 실패 테스트"""
    mock_user_service_instance = MagicMock()
    app.dependency_overrides[get_user_service] = lambda: mock_user_service_instance

    mock_user_service_instance.get_user_by_telegram_id.return_value = None
    
    response = client.post("/api/v1/bot/alert/list", json={"telegram_user_id": 99999})
    
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

    app.dependency_overrides.clear()

def test_remove_alert_for_bot_unauthorized():
    """권한 없는 알림 삭제 시도 테스트"""
    mock_user_service_instance = MagicMock()
    mock_price_alert_service_instance = MagicMock()

    app.dependency_overrides[get_user_service] = lambda: mock_user_service_instance
    app.dependency_overrides[get_price_alert_service] = lambda: mock_price_alert_service_instance

    mock_user_service_instance.get_user_by_telegram_id.return_value = mock_user
    
    other_user_alert = PriceAlert(
        id=2, user_id=2, symbol="005930",
        created_at=datetime.now(), updated_at=datetime.now(),
        notify_on_disclosure=False, is_active=True, target_price=None, condition=None, change_percent=None, change_type=None, repeat_interval=None
    )
    mock_price_alert_service_instance.get_alert_by_id.return_value = other_user_alert # Fixed: removed AsyncMock
    
    response = client.post("/api/v1/bot/alert/remove", json={"telegram_user_id": 12345, "alert_id": 2})
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found or not authorized"

    app.dependency_overrides.clear()

def test_deactivate_alert_for_bot_success():
    """알림 비활성화 성공 테스트"""
    mock_user_service_instance = MagicMock()
    mock_price_alert_service_instance = MagicMock()

    app.dependency_overrides[get_user_service] = lambda: mock_user_service_instance
    app.dependency_overrides[get_price_alert_service] = lambda: mock_price_alert_service_instance

    mock_user_service_instance.get_user_by_telegram_id.return_value = mock_user
    
    deactivated_alert = PriceAlert(
        id=1, user_id=1, symbol="005930", is_active=False,
        created_at=datetime.now(), updated_at=datetime.now(),
        notify_on_disclosure=False, target_price=None, condition=None, change_percent=None, change_type=None, repeat_interval=None
    )
    mock_price_alert_service_instance.get_alert_by_id.return_value = mock_alert # Fixed: removed AsyncMock
    mock_price_alert_service_instance.update_alert = AsyncMock(return_value=deactivated_alert)
    
    response = client.post("/api/v1/bot/alert/deactivate", json={"telegram_user_id": 12345, "alert_id": 1})
    
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    mock_price_alert_service_instance.update_alert.assert_awaited_once()

    app.dependency_overrides.clear()