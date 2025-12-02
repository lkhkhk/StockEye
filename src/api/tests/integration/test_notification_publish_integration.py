# src/api/tests/integration/test_notification_publish_integration.py
"""
API 통합 테스트: 일반 사용자 알림 생성

이 파일은 일반적인 웹/앱 사용자의 알림 생성 흐름에 대한 통합 테스트를 포함합니다.
텔레그램 ID 기반이 아닌, 사용자 이름과 비밀번호로 가입하고 로그인하여 얻은
JWT 토큰을 사용하여 인증하는 시나리오를 검증합니다.

**주요 검증 시나리오**:
1. 사용자 가입 (`/api/v1/users/register`)
2. 로그인 및 토큰 발급 (`/api/v1/users/login`)
3. 발급된 토큰을 이용한 알림 생성 (`/api/v1/alerts`)
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_create_price_alert_successfully(client: TestClient, real_db):
    """
    - **테스트 대상**: `POST /api/v1/alerts` (JWT 토큰 인증)
    - **목적**: 가입-로그인-알림 생성으로 이어지는 일반 사용자의 핵심 흐름이 정상적으로 동작하는지 확인합니다.
    - **시나리오**:
        1. `TestClient`를 사용하여 테스트용 사용자를 가입시킵니다.
        2. 동일 사용자로 로그인하여 `access_token`을 발급받습니다.
        3. 발급받은 토큰을 인증 헤더에 담아 가격 알림 생성을 요청합니다.
        4. 200 OK 응답과 함께, 생성된 알림 정보가 올바르게 반환되는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # --- 1. 사용자 가입 및 로그인 --- #
    # Given: 테스트용 사용자 정보
    register_data = {"username": "testuser_alert_create", "password": "testpassword", "email": "testuser_alert_create@example.com"}
    
    # When: 가입 요청
    register_response = client.post("/api/v1/users/register", json=register_data)
    assert register_response.status_code == 200, f"사용자 등록 실패: {register_response.text}"

    # When: 로그인 요청
    login_data = {"username": "testuser_alert_create", "password": "testpassword"}
    login_response = client.post("/api/v1/users/login", json=login_data) # login은 JSON body를 사용
    assert login_response.status_code == 200, f"로그인 실패: {login_response.text}"
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # --- 2. 알림 생성 --- #
    # Given: 생성할 알림 정보
    alert_data = {
        "symbol": "005930",
        "target_price": 80000,
        "condition": "gte",
    }

    # When: 알림 생성 API 호출
    alert_response = client.post("/api/v1/price-alerts/", json=alert_data, headers=headers)

    # --- 3. 결과 검증 --- #
    # Then: 알림 생성 결과 확인
    assert alert_response.status_code == 201, f"알림 생성 실패: {alert_response.text}"
    response_data = alert_response.json()
    assert response_data["symbol"] == alert_data["symbol"]
    assert response_data["target_price"] == alert_data["target_price"]
    assert "user_id" in response_data