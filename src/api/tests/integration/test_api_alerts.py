import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.common.models.user import User
from src.common.models.price_alert import PriceAlert

class TestTelegramAlertRouter:
    """텔레그램 봇을 통한 가격 알림 라우터 테스트"""

    def test_alert_scenario(self, client: TestClient, real_db: Session):
        """알림 생성, 조회, 수정, 삭제 전체 시나리오 테스트"""
        telegram_id = 123456789
        symbol = "005930"

        # 1. 신규 알림 생성 (사용자도 함께 생성되어야 함)
        create_payload = {
            "telegram_id": telegram_id,
            "symbol": symbol,
            "target_price": 80000,
            "condition": "gte",
            "is_active": True
        }
        create_response = client.post("/api/v1/alerts/", json=create_payload)
        assert create_response.status_code == 200
        created_alert = create_response.json()
        assert created_alert["symbol"] == symbol
        assert created_alert["target_price"] == 80000
        assert created_alert["is_active"] is True

        # DB에서 사용자 및 알림 확인
        user = real_db.query(User).filter(User.telegram_id == telegram_id).first()
        assert user is not None
        alert_in_db = real_db.query(PriceAlert).filter(PriceAlert.user_id == user.id, PriceAlert.symbol == symbol).first()
        assert alert_in_db is not None
        assert alert_in_db.target_price == 80000

        # 2. 알림 목록 조회
        list_response = client.get(f"/api/v1/alerts/{telegram_id}")
        assert list_response.status_code == 200
        alerts = list_response.json()
        assert len(alerts) == 1
        assert alerts[0]["symbol"] == symbol

        # 3. 알림 수정 (공시 알림 켜기)
        update_payload = {"notify_on_disclosure": True}
        update_response = client.put(f"/api/v1/alerts/{telegram_id}/{symbol}", json=update_payload)
        assert update_response.status_code == 200
        updated_alert = update_response.json()
        assert updated_alert["notify_on_disclosure"] is True
        alert_in_db = real_db.query(PriceAlert).filter(PriceAlert.user_id == user.id, PriceAlert.symbol == symbol).first() # DB 객체 새로고침
        assert alert_in_db.notify_on_disclosure is True

        # 4. 알림 삭제
        delete_response = client.delete(f"/api/v1/alerts/{telegram_id}/{symbol}")
        assert delete_response.status_code == 200
        assert delete_response.json()["result"] is True

        # DB에서 알림 삭제 확인
        alert_after_delete = real_db.query(PriceAlert).filter(PriceAlert.user_id == user.id, PriceAlert.symbol == symbol).first()
        assert alert_after_delete is None

        # 5. 알림 목록 재조회 (비어 있어야 함)
        final_list_response = client.get(f"/api/v1/alerts/{telegram_id}")
        assert final_list_response.status_code == 200
        assert final_list_response.json() == []

    def test_create_alert_invalid_data(self, client: TestClient):
        """유효하지 않은 데이터로 알림 생성 시 422 오류 테스트"""
        payload = {
            "telegram_id": 987654321,
            "symbol": "005930",
            "target_price": "invalid_price", # 잘못된 타입
            "condition": "gte"
        }
        response = client.post("/api/v1/alerts/", json=payload)
        assert response.status_code == 422

    def test_get_alerts_no_user(self, client: TestClient):
        """존재하지 않는 사용자의 알림 목록 조회 시 빈 리스트 반환 테스트"""
        response = client.get("/api/v1/alerts/999999999")
        assert response.status_code == 200
        assert response.json() == []

    def test_update_alert_not_found(self, client: TestClient):
        """존재하지 않는 알림 수정 시 404 오류 테스트"""
        telegram_id = 111222333
        # 먼저 사용자 생성
        client.post("/api/v1/alerts/", json={"telegram_id": telegram_id, "symbol": "000020", "target_price": 10000})
        
        update_payload = {"target_price": 12000}
        response = client.put(f"/api/v1/alerts/{telegram_id}/NONEXISTENT_SYMBOL", json=update_payload)
        assert response.status_code == 404

    def test_delete_alert_not_found(self, client: TestClient):
        """존재하지 않는 알림 삭제 시 404 오류 테스트"""
        telegram_id = 444555666
        # 먼저 사용자 생성
        client.post("/api/v1/alerts/", json={"telegram_id": telegram_id, "symbol": "000040", "target_price": 20000})

        response = client.delete(f"/alerts/{telegram_id}/NONEXISTENT_SYMBOL")
        assert response.status_code == 404
