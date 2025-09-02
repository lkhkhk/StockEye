import pytest
import httpx
import os
import asyncio

# --- Constants ---
API_HOST = os.getenv("API_HOST", "stockeye-api")
API_URL = f"http://{API_HOST}:8000/api/v1"

@pytest.fixture(scope="module", autouse=True)
async def setup_e2e_environment():
    """E2E 테스트 모듈 시작 시 DB를 초기화하고 환경 변수를 설정합니다."""
    print("\n--- E2E 테스트 환경 설정 시작 ---")
    # 1. DB 초기화 및 시딩
    async with httpx.AsyncClient() as client:
        try:
            print("DB 초기화 및 데이터 시딩을 요청합니다...")
            response = await client.post(f"{API_URL}/admin/debug/reset-database", timeout=20)
            response.raise_for_status()
            print(f"DB 초기화 완료: {response.json()}")
        except httpx.RequestError as e:
            pytest.fail(f"API 서버 연결 실패: {e}. 테스트를 진행할 수 없습니다.")

    # 2. 환경 변수 설정
    os.environ["API_HOST"] = API_HOST # Ensure API_HOST is set for the test run
    
    yield
    
    # 3. 테스트 종료 후 정리
    del os.environ["API_HOST"]
    print("\n--- E2E 테스트 환경 설정 종료 ---")

@pytest.mark.asyncio
async def test_httpx_response_attributes():
    """
    Minimal test to check httpx.Response attributes directly.
    """
    print("\n[E2E Debug] Running test_httpx_response_attributes")
    
    # Debug httpx.Response class itself
    print(f"[E2E Debug] httpx.Response class __dict__: {httpx.Response.__dict__}")
    try:
        print(f"[E2E Debug] httpx.Response class __slots__: {httpx.Response.__slots__}")
    except AttributeError as e:
        print(f"[E2E Debug] httpx.Response class __slots__ access failed: {e}")

    try:
        async with httpx.AsyncClient(base_url=API_URL, timeout=10.0) as client:
            response = await client.post("/predict", json={"symbol": "005930", "telegram_id": 99999})
            
            print(f"[E2E Debug] Type of response: {type(response).__name__}")
            print(f"[E2E Debug] Response object: {response}")
            print(f"[E2E Debug] Has 'is_success' attribute: {hasattr(response, 'is_success')}")
            print(f"[E2E Debug] dir(response): {dir(response)}")

            assert response.status_code == 200
            assert hasattr(response, 'is_success') # This is the key assertion
            assert response.is_success
            data = response.json()
            assert "prediction" in data
            print("[E2E Debug] httpx.Response attributes checked successfully.")

    except Exception as e:
        pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")

