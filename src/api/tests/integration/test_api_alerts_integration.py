# src/api/tests/integration/test_api_alerts_integration.py
"""
API 통합 테스트: 텔레그램 봇 알림 API

이 파일은 `/api/v1/alerts/` 엔드포인트 그룹에 대한 통합 테스트를 포함합니다.
이 API는 텔레그램 봇으로부터 가격 알림 설정 요청을 받아 처리하는 역할을 합니다.
`TestClient`를 사용하여 API 요청을 보내고, `real_db` fixture를 통해 실제 데이터베이스와의
상호작용을 검증합니다. 서비스 계층에 대한 모의(Mock)는 사용하지 않습니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.common.models.user import User
from src.common.models.price_alert import PriceAlert


class TestTelegramAlertRouter:
    """
    `/api/v1/alerts` 라우터에 대한 통합 테스트 클래스.
    """

    def test_alert_scenario(self, client: TestClient, real_db: Session):
        """
        - **테스트 대상**: `/api/v1/alerts/` 전체 엔드포인트 (POST, GET, PUT, DELETE)
        - **목적**: 가격 알림의 생성, 조회, 수정, 삭제(CRUD) 전체 시나리오가 정상적으로 동작하는지 확인합니다.
        - **시나리오**:
            1. 새로운 가격 알림을 생성합니다. (이 과정에서 사용자도 함께 생성됩니다.)
            2. 생성된 알림이 목록에 정상적으로 조회되는지 확인합니다.
            3. 생성된 알림의 설정을 (공시 알림) 수정합니다.
            4. 수정된 알림을 삭제합니다.
            5. 삭제 후 알림 목록이 비어있는지 확인합니다.
        - **Mock 대상**: 없음
        """
        telegram_id = 123456789
        symbol = "005930"

        # 1. 신규 알림 생성
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

        # DB에서 사용자 및 알림 생성 확인
        user_in_db = real_db.query(User).filter(User.telegram_id == telegram_id).first()
        assert user_in_db is not None
        alert_in_db = real_db.query(PriceAlert).filter(PriceAlert.user_id == user_in_db.id, PriceAlert.symbol == symbol).first()
        assert alert_in_db is not None
        assert alert_in_db.target_price == 80000

        # 2. 알림 목록 조회
        list_response = client.get(f"/api/v1/alerts/{telegram_id}")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        # 3. 알림 수정
        update_payload = {"notify_on_disclosure": True}
        update_response = client.put(f"/api/v1/alerts/{telegram_id}/{symbol}", json=update_payload)
        assert update_response.status_code == 200
        assert update_response.json()["notify_on_disclosure"] is True

        # 4. 알림 삭제
        delete_response = client.delete(f"/api/v1/alerts/{telegram_id}/{symbol}")
        assert delete_response.status_code == 200
        assert delete_response.json()["result"] is True

        # 5. 알림 목록 재조회 (삭제 확인)
        final_list_response = client.get(f"/api/v1/alerts/{telegram_id}")
        assert final_list_response.status_code == 200
        assert final_list_response.json() == []

    def test_create_alert_invalid_data(self, client: TestClient):
        """
        - **테스트 대상**: `POST /api/v1/alerts/`
        - **목적**: 유효하지 않은 데이터로 알림 생성을 요청했을 때, 422 Unprocessable Entity 오류를 반환하는지 확인합니다.
        - **시나리오**:
            - `target_price` 필드에 숫자 대신 문자열을 포함하여 API를 호출합니다.
            - 응답 코드가 422인지 확인합니다.
        - **Mock 대상**: 없음
        """
        payload = {
            "telegram_id": 987654321,
            "symbol": "005930",
            "target_price": "invalid_price",  # 잘못된 데이터 타입
            "condition": "gte"
        }
        response = client.post("/api/v1/alerts/", json=payload)
        assert response.status_code == 422

    def test_get_alerts_no_user(self, client: TestClient):
        """
        - **테스트 대상**: `GET /api/v1/alerts/{telegram_id}`
        - **목적**: 존재하지 않는 사용자의 알림 목록을 조회할 때, 빈 리스트를 정상적으로 반환하는지 확인합니다.
        - **시나리오**:
            - 시스템에 등록되지 않은 `telegram_id`로 API를 호출합니다.
            - 200 OK 응답과 함께 빈 리스트가 반환되는지 확인합니다.
        - **Mock 대상**: 없음
        """
        response = client.get("/api/v1/alerts/999999999")
        assert response.status_code == 200
        assert response.json() == []

    def test_update_alert_not_found(self, client: TestClient):
        """
        - **테스트 대상**: `PUT /api/v1/alerts/{telegram_id}/{symbol}`
        - **목적**: 존재하지 않는 알림을 수정하려고 할 때, 404 Not Found 오류를 반환하는지 확인합니다.
        - **시나리오**:
            - 테스트용 사용자를 생성합니다.
            - 해당 사용자가 가지고 있지 않은 `symbol`로 수정 API를 호출합니다.
            - 응답 코드가 404인지 확인합니다.
        - **Mock 대상**: 없음
        """
        telegram_id = 111222333
        # 먼저 사용자를 생성하기 위해 임의의 알림을 하나 생성합니다.
        client.post("/api/v1/alerts/", json={"telegram_id": telegram_id, "symbol": "000020", "target_price": 10000})

        update_payload = {"target_price": 12000}
        response = client.put(f"/api/v1/alerts/{telegram_id}/NONEXISTENT_SYMBOL", json=update_payload)
        assert response.status_code == 404

    def test_delete_alert_not_found(self, client: TestClient):
        """
        - **테스트 대상**: `DELETE /api/v1/alerts/{telegram_id}/{symbol}`
        - **목적**: 존재하지 않는 알림을 삭제하려고 할 때, 404 Not Found 오류를 반환하는지 확인합니다.
        - **시나리오**:
            - 테스트용 사용자를 생성합니다.
            - 해당 사용자가 가지고 있지 않은 `symbol`로 삭제 API를 호출합니다.
            - 응답 코드가 404인지 확인합니다.
        - **Mock 대상**: 없음
        """
        telegram_id = 444555666
        # 먼저 사용자를 생성하기 위해 임의의 알림을 하나 생성합니다.
        client.post("/api/v1/alerts/", json={"telegram_id": telegram_id, "symbol": "000040", "target_price": 20000})

        # API 경로가 잘못되어 있어 수정합니다. `/api/v1` 접두사가 누락되었습니다.
        response = client.delete(f"/api/v1/alerts/{telegram_id}/NONEXISTENT_SYMBOL")
        assert response.status_code == 404