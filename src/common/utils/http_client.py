import httpx
from httpx import AsyncClient
import os

# API_HOST 환경 변수 로드
API_HOST = os.getenv("API_HOST", "localhost")
API_BASE_URL = f"http://{API_HOST}:8000"

def get_retry_client(auth_token: str = None) -> AsyncClient:
    """
    재시도 로직이 포함된 AsyncClient 인스턴스를 반환합니다.
    5xx 에러나 네트워크 에러 발생 시 최대 3번 재시도합니다.
    선택적으로 인증 토큰을 받아 Authorization 헤더에 포함합니다.
    """
    transport = httpx.AsyncHTTPTransport(retries=3)
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return AsyncClient(base_url=API_BASE_URL, transport=transport, timeout=10.0, headers=headers)