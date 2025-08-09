
import pytest
from fastapi.testclient import TestClient
import asyncio

# Mark the test as a pytest-asyncio test
@pytest.mark.asyncio
async def test_create_price_alert_successfully(client: TestClient, real_db):
    """
    인증된 사용자가 가격 알림을 성공적으로 생성하는지 테스트합니다.
    (TestClient와 real_db fixture 사용)
    """
    # 1. 사용자 등록 및 로그인 (TestClient 사용)
    # real_db fixture가 테스트 전에 DB를 초기화하므로 사용자 이름은 충돌하지 않음
    register_data = {"username": "testuser_alert_create", "password": "testpassword", "email": "testuser_alert_create@example.com"}
    response = client.post("/api/v1/users/register", json=register_data)
    assert response.status_code == 200, f"사용자 등록 실패: {response.text}"

    login_data = {"username": "testuser_alert_create", "password": "testpassword"}
    response = client.post("/api/v1/users/login", json=login_data)
    assert response.status_code == 200, f"로그인 실패: {response.text}"
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 알림 생성 API 호출
    alert_data = {
        "symbol": "005930",
        "target_price": 80000,
        "condition": "gte",
    }
    response = client.post("/api/v1/alerts", json=alert_data, headers=headers)
    
    # 3. 결과 검증
    assert response.status_code == 200, f"알림 생성 실패: {response.text}"
    response_data = response.json()
    assert response_data["symbol"] == alert_data["symbol"]
    assert response_data["target_price"] == alert_data["target_price"]
    assert response_data["user_id"] is not None

