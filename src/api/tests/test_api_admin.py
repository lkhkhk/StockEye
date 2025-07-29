import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.models.user import User
from src.api.models.stock_master import StockMaster
from src.api.auth.jwt_handler import get_current_active_admin_user
from src.api.tests.helpers import create_test_user, get_auth_headers
from unittest.mock import patch, MagicMock
from datetime import datetime
from fastapi import HTTPException # HTTPException 임포트 추가
from src.common.db_connector import get_db # get_db 임포트 추가
from src.api.main import app # app 임포트 추가

@pytest.fixture
def admin_user_and_headers(db: Session):
    admin_user = create_test_user(db, role="admin")
    headers = get_auth_headers(admin_user)
    return admin_user, headers

@pytest.fixture
def normal_user_and_headers(db: Session):
    normal_user = create_test_user(db, role="user")
    headers = get_auth_headers(normal_user)
    return normal_user, headers

class TestAdminRouter:
    def test_admin_stats_as_admin(self, client: TestClient, admin_user_and_headers):
        """관리자로 로그인하여 통계 정보를 조회합니다."""
        admin_user, _ = admin_user_and_headers # We don't need headers here

        # get_current_active_admin_user 의존성을 Mocking된 관리자 사용자로 오버라이드
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user
        
        response = client.get("/admin/admin_stats") # No headers needed
        assert response.status_code == 200
        data = response.json()
        assert "user_count" in data
        assert "trade_count" in data
        assert "prediction_count" in data

        del app.dependency_overrides[get_current_active_admin_user] # 오버라이드 해제

    def test_admin_stats_as_normal_user(self, client: TestClient, normal_user_and_headers):
        """일반 사용자로 통계 정보 조회 시 403 Forbidden 응답을 받는지 테스트합니다."""
        normal_user, headers = normal_user_and_headers
        # 일반 사용자가 관리자 권한이 없으므로 HTTPException을 발생시키도록 오버라이드
        def override_get_current_active_admin_user_normal_user():
            raise HTTPException(status_code=403, detail="Not authorized")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_normal_user
        response = client.get("/admin/admin_stats", headers=headers)
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user] # 오버라이드 해제

    def test_admin_stats_unauthenticated(self, client: TestClient):
        """인증되지 않은 사용자로 통계 정보 조회 시 403 Forbidden 응답을 받는지 테스트합니다."""
        def override_get_current_active_admin_user_unauthenticated():
            raise HTTPException(status_code=403, detail="Not authenticated")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_unauthenticated
        response = client.get("/admin/admin_stats")
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user] # 오버라이드 해제

    @patch('src.api.routers.admin.StockService.update_stock_master')
    def test_update_master_success_as_admin(self, mock_update_stock_master, client: TestClient, admin_user_and_headers):
        """관리자로 종목마스터 갱신 성공 테스트"""
        admin_user, _ = admin_user_and_headers
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user

        mock_update_stock_master.return_value = {"success": True, "updated_count": 100}
        response = client.post("/admin/update_master")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "종목마스터 갱신 완료"
        assert data["updated_count"] == 100
        mock_update_stock_master.assert_called_once()

        del app.dependency_overrides[get_current_active_admin_user]

    @patch('src.api.routers.admin.StockService.update_stock_master')
    def test_update_master_failure_as_admin(self, mock_update_stock_master, client: TestClient, admin_user_and_headers):
        """관리자로 종목마스터 갱신 실패 테스트"""
        admin_user, _ = admin_user_and_headers
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user

        mock_update_stock_master.side_effect = Exception("DB connection error")
        response = client.post("/admin/update_master")
        assert response.status_code == 500
        assert "서버 오류" in response.json()["detail"]
        mock_update_stock_master.assert_called_once()

        del app.dependency_overrides[get_current_active_admin_user]

    def test_update_master_as_normal_user(self, client: TestClient, normal_user_and_headers):
        """일반 사용자로 종목마스터 갱신 시 403 Forbidden 응답 테스트"""
        normal_user, headers = normal_user_and_headers
        def override_get_current_active_admin_user_normal_user():
            raise HTTPException(status_code=403, detail="Not authorized")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_normal_user
        response = client.post("/admin/update_master", headers=headers)
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user]

    def test_update_master_unauthenticated(self, client: TestClient):
        """인증되지 않은 사용자로 종목마스터 갱신 시 403 Forbidden 응답 테스트"""
        def override_get_current_active_admin_user_unauthenticated():
            raise HTTPException(status_code=403, detail="Not authenticated")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_unauthenticated
        response = client.post("/admin/update_master")
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user]

    @patch('src.api.routers.admin.StockService.update_daily_prices')
    def test_update_price_success_as_admin(self, mock_update_daily_prices, client: TestClient, admin_user_and_headers):
        """관리자로 일별시세 갱신 성공 테스트"""
        admin_user, _ = admin_user_and_headers
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user

        mock_update_daily_prices.return_value = {"success": True, "updated_count": 500, "errors": []}
        response = client.post("/admin/update_price")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "일별시세 갱신 완료: 500개 데이터 처리. 오류: 0개 종목"
        assert data["updated_count"] == 500
        assert data["error_stocks"] == []
        mock_update_daily_prices.assert_called_once()

        del app.dependency_overrides[get_current_active_admin_user]

    @patch('src.api.routers.admin.StockService.update_daily_prices')
    def test_update_price_failure_as_admin(self, mock_update_daily_prices, client: TestClient, admin_user_and_headers):
        """관리자로 일별시세 갱신 실패 테스트"""
        admin_user, _ = admin_user_and_headers
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user

        mock_update_daily_prices.side_effect = Exception("API call failed")
        response = client.post("/admin/update_price")
        assert response.status_code == 500
        assert "서버 오류" in response.json()["detail"]
        mock_update_daily_prices.assert_called_once()

        del app.dependency_overrides[get_current_active_admin_user]

    def test_update_price_as_normal_user(self, client: TestClient, normal_user_and_headers):
        """일반 사용자로 일별시세 갱신 시 403 Forbidden 응답 테스트"""
        normal_user, headers = normal_user_and_headers
        def override_get_current_active_admin_user_normal_user():
            raise HTTPException(status_code=403, detail="Not authorized")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_normal_user
        response = client.post("/admin/update_price", headers=headers)
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user]

    def test_update_price_unauthenticated(self, client: TestClient):
        """인증되지 않은 사용자로 일별시세 갱신 시 403 Forbidden 응답 테스트"""
        def override_get_current_active_admin_user_unauthenticated():
            raise HTTPException(status_code=403, detail="Not authenticated")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_unauthenticated
        response = client.post("/admin/update_price")
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user]

    @patch('src.api.routers.admin.StockService.update_disclosures')
    def test_update_disclosure_all_success_as_admin(self, mock_update_disclosures, client: TestClient, admin_user_and_headers, db: Session):
        """관리자로 전체 종목 공시 갱신 성공 테스트"""
        admin_user, _ = admin_user_and_headers
        
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user

        mock_stock1 = MagicMock(symbol="005930", name="삼성전자", corp_code="0012345")
        mock_stock2 = MagicMock(symbol="035720", name="카카오", corp_code="0067890")

        def mock_get_db():
            mock_db_session = MagicMock(spec=Session)
            mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_stock1, mock_stock2]
            yield mock_db_session

        app.dependency_overrides[get_db] = mock_get_db

        mock_update_disclosures.side_effect = [
            {"success": True, "inserted": 5, "skipped": 2, "errors": []},
            {"success": True, "inserted": 3, "skipped": 1, "errors": []}
        ]
        response = client.post("/admin/update_disclosure")
        assert response.status_code == 200
        data = response.json()
        assert data["message"].startswith("전체 종목 공시 이력 갱신 완료")
        assert data["inserted"] == 8
        assert data["skipped"] == 3
        assert data["errors"] == []
        assert mock_update_disclosures.call_count == 2
        
        # Clean up the override
        del app.dependency_overrides[get_current_active_admin_user]
        del app.dependency_overrides[get_db]

    @patch('src.api.routers.admin.StockService.update_disclosures')
    def test_update_disclosure_single_by_symbol_success_as_admin(self, mock_update_disclosures, client: TestClient, admin_user_and_headers, db: Session):
        """관리자로 단일 종목 공시 갱신 (종목코드) 성공 테스트"""
        admin_user, _ = admin_user_and_headers
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user

        mock_stock = MagicMock(spec=StockMaster)
        mock_stock.symbol = "005930"
        mock_stock.name = "삼성전자"
        mock_stock.corp_code = "0012345"

        def mock_get_db():
            mock_db_session = MagicMock(spec=Session)
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_stock
            yield mock_db_session

        app.dependency_overrides[get_db] = mock_get_db

        mock_update_disclosures.return_value = {"success": True, "inserted": 10, "skipped": 3, "errors": []}
        response = client.post("/admin/update_disclosure", params={"code_or_name": "005930"})
        assert response.status_code == 200
        data = response.json()
        assert data["message"].startswith("공시 이력 갱신 완료")
        assert data["inserted"] == 10
        assert data["skipped"] == 3
        from unittest.mock import ANY
        mock_update_disclosures.assert_called_once_with(ANY, corp_code="0012345", stock_code="005930", stock_name="삼성전자")

        del app.dependency_overrides[get_db]
        del app.dependency_overrides[get_current_active_admin_user]

    @patch('src.api.routers.admin.StockService.update_disclosures')
    def test_update_disclosure_single_by_name_success_as_admin(self, mock_update_disclosures, client: TestClient, admin_user_and_headers, db: Session):
        """관리자로 단일 종목 공시 갱신 (종목명) 성공 테스트"""
        admin_user, _ = admin_user_and_headers
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user

        mock_stock = MagicMock(spec=StockMaster)
        mock_stock.symbol = "035720"
        mock_stock.name = "카카오"
        mock_stock.corp_code = "0067890"

        def mock_get_db():
            mock_db_session = MagicMock(spec=Session)
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_stock
            yield mock_db_session

        app.dependency_overrides[get_db] = mock_get_db

        mock_update_disclosures.return_value = {"success": True, "inserted": 7, "skipped": 1, "errors": []}
        response = client.post("/admin/update_disclosure", params={"code_or_name": "카카오"})
        assert response.status_code == 200
        data = response.json()
        assert data["message"].startswith("공시 이력 갱신 완료")
        assert data["inserted"] == 7
        assert data["skipped"] == 1
        from unittest.mock import ANY
        mock_update_disclosures.assert_called_once_with(ANY, corp_code="0067890", stock_code="035720", stock_name="카카오")

        del app.dependency_overrides[get_db]
        del app.dependency_overrides[get_current_active_admin_user]

    @patch('src.api.routers.admin.StockService.update_disclosures')
    def test_update_disclosure_single_by_corp_code_success_as_admin(self, mock_update_disclosures, client: TestClient, admin_user_and_headers, db: Session):
        """관리자로 단일 종목 공시 갱신 (고유번호) 성공 테스트"""
        admin_user, headers = admin_user_and_headers
        app.dependency_overrides[get_current_active_admin_user] = lambda: admin_user

        mock_stock = MagicMock(spec=StockMaster)
        mock_stock.symbol = "000660"
        mock_stock.name = "SK하이닉스"
        mock_stock.corp_code = "0013456"

        def mock_get_db():
            mock_db_session = MagicMock(spec=Session)
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_stock
            yield mock_db_session

        app.dependency_overrides[get_db] = mock_get_db

        mock_update_disclosures.return_value = {"success": True, "inserted": 12, "skipped": 0, "errors": []}
        response = client.post("/admin/update_disclosure", params={"code_or_name": "0013456"}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["message"].startswith("공시 이력 갱신 완료")
        assert data["inserted"] == 12
        assert data["skipped"] == 0
        from unittest.mock import ANY
        mock_update_disclosures.assert_called_once_with(ANY, corp_code="0013456", stock_code="000660", stock_name="SK하이닉스")

        del app.dependency_overrides[get_db]
        del app.dependency_overrides[get_current_active_admin_user]

    def test_update_disclosure_not_found_as_admin(self, client: TestClient, admin_user_and_headers, db: Session):
        """관리자로 존재하지 않는 종목 공시 갱신 시 404 Not Found 응답 테스트"""
        admin_user, headers = admin_user_and_headers
        app.dependency_overrides[get_current_active_admin_user] = lambda: admin_user

        def mock_get_db():
            mock_db_session = MagicMock(spec=Session)
            mock_db_session.query.return_value.filter.return_value.first.return_value = None # No stock found
            yield mock_db_session

        app.dependency_overrides[get_db] = mock_get_db

        response = client.post("/admin/update_disclosure", params={"code_or_name": "NONEXIST"}, headers=headers)
        assert response.status_code == 404
        assert "해당 입력에 대한 corp_code(고유번호)를 찾을 수 없습니다." in response.json()["detail"]

        del app.dependency_overrides[get_db]
        del app.dependency_overrides[get_current_active_admin_user]

    @patch('src.api.routers.admin.StockService.update_disclosures')
    def test_update_disclosure_failure_as_admin(self, mock_update_disclosures, client: TestClient, admin_user_and_headers, db: Session):
        """관리자로 공시 갱신 실패 테스트"""
        admin_user, headers = admin_user_and_headers
        app.dependency_overrides[get_current_active_admin_user] = lambda: admin_user

        mock_stock = MagicMock(spec=StockMaster)
        mock_stock.symbol = "005930"
        mock_stock.name = "삼성전자"
        mock_stock.corp_code = "0012345"

        def mock_get_db():
            mock_db_session = MagicMock(spec=Session)
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_stock
            yield mock_db_session

        app.dependency_overrides[get_db] = mock_get_db

        mock_update_disclosures.side_effect = Exception("DART API error")

        response = client.post("/admin/update_disclosure", params={"code_or_name": "005930"}, headers=headers)

        assert response.status_code == 500
        assert "서버 오류" in response.json()["detail"]
        from unittest.mock import ANY
        mock_update_disclosures.assert_called_once_with(ANY, corp_code='0012345', stock_code='005930', stock_name='삼성전자')

        del app.dependency_overrides[get_db]
        del app.dependency_overrides[get_current_active_admin_user]
    
    def test_update_disclosure_as_normal_user(self, client: TestClient, normal_user_and_headers):
        """일반 사용자로 공시 갱신 시 403 Forbidden 응답 테스트"""
        normal_user, headers = normal_user_and_headers
        def override_get_current_active_admin_user_normal_user():
            raise HTTPException(status_code=403, detail="Not authorized")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_normal_user
        response = client.post("/admin/update_disclosure", headers=headers)
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user]

    def test_update_disclosure_unauthenticated(self, client: TestClient):
        """인증되지 않은 사용자로 공시 갱신 시 403 Forbidden 응답 테스트"""
        def override_get_current_active_admin_user_unauthenticated():
            raise HTTPException(status_code=403, detail="Not authenticated")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_unauthenticated
        response = client.post("/admin/update_disclosure")
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user]

    @patch('src.api.main.app.state.scheduler') # main.py에서 scheduler를 직접 import하므로 이렇게 패치
    def test_get_schedule_status_success_as_admin(self, mock_scheduler, client: TestClient, admin_user_and_headers):
        """관리자로 스케줄러 상태 조회 성공 테스트"""
        admin_user, headers = admin_user_and_headers

        # get_current_active_admin_user 의존성을 Mocking된 관리자 사용자로 오버라이드
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user

        mock_job1 = MagicMock(id="job1", name="Job One", trigger="interval[0:01:00]", next_run_time=datetime.now())
        mock_job2 = MagicMock(id="job2", name="Job Two", trigger="cron[hour='10']", next_run_time=datetime.now())
        mock_scheduler.running = True
        mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]

        response = client.get("/admin/schedule/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is True
        assert len(data["jobs"]) == 2
        assert data["jobs"][0]["id"] == "job1"
        assert data["jobs"][1]["id"] == "job2"
        mock_scheduler.get_jobs.assert_called_once()

    @patch('src.api.main.app.state.scheduler')
    def test_get_schedule_status_not_running_as_admin(self, mock_scheduler, client: TestClient, admin_user_and_headers):
        """관리자로 스케줄러가 실행 중이 아닐 때 상태 조회 테스트"""
        admin_user, headers = admin_user_and_headers

        # get_current_active_admin_user 의존성을 Mocking된 관리자 사용자로 오버라이드
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user

        mock_scheduler.running = False
        mock_scheduler.get_jobs.return_value = [] # 실행 중이 아니면 잡이 없음
        response = client.get("/admin/schedule/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is False
        assert len(data["jobs"]) == 0
        mock_scheduler.get_jobs.assert_not_called() # 스케줄러가 실행 중이 아니면 get_jobs는 호출되지 않음

    def test_get_schedule_status_as_normal_user(self, client: TestClient, normal_user_and_headers):
        """일반 사용자로 스케줄러 상태 조회 시 403 Forbidden 응답 테스트"""
        normal_user, headers = normal_user_and_headers
        def override_get_current_active_admin_user_normal_user():
            raise HTTPException(status_code=403, detail="Not authorized")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_normal_user
        response = client.get("/admin/schedule/status", headers=headers)
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user]

    def test_get_schedule_status_unauthenticated(self, client: TestClient):
        """인증되지 않은 사용자로 잡 실행 시 403 Forbidden 응답 테스트"""
        def override_get_current_active_admin_user_unauthenticated():
            raise HTTPException(status_code=403, detail="Not authenticated")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_unauthenticated
        response = client.get("/admin/schedule/status")
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user]

    @patch('src.api.main.app.state.scheduler')
    def test_trigger_job_not_found_as_admin(self, mock_scheduler, client: TestClient, admin_user_and_headers):
        """관리자로 존재하지 않는 잡 실행 시 404 Not Found 응답 테스트"""
        admin_user, headers = admin_user_and_headers

        # get_current_active_admin_user 의존성을 Mocking된 관리자 사용자로 오버라이드
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user

        mock_scheduler.get_job.return_value = None
        response = client.post("/admin/schedule/trigger/nonexistent_job", headers=headers)
        assert response.status_code == 404 # Changed from 500 to 404
        assert "잡을 찾을 수 없습니다: nonexistent_job" in response.json()["detail"]
        mock_scheduler.get_job.assert_called_once_with("nonexistent_job")
    
    @patch('src.api.auth.jwt_handler.get_current_active_admin_user')
    @patch('src.api.main.app.state.scheduler')
    def test_trigger_job_failure_as_admin(self, mock_scheduler, mock_get_current_active_admin_user, client: TestClient, admin_user_and_headers):
        """관리자로 잡 실행 중 오류 발생 시 500 Internal Server Error 응답 테스트"""
        admin_user, headers = admin_user_and_headers
        mock_get_current_active_admin_user.return_value = admin_user

        # Mock job object
        mock_job = MagicMock(id="test_job", args=(), kwargs={})
        mock_job.func.side_effect = Exception("Job execution failed")  # 예외 발생 설정
        mock_scheduler.get_job.return_value = mock_job  # get_job이 mock_job 반환

        # WHEN
        response = client.post("/admin/schedule/trigger/test_job", headers=headers)

        # THEN
        assert response.status_code == 500  # 500 상태 코드 확인
        assert "잡 실행 실패" in response.json()["detail"]  # 에러 메시지 확인
        mock_scheduler.get_job.assert_called_once_with("test_job")  # get_job 호출 확인
        mock_job.func.assert_called_once()  # 잡 실행 확인

    def test_trigger_job_as_normal_user(self, client: TestClient, normal_user_and_headers):
        """일반 사용자로 잡 실행 시 403 Forbidden 응답 테스트"""
        normal_user, headers = normal_user_and_headers
        def override_get_current_active_admin_user_normal_user():
            raise HTTPException(status_code=403, detail="Not authorized")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_normal_user
        response = client.post("/admin/schedule/trigger/test_job", headers=headers)
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user]

    def test_trigger_job_unauthenticated(self, client: TestClient):
        """인증되지 않은 사용자로 잡 실행 시 403 Forbidden 응답 테스트"""
        def override_get_current_active_admin_user_unauthenticated():
            raise HTTPException(status_code=403, detail="Not authenticated")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_unauthenticated
        response = client.post("/admin/schedule/trigger/test_job")
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user]

    @patch('src.api.routers.admin.StockService.check_and_notify_new_disclosures')
    def test_trigger_check_disclosures_success_as_admin(self, mock_check_and_notify, client: TestClient, admin_user_and_headers):
        """관리자로 공시 확인 잡 수동 실행 성공 테스트"""
        admin_user, headers = admin_user_and_headers

        # get_current_active_admin_user 의존성을 Mocking된 관리자 사용자로 오버라이드
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user

        mock_check_and_notify.return_value = None # This function doesn't return anything specific
        response = client.post("/admin/trigger/check_disclosures", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "공시 확인 잡이 성공적으로 실행되었습니다."
        mock_check_and_notify.assert_called_once()

    @patch('src.api.auth.jwt_handler.get_current_active_admin_user')
    @patch('src.api.routers.admin.StockService.check_and_notify_new_disclosures')
    def test_trigger_check_disclosures_failure_as_admin(self, mock_check_and_notify, mock_get_current_active_admin_user, client: TestClient, admin_user_and_headers):
        """관리자로 공시 확인 잡 실행 중 오류 발생 시 500 Internal Server Error 응답 테스트"""
        admin_user, headers = admin_user_and_headers
        mock_get_current_active_admin_user.return_value = admin_user

        # get_current_active_admin_user 의존성을 Mocking된 관리자 사용자로 오버라이드
        def override_get_current_active_admin_user():
            return admin_user

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user

        mock_check_and_notify.side_effect = Exception("Disclosure check failed")
        response = client.post("/admin/trigger/check_disclosures", headers=headers)
        assert response.status_code == 500 # Changed from 200 to 500
        assert "Disclosure check failed" in response.json()["detail"]
        mock_check_and_notify.assert_called_once()

    def test_trigger_check_disclosures_as_normal_user(self, client: TestClient, normal_user_and_headers):
        """일반 사용자로 공시 확인 잡 실행 시 403 Forbidden 응답 테스트"""
        normal_user, headers = normal_user_and_headers
        def override_get_current_active_admin_user_normal_user():
            raise HTTPException(status_code=403, detail="Not authorized")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_normal_user
        response = client.post("/admin/trigger/check_disclosures", headers=headers)
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user]

    def test_trigger_check_disclosures_unauthenticated(self, client: TestClient):
        """인증되지 않은 사용자로 공시 확인 잡 실행 시 403 Forbidden 응답 테스트"""
        def override_get_current_active_admin_user_unauthenticated():
            raise HTTPException(status_code=403, detail="Not authenticated")

        app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user_unauthenticated
        response = client.post("/admin/trigger/check_disclosures")
        assert response.status_code == 403
        del app.dependency_overrides[get_current_active_admin_user]
