import httpx
from httpx import AsyncClient

# httpx.AsyncClient 인스턴스를 전역으로 관리
# 애플리케이션 시작 시 생성하고 종료 시 닫는 것이 좋음
# 여기서는 간단화를 위해 직접 인스턴스화
# 실제 프로덕션에서는 FastAPI의 lifespan 이벤트를 활용하여 관리하는 것이 권장됨

session = AsyncClient(timeout=10.0) # 기본 타임아웃 설정