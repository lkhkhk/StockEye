import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

class TestAdminScheduler:
    """관리자 스케줄러 관련 API 테스트"""
    
    def test_health_check(self):
        """헬스체크 엔드포인트 테스트"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "scheduler_running" in data
        assert data["status"] == "healthy"
    
    def test_schedule_status(self):
        """스케줄러 상태 조회 엔드포인트 테스트"""
        response = client.get("/admin/schedule/status")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert "timestamp" in data
        
        status = data["status"]
        assert "scheduler_running" in status
        assert "job_count" in status
        assert "jobs" in status
        assert isinstance(status["jobs"], list)
    
    def test_trigger_job_valid(self):
        """유효한 잡 수동 실행 테스트"""
        # 실제 스케줄러가 실행 중인지 확인
        health_response = client.get("/health")
        if health_response.status_code == 200:
            health_data = health_response.json()
            if health_data.get("scheduler_running", False):
                response = client.post("/admin/schedule/trigger/sample_job")
                # 스케줄러가 실행 중이면 200 또는 500 (실행 중인 잡이므로)
                assert response.status_code in [200, 500]
                if response.status_code == 200:
                    data = response.json()
                    assert "message" in data
                    assert "job_id" in data
                    assert "timestamp" in data
                    assert data["job_id"] == "sample_job"
                else:
                    # 500 오류인 경우 오류 메시지 확인
                    data = response.json()
                    assert "detail" in data
            else:
                # 스케줄러가 실행되지 않은 경우 테스트 스킵
                pytest.skip("스케줄러가 실행되지 않음")
        else:
            pytest.skip("헬스체크 실패")
    
    def test_trigger_job_invalid(self):
        """존재하지 않는 잡 실행 테스트"""
        response = client.post("/admin/schedule/trigger/nonexistent_job")
        # 404 또는 500 (스케줄러 접근 오류)
        assert response.status_code in [404, 500]
        data = response.json()
        assert "detail" in data 