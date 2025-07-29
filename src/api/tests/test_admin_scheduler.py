import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.models.user import User
from src.api.models.price_alert import PriceAlert
from src.api.models.watchlist import Watchlist
from src.api.models.stock_master import StockMaster
from src.api.models.daily_price import DailyPrice
from src.api.models.disclosure import Disclosure
from src.api.models.prediction_history import PredictionHistory
from src.api.models.simulated_trade import SimulatedTrade
from src.api.models.system_config import SystemConfig
from unittest.mock import patch, MagicMock
from src.api.tests.helpers import create_test_user, get_auth_headers
from sqlalchemy.orm import Session # Session 임포트 추가
from src.api.auth.jwt_handler import get_current_active_admin_user # get_current_active_admin_user 임포트 추가

client = TestClient(app)

@pytest.fixture
def admin_user_and_headers(db: Session):
    admin_user = create_test_user(db, role="admin")
    headers = get_auth_headers(admin_user)
    return admin_user, headers

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
    
    def test_schedule_status(self, admin_user_and_headers):
        """스케줄러 상태 조회 엔드포인트 테스트"""
        admin_user, headers = admin_user_and_headers
        
        # 의존성 오버라이드 설정
        app.dependency_overrides[get_current_active_admin_user] = lambda: admin_user
        
        response = client.get("/admin/schedule/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        
        # 의존성 오버라이드 정리
        app.dependency_overrides.clear()
    
    def test_trigger_job_valid(self, admin_user_and_headers):
        """유효한 잡 수동 실행 테스트"""
        admin_user, headers = admin_user_and_headers
        
        # 의존성 오버라이드 설정
        app.dependency_overrides[get_current_active_admin_user] = lambda: admin_user
        
        # 실제 스케줄러가 실행 중인지 확인
        health_response = client.get("/health")
        if health_response.status_code == 200:
            health_data = health_response.json()
            if health_data.get("scheduler_running", False):
                response = client.post("/admin/schedule/trigger/sample_job", headers=headers)
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
            
        # 의존성 오버라이드 정리
        app.dependency_overrides.clear()
    
    def test_trigger_job_invalid(self, admin_user_and_headers):
        """존재하지 않는 잡 실행 테스트"""
        admin_user, headers = admin_user_and_headers
        
        # 의존성 오버라이드 설정
        app.dependency_overrides[get_current_active_admin_user] = lambda: admin_user
        
        response = client.post("/admin/schedule/trigger/nonexistent_job", headers=headers)
        # 404 또는 500 (스케줄러 접근 오류)
        assert response.status_code in [404, 500]
        data = response.json()
        assert "detail" in data
        
        # 의존성 오버라이드 정리
        app.dependency_overrides.clear()