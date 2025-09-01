# src/api/tests/integration/test_admin_scheduler_integration.py
"""
**API 통합 테스트: 관리자 스케줄러 (현재 대부분 비활성화)**

**중요**: 이 파일의 테스트는 대부분 주석 처리되어 있습니다.
스케줄러 관련 기능이 `stockeye-api` 서비스에서 `stockeye-worker` 서비스로 이전되었기 때문입니다.
현재 이 파일에 남아있는 테스트는 `stockeye-api`의 기본적인 상태를 확인하는 헬스체크뿐입니다.

향후 `worker` 서비스와의 API 연동을 통해 스케줄러를 제어하는 기능이 추가된다면,
이 파일은 해당 API 연동을 테스트하는 내용으로 업데이트될 수 있습니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from src.api.main import app
from src.api.auth.jwt_handler import get_current_active_admin_user
from src.api.tests.helpers import create_test_user, get_auth_headers

# TestClient 인스턴스 생성. FastAPI 애플리케이션에 직접 요청을 보냅니다.
client = TestClient(app)

@pytest.fixture
def admin_user_and_headers(real_db: Session):
    """
    테스트를 위한 관리자 사용자 생성 및 인증 헤더를 제공합니다.

    - **목적**: 관리자 권한이 필요한 API를 테스트하기 위해 사전에 관리자 계정과 JWT 토큰을 생성합니다.
    - **반환**: 생성된 User 모델 객체와 HTTP 요청에 사용될 인증 헤더(딕셔너리)를 튜플로 반환합니다.
    """
    admin_user = create_test_user(real_db, role="admin")
    headers = get_auth_headers(admin_user)
    return admin_user, headers

class TestAdminScheduler:
    """
    관리자 스케줄러 관련 API 엔드포인트 통합 테스트 클래스.
    (현재는 헬스체크 테스트만 포함)
    """

    def test_health_check(self):
        """
        - **테스트 대상**: `GET /health`
        - **목적**: `stockeye-api` 서비스가 정상적으로 실행 중이며, 기본적인 응답을 반환하는지 확인합니다.
        - **시나리오**:
            - `/health` 엔드포인트에 GET 요청을 보냅니다.
            - 응답 상태 코드가 200인지 확인합니다.
            - 응답 본문에 `status` 필드가 'healthy' 값으로 포함되어 있는지 확인합니다.
        - **Mock 대상**: 없음
        """
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"

    # --- 이하 주석 처리된 테스트 ---
    # 아래 주석 처리된 테스트들은 스케줄러 기능이 worker 서비스로 분리되면서
    # 현재는 사용되지 않거나, worker 서비스의 API를 호출하도록 수정되어야 합니다.
    # 기존 코드를 참고용으로 남겨둡니다.

    # def test_schedule_status(self, admin_user_and_headers):
    #     """스케줄러 상태 조회 엔드포인트 테스트"""
    #     admin_user, headers = admin_user_and_headers
    #
    #     # get_current_active_admin_user 의존성을 Mocking된 관리자 사용자로 오버라이드
    #     app.dependency_overrides[get_current_active_admin_user] = lambda: admin_user
    #
    #     response = client.get("/admin/schedule/status", headers=headers)
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert "running" in data
    #     assert "jobs" in data
    #     assert isinstance(data["jobs"], list)
    #
    #     # 의존성 오버라이드 정리
    #     app.dependency_overrides.clear()

    # def test_trigger_job_valid(self, admin_user_and_headers):
    #     """유효한 잡 수동 실행 테스트"""
    #     admin_user, headers = admin_user_and_headers
    #
    #     # 의존성 오버라이드 설정
    #     app.dependency_overrides[get_current_active_admin_user] = lambda: admin_user
    #
    #     # 스케줄러 Mocking
    #     mock_scheduler = MagicMock()
    #     mock_job = MagicMock(id="sample_job", args=(), kwargs={})
    #     mock_scheduler.get_job.return_value = mock_job
    #
    #     # app.state.scheduler를 Mocking
    #     with patch('src.api.main.app.state.scheduler', new=mock_scheduler):
    #         response = client.post("/admin/schedule/trigger/sample_job", headers=headers)
    #         assert response.status_code == 200
    #         data = response.json()
    #         assert "message" in data
    #         assert "job_id" in data
    #         assert "timestamp" in data
    #         assert data["job_id"] == "sample_job"
    #         mock_scheduler.get_job.assert_called_once_with("sample_job")
    #         mock_job.func.assert_called_once() # 잡 함수가 호출되었는지 확인
    #
    #     # 의존성 오버라이드 정리
    #     app.dependency_overrides.clear()

    # def test_trigger_job_invalid(self, admin_user_and_headers):
    #     """존재하지 않는 잡 실행 테스트"""
    #     admin_user, headers = admin_user_and_headers
    #
    #     # 의존성 오버라이드 설정
    #     app.dependency_overrides[get_current_active_admin_user] = lambda: admin_user
    #
    #     # 스케줄러 Mocking
    #     mock_scheduler = MagicMock()
    #     mock_scheduler.get_job.return_value = None # 잡이 없음을 모의
    #
    #     with patch('src.api.main.app.state.scheduler', new=mock_scheduler):
    #         response = client.post("/admin/schedule/trigger/nonexistent_job", headers=headers)
    #         assert response.status_code == 404 # 404 Not Found 예상
    #         data = response.json()
    #         assert "detail" in data
    #         assert data["detail"] == "잡을 찾을 수 없습니다: nonexistent_job"
    #         mock_scheduler.get_job.assert_called_once_with("nonexistent_job")
    #
    #     # 의존성 오버라이드 정리
    #     app.dependency_overrides.clear()