import pytest
from fastapi.testclient import TestClient
from src.api.tests.helpers import create_test_user, get_auth_headers
from src.api.schemas.price_alert import PriceAlertRead, PriceAlertCreate, PriceAlertUpdate
from src.api.models.price_alert import PriceAlert
from unittest.mock import patch, MagicMock
from src.common.notify_service import send_telegram_message
from sqlalchemy.orm import Session


class TestPriceAlertRouter:
    """가격 알림 라우터 테스트"""

    def test_create_alert_success(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        headers = get_auth_headers(user)
        alert_payload = {"symbol": "005930", "target_price": 90000, "condition": "gte"}

        # When
        response = client.post("/alerts/", json=alert_payload, headers=headers)

        # Then
        assert response.status_code == 200
        created_alert = PriceAlertRead.parse_obj(response.json())
        assert created_alert.symbol == "005930"
        assert created_alert.target_price == 90000
        assert created_alert.condition == "gte"
        assert created_alert.user_id == user.id

    def test_create_alert_unauthenticated(self, client: TestClient):
        # Given
        alert_payload = {"symbol": "005930", "target_price": 90000, "condition": "gte"}

        # When
        response = client.post("/alerts/", json=alert_payload)

        # Then
        assert response.status_code == 403

    def test_create_alert_invalid_data(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        headers = get_auth_headers(user)
        alert_payload = {"symbol": "005930", "target_price": "invalid", "condition": "gte"} # Invalid target_price

        # When
        response = client.post("/alerts/", json=alert_payload, headers=headers)

        # Then
        assert response.status_code == 422

    def test_get_my_alerts_success(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        headers = get_auth_headers(user)
        client.post("/alerts/", json={"symbol": "005930", "target_price": 90000, "condition": "gte"}, headers=headers)
        client.post("/alerts/", json={"symbol": "035720", "target_price": 50000, "condition": "lte"}, headers=headers)

        # When
        response = client.get("/alerts/", headers=headers)

        # Then
        assert response.status_code == 200
        alerts = [PriceAlertRead.parse_obj(a) for a in response.json()]
        assert len(alerts) == 2
        assert any(a.symbol == "005930" for a in alerts)
        assert any(a.symbol == "035720" for a in alerts)

    def test_get_my_alerts_empty(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        headers = get_auth_headers(user)

        # When
        response = client.get("/alerts/", headers=headers)

        # Then
        assert response.status_code == 200
        assert response.json() == []

    def test_get_my_alerts_unauthenticated(self, client: TestClient):
        # When
        response = client.get("/alerts/")

        # Then
        assert response.status_code == 403

    def test_get_alert_by_user_and_symbol_success(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        client.post("/alerts/", json={"symbol": "005930", "target_price": 90000, "condition": "gte"}, headers=get_auth_headers(user))

        # When
        response = client.get(f"/alerts/user/{user.id}/symbol/005930")

        # Then
        assert response.status_code == 200
        alert = PriceAlertRead.parse_obj(response.json())
        assert alert.symbol == "005930"
        assert alert.user_id == user.id

    def test_get_alert_by_user_and_symbol_not_found(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)

        # When
        response = client.get(f"/alerts/user/{user.id}/symbol/NONEXISTENT")

        # Then
        assert response.status_code == 404
        assert response.json() == {"detail": "해당 종목에 대한 알림 설정을 찾을 수 없습니다."}

    def test_update_alert_success(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        headers = get_auth_headers(user)
        create_response = client.post("/alerts/", json={"symbol": "005930", "target_price": 90000, "condition": "gte"}, headers=headers)
        alert_id = create_response.json()["id"]

        # When
        update_payload = {"target_price": 95000, "condition": "lte", "is_active": False}
        response = client.put(f"/alerts/{alert_id}", json=update_payload, headers=headers)

        # Then
        assert response.status_code == 200
        updated_alert = PriceAlertRead.parse_obj(response.json())
        assert updated_alert.id == alert_id
        assert updated_alert.target_price == 95000
        assert updated_alert.condition == "lte"
        assert updated_alert.is_active is False

    def test_update_alert_unauthenticated(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        create_response = client.post("/alerts/", json={"symbol": "005930", "target_price": 90000, "condition": "gte"}, headers=get_auth_headers(user))
        alert_id = create_response.json()["id"]

        # When
        update_payload = {"target_price": 95000}
        response = client.put(f"/alerts/{alert_id}", json=update_payload)

        # Then
        assert response.status_code == 403

    def test_update_alert_not_found(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        headers = get_auth_headers(user)

        # When
        update_payload = {"target_price": 95000}
        response = client.put(f"/alerts/99999", json=update_payload, headers=headers)

        # Then
        assert response.status_code == 404

    def test_update_alert_forbidden(self, client: TestClient, db: Session):
        # Given
        user1 = create_test_user(db)
        user2 = create_test_user(db)
        headers2 = get_auth_headers(user2)
        create_response = client.post("/alerts/", json={"symbol": "005930", "target_price": 90000, "condition": "gte"}, headers=get_auth_headers(user1))
        alert_id = create_response.json()["id"]

        # When
        update_payload = {"target_price": 95000}
        response = client.put(f"/alerts/{alert_id}", json=update_payload, headers=headers2)

        # Then
        assert response.status_code == 403

    def test_delete_alert_success(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        headers = get_auth_headers(user)
        create_response = client.post("/alerts/", json={"symbol": "005930", "target_price": 90000, "condition": "gte"}, headers=headers)
        alert_id = create_response.json()["id"]

        # When
        response = client.delete(f"/alerts/{alert_id}", headers=headers)

        # Then
        assert response.status_code == 200
        assert response.json() == {"result": True}
        # DB에서 실제로 삭제되었는지 확인
        assert db.query(PriceAlert).filter_by(id=alert_id).first() is None

    def test_delete_alert_unauthenticated(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        create_response = client.post("/alerts/", json={"symbol": "005930", "target_price": 90000, "condition": "gte"}, headers=get_auth_headers(user))
        alert_id = create_response.json()["id"]

        # When
        response = client.delete(f"/alerts/{alert_id}")

        # Then
        assert response.status_code == 403

    def test_delete_alert_not_found(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        headers = get_auth_headers(user)

        # When
        response = client.delete(f"/alerts/99999", headers=headers)

        # Then
        assert response.status_code == 404

    def test_delete_alert_forbidden(self, client: TestClient, db: Session):
        # Given
        user1 = create_test_user(db)
        user2 = create_test_user(db)
        headers2 = get_auth_headers(user2)
        create_response = client.post("/alerts/", json={"symbol": "005930", "target_price": 90000, "condition": "gte"}, headers=get_auth_headers(user1))
        alert_id = create_response.json()["id"]

        # When
        response = client.delete(f"/alerts/{alert_id}", headers=headers2)

        # Then
        assert response.status_code == 403

    @patch('src.api.routers.notification.send_telegram_message')
    def test_test_notify_api_success(self, mock_send_telegram_message, client: TestClient):
        # Given
        chat_id = 123456789
        text = "테스트 메시지입니다."

        # When
        response = client.post("/alerts/test_notify", json={"chat_id": chat_id, "text": text})

        # Then
        assert response.status_code == 200
        assert response.json() == {"result": True, "message": "메시지 전송 성공"}
        mock_send_telegram_message.assert_called_once_with(chat_id, text)

    @patch('src.api.routers.notification.send_telegram_message')
    def test_test_notify_api_failure(self, mock_send_telegram_message, client: TestClient):
        # Given
        chat_id = 123456789
        text = "테스트 메시지입니다."
        mock_send_telegram_message.side_effect = Exception("Telegram API Error")

        # When
        response = client.post("/alerts/test_notify", json={"chat_id": chat_id, "text": text})

        # Then
        assert response.status_code == 200 # API 자체는 200을 반환하고 내부 오류를 메시지로 전달
        assert response.json() == {"result": False, "error": "Telegram API Error"}
        mock_send_telegram_message.assert_called_once_with(chat_id, text)