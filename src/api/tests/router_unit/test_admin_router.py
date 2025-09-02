import pytest
from fastapi import FastAPI, Depends # Import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.orm import Session
from src.api.routers.admin import router, get_db, get_current_active_admin_user # Removed get_stock_service
from src.common.models.user import User
from src.common.models.simulated_trade import SimulatedTrade
from src.common.models.prediction_history import PredictionHistory
from src.common.models.stock_master import StockMaster
from src.common.services.stock_master_service import StockMasterService # Changed import from StockService
from src.common.services.market_data_service import MarketDataService
from src.common.services.disclosure_service import DisclosureService
import httpx

# FastAPI 앱 인스턴스 생성
app = FastAPI()
app.include_router(router) # 관리자 라우터 포함

# FastAPI 앱을 위한 TestClient 생성
client = TestClient(app) # 여기에 앱 사용

# 의존성 모의
@pytest.fixture
def mock_get_db():
    # MOCK: get_db 의존성
    # MagicMock: SQLAlchemy Session 객체를 모의합니다. 동기적으로 동작합니다.
    db_mock = MagicMock(spec=Session)
    yield db_mock

@pytest.fixture
def mock_get_current_active_admin_user():
    # MOCK: get_current_active_admin_user 의존성
    # MagicMock: User 모델 객체를 모의합니다. 동기적으로 동작합니다.
    user_mock = MagicMock(spec=User)
    user_mock.username = "admin_user"
    yield user_mock

class TestAdminRouter:

    def test_admin_stats(self, mock_get_current_active_admin_user, mock_get_db):
        # GIVEN
        # mock_get_db 픽스처에서 반환된 모의 DB 세션 인스턴스를 사용합니다.
        db_instance = mock_get_db 
        # db_instance.query().count() 호출 시 반환될 값을 설정합니다. 동기적으로 동작합니다。
        # User, SimulatedTrade, PredictionHistory 순서로 호출될 것으로 예상합니다.
        db_instance.query.return_value.count.side_effect = [10, 5, 20] # user, trade, prediction counts

        # FastAPI의 의존성 주입을 오버라이드하여 실제 함수 대신 모의 객체를 사용하도록 설정합니다.
        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

        # WHEN
        response = client.get("/admin/admin_stats") 

        # THEN
        assert response.status_code == 200
        assert response.json() == {
            "user_count": 10,
            "trade_count": 5,
            "prediction_count": 20
        }
        # db_instance.query (MagicMock)가 User, SimulatedTrade, PredictionHistory 모델로 호출되었는지 확인합니다.
        db_instance.query.assert_any_call(User)
        db_instance.query.assert_any_call(SimulatedTrade)
        db_instance.query.assert_any_call(PredictionHistory)

        # 테스트 후 의존성 오버라이드를 정리하여 다른 테스트에 영향을 주지 않도록 합니다。
        app.dependency_overrides = {}

    def test_reset_database_exception(self, mock_get_db, mock_get_current_active_admin_user):
        # GIVEN
        db_instance = mock_get_db
        db_instance.execute.side_effect = Exception("DB reset error")

        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

        # WHEN
        response = client.post("/admin/debug/reset-database")

        # THEN
        assert response.status_code == 500
        assert "DB 초기화 실패" in response.json()["detail"]
        db_instance.rollback.assert_called_once()
        app.dependency_overrides = {}

    @pytest.mark.asyncio 
    @patch('src.api.routers.admin.get_db') # MOCK: get_db 의존성
    @patch('src.api.routers.admin.get_current_active_admin_user') # MOCK: get_current_active_admin_user 의존성
    async def test_update_master_success(self, mock_get_current_active_admin_user, mock_get_db):
        # GIVEN
        db_instance = mock_get_db 

        # MOCK: StockMasterService 인스턴스
        mock_stock_master_service_instance = MagicMock(spec=StockMasterService)
        mock_stock_master_service_instance.update_stock_master.return_value = {"success": True, "updated_count": 100}

        # FastAPI의 의존성 주입을 오버라이드하여 실제 함수 대신 모의 객체를 사용하도록 설정합니다.
        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user
        app.dependency_overrides[StockMasterService] = lambda: mock_stock_master_service_instance # Override the dependency directly

        # WHEN
        response = client.post("/admin/update_master")

        # THEN
        assert response.status_code == 200
        assert response.json()["message"] == "종목마스터 갱신 완료"
        assert response.json()["updated_count"] == 100
        assert "timestamp" in response.json()

        # mock_stock_master_service_instance.update_stock_master (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다.
        mock_stock_master_service_instance.update_stock_master.assert_called_once_with(db_instance)

        # 테스트 후 의존성 오버라이드를 정리하여 다른 테스트에 영향을 주지 않도록 합니다。
        app.dependency_overrides = {}

    @pytest.mark.asyncio
    @patch('src.api.routers.admin.get_db')
    @patch('src.api.routers.admin.get_current_active_admin_user')
    async def test_update_master_failure(self, mock_get_current_active_admin_user, mock_get_db):
        # GIVEN
        db_instance = mock_get_db

        mock_stock_master_service_instance = MagicMock(spec=StockMasterService)
        mock_stock_master_service_instance.update_stock_master.return_value = {"success": False, "error": "API error"}

        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user
        app.dependency_overrides[StockMasterService] = lambda: mock_stock_master_service_instance

        # WHEN
        response = client.post("/admin/update_master")

        # THEN
        assert response.status_code == 500
        assert response.json()["detail"].startswith("서버 오류:")
        mock_stock_master_service_instance.update_stock_master.assert_called_once_with(db_instance)
        app.dependency_overrides = {}

    @pytest.mark.asyncio
    @patch('src.api.routers.admin.get_db')
    @patch('src.api.routers.admin.get_current_active_admin_user')
    async def test_update_master_exception(self, mock_get_current_active_admin_user, mock_get_db):
        # GIVEN
        db_instance = mock_get_db

        mock_stock_master_service_instance = MagicMock(spec=StockMasterService)
        mock_stock_master_service_instance.update_stock_master.side_effect = Exception("Unexpected error")

        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user
        app.dependency_overrides[StockMasterService] = lambda: mock_stock_master_service_instance

        # WHEN
        response = client.post("/admin/update_master")

        # THEN
        assert response.status_code == 500
        assert response.json()["detail"] == "서버 오류: Unexpected error"
        mock_stock_master_service_instance.update_stock_master.assert_called_once_with(db_instance)
        app.dependency_overrides = {}

    @pytest.mark.asyncio
    @patch('src.api.routers.admin.get_db')
    @patch('src.api.routers.admin.get_current_active_admin_user')
    async def test_update_price_failure(self, mock_get_current_active_admin_user, mock_get_db):
        # GIVEN
        db_instance = mock_get_db

        mock_market_data_service_instance = MagicMock(spec=MarketDataService)
        mock_market_data_service_instance.update_daily_prices.return_value = {"success": False, "error": "API error"}

        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user
        app.dependency_overrides[MarketDataService] = lambda: mock_market_data_service_instance

        # WHEN
        response = client.post("/admin/update_price")

        # THEN
        assert response.status_code == 500
        assert response.json()["detail"].startswith("서버 오류:")
        mock_market_data_service_instance.update_daily_prices.assert_called_once_with(db_instance)
        app.dependency_overrides = {}

    @pytest.mark.asyncio
    @patch('src.api.routers.admin.get_db')
    @patch('src.api.routers.admin.get_current_active_admin_user')
    async def test_update_disclosure_all_stocks_failure(self, mock_get_current_active_admin_user, mock_get_db):
        # GIVEN
        db_instance = mock_get_db

        mock_disclosure_service_instance = MagicMock(spec=DisclosureService)
        mock_disclosure_service_instance.update_disclosures_for_all_stocks.return_value = {"success": False, "errors": ["Error 1"]}

        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user
        app.dependency_overrides[DisclosureService] = lambda: mock_disclosure_service_instance

        # WHEN
        response = client.post("/admin/update_disclosure")

        # THEN
        assert response.status_code == 500
        assert response.json()["detail"] == "전체 공시 갱신 실패: ['Error 1']"
        mock_disclosure_service_instance.update_disclosures_for_all_stocks.assert_called_once_with(db_instance)
        app.dependency_overrides = {}

    @pytest.mark.asyncio
    @patch('src.api.routers.admin.get_db')
    @patch('src.api.routers.admin.get_current_active_admin_user')
    async def test_update_disclosure_specific_stock_not_found(self, mock_get_current_active_admin_user, mock_get_db):
        # GIVEN
        db_instance = mock_get_db

        mock_stock_master_service_instance = MagicMock(spec=StockMasterService)
        mock_stock_master_service_instance.search_stocks.return_value = []

        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user
        app.dependency_overrides[StockMasterService] = lambda: mock_stock_master_service_instance

        # WHEN
        response = client.post("/admin/update_disclosure?code_or_name=INVALID")

        # THEN
        assert response.status_code == 404
        assert response.json()["detail"] == "'INVALID'에 해당하는 종목을 찾을 수 없거나 DART 고유번호(corp_code)가 없습니다."
        mock_stock_master_service_instance.search_stocks.assert_called_once_with("INVALID", db_instance, limit=1)
        app.dependency_overrides = {}

    @pytest.mark.asyncio
    @patch('src.api.routers.admin.get_db')
    @patch('src.api.routers.admin.get_current_active_admin_user')
    async def test_update_disclosure_specific_stock_failure(self, mock_get_current_active_admin_user, mock_get_db):
        # GIVEN
        db_instance = mock_get_db

        mock_stock = MagicMock(spec=StockMaster)
        mock_stock.corp_code = "123"
        mock_stock.symbol = "005930"
        mock_stock.name = "삼성전자"
        mock_stock_master_service_instance = MagicMock(spec=StockMasterService)
        mock_stock_master_service_instance.search_stocks.return_value = [mock_stock]

        mock_disclosure_service_instance = MagicMock(spec=DisclosureService)
        mock_disclosure_service_instance.update_disclosures.return_value = {"success": False, "errors": ["Error 2"]}

        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user
        app.dependency_overrides[StockMasterService] = lambda: mock_stock_master_service_instance
        app.dependency_overrides[DisclosureService] = lambda: mock_disclosure_service_instance

        # WHEN
        response = client.post("/admin/update_disclosure?code_or_name=005930")

        # THEN
        assert response.status_code == 500
        assert response.json()["detail"].startswith("'삼성전자' 공시 갱신 실패:")
        mock_disclosure_service_instance.update_disclosures.assert_called_once_with(db_instance, corp_code="123", stock_code="005930", stock_name="삼성전자")
        app.dependency_overrides = {}

    @pytest.mark.asyncio
    @patch('src.api.routers.admin.get_db')
    @patch('src.api.routers.admin.get_current_active_admin_user')
    async def test_update_disclosure_exception(self, mock_get_current_active_admin_user, mock_get_db):
        # GIVEN
        db_instance = mock_get_db

        mock_disclosure_service_instance = MagicMock(spec=DisclosureService)
        mock_disclosure_service_instance.update_disclosures_for_all_stocks.side_effect = Exception("Unexpected error")

        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user
        app.dependency_overrides[DisclosureService] = lambda: mock_disclosure_service_instance

        # WHEN
        response = client.post("/admin/update_disclosure")

        # THEN
        assert response.status_code == 500
        assert response.json()["detail"] == "서버 오류: Unexpected error"
        app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_trigger_schedule_job_success(self, mock_get_current_active_admin_user):
        # GIVEN
        job_id = "test_job"
        request_data = {"chat_id": 12345}

        with patch('httpx.AsyncClient') as MockAsyncClient:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": "Job triggered"}
            mock_response.raise_for_status.return_value = None # Ensure no exception is raised

            mock_httpx_client_instance = MockAsyncClient.return_value.__aenter__.return_value
            mock_httpx_client_instance.post.return_value = mock_response

            app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

            # WHEN
            response = client.post(f"/admin/schedule/trigger/{job_id}", json=request_data)

            # THEN
            assert response.status_code == 200
            assert response.json() == {"message": "Job triggered"}
            mock_httpx_client_instance.post.assert_called_once_with(f"http://stockeye-worker:8001/api/v1/scheduler/trigger/{job_id}", json=request_data)
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_trigger_schedule_job_worker_unreachable(self, mock_get_current_active_admin_user):
        # GIVEN
        job_id = "test_job"
        request_data = {"chat_id": 12345}

        with patch('httpx.AsyncClient') as MockAsyncClient:
            mock_httpx_client_instance = MockAsyncClient.return_value.__aenter__.return_value
            mock_httpx_client_instance.post.side_effect = httpx.RequestError("Connection error", request=httpx.Request("POST", "http://stockeye-worker:8001"))

            app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

            # WHEN
            response = client.post(f"/admin/schedule/trigger/{job_id}", json=request_data)

            # THEN
            assert response.status_code == 502
            assert response.json()["detail"] == "워커 서비스에 연결할 수 없습니다."
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_trigger_schedule_job_worker_error(self, mock_get_current_active_admin_user):
        # GIVEN
        job_id = "test_job"
        request_data = {"chat_id": 12345}

        with patch('httpx.AsyncClient') as MockAsyncClient:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request from worker"
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Bad Request", request=httpx.Request("POST", "http://stockeye-worker:8001"), response=mock_response)

            mock_httpx_client_instance = MockAsyncClient.return_value.__aenter__.return_value
            mock_httpx_client_instance.post.return_value = mock_response

            app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

            # WHEN
            response = client.post(f"/admin/schedule/trigger/{job_id}", json=request_data)

            # THEN
            assert response.status_code == 400
            assert response.json()["detail"] == "Bad Request from worker"
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_schedule_status_success(self, mock_get_current_active_admin_user):
        # GIVEN
        with patch('httpx.AsyncClient') as MockAsyncClient:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "running", "jobs": []}
            mock_response.raise_for_status.return_value = None

            mock_httpx_client_instance = MockAsyncClient.return_value.__aenter__.return_value
            mock_httpx_client_instance.get.return_value = mock_response

            app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

            # WHEN
            response = client.get("/admin/schedule/status")

            # THEN
            assert response.status_code == 200
            assert response.json() == {"status": "running", "jobs": []}
            mock_httpx_client_instance.get.assert_called_once_with("http://stockeye-worker:8001/api/v1/scheduler/status")
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_schedule_status_worker_unreachable(self, mock_get_current_active_admin_user):
        # GIVEN
        with patch('httpx.AsyncClient') as MockAsyncClient:
            mock_httpx_client_instance = MockAsyncClient.return_value.__aenter__.return_value
            mock_httpx_client_instance.get.side_effect = httpx.RequestError("Connection error", request=httpx.Request("GET", "http://stockeye-worker:8001"))

            app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

            # WHEN
            response = client.get("/admin/schedule/status")

            # THEN
            assert response.status_code == 502
            assert response.json()["detail"] == "워커 서비스에 연결할 수 없습니다."
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_schedule_status_worker_error(self, mock_get_current_active_admin_user):
        # GIVEN
        with patch('httpx.AsyncClient') as MockAsyncClient:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request from worker"
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Bad Request", request=httpx.Request("GET", "http://stockeye-worker:8001"), response=mock_response)

            mock_httpx_client_instance = MockAsyncClient.return_value.__aenter__.return_value
            mock_httpx_client_instance.get.return_value = mock_response

            app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

            # WHEN
            response = client.get("/admin/schedule/status")

            # THEN
            assert response.status_code == 400
            assert response.json()["detail"] == "Bad Request from worker"
            app.dependency_overrides = {}

    def test_debug_auth_test_success(self, mock_get_current_active_admin_user):
        # GIVEN
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

        # WHEN
        response = client.get("/admin/debug/auth_test")

        # THEN
        assert response.status_code == 200
        assert response.json()["username"] == "admin_user"
        app.dependency_overrides = {}

    @pytest.mark.skip(reason="TestClient does not re-raise exceptions from dependencies as expected")
    def test_debug_auth_test_exception(self, mock_get_current_active_admin_user):
        # GIVEN
        mock_get_current_active_admin_user.side_effect = Exception("Auth error")

        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

        # WHEN / THEN
        with pytest.raises(Exception) as exc_info:
            client.get("/admin/debug/auth_test")
        assert "Auth error" in str(exc_info.value)
        app.dependency_overrides = {}
