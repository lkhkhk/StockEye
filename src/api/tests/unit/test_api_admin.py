import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.orm import Session
from src.api.main import app
from src.common.database.db_connector import get_db
from src.common.models.user import User
from src.common.models.simulated_trade import SimulatedTrade
from src.common.models.prediction_history import PredictionHistory
import os
from src.api.routers.admin import get_current_active_admin_user # Removed get_stock_service
from src.common.models.stock_master import StockMaster # Added this import for spec=StockMaster
from src.common.services.stock_master_service import StockMasterService # Added import for StockMasterService
from src.common.services.disclosure_service import DisclosureService # Added import for DisclosureService
from src.common.services.market_data_service import MarketDataService # Added import for MarketDataService
from src.common.utils.exceptions import DartApiError # Import DartApiError

# 모의 관리자 사용자 픽스처, 테스트 전반에 재사용
@pytest.fixture
def mock_admin_user():
    # MOCK: User 모델 객체
    # User 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    return User(id=1, username="admin", email="admin@test.com", role="admin")

# 모의 DB 세션 픽스처, 재사용 가능
@pytest.fixture
def mock_db_session():
    # MOCK: SQLAlchemy Session 객체
    # SQLAlchemy Session의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    db = MagicMock(spec=Session)
    yield db
    # 테스트 후 의존성 오버라이드를 정리하여 다른 테스트에 영향을 주지 않도록 합니다.
    app.dependency_overrides.clear()

# 모의 주식 서비스 픽스처, 재사용 가능
@pytest.fixture
def mock_stock_service_fixture():
    # MOCK: StockMasterService 객체
    # StockMasterService의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    service = MagicMock(spec=StockMasterService) # Changed spec
    yield service
    # 테스트 후 의존성 오버라이드를 정리하여 다른 테스트에 영향을 주지 않도록 합니다가
    app.dependency_overrides.clear()


@pytest.mark.skip(reason="디버깅용 임시 테스트. 평상시에는 비활성화합니다.")
def test_auth_dependency_override_hang(mock_admin_user):
    """임시 테스트: 인증 의존성 주입만 테스트하여 멈춤 현상 확인"""
    # FastAPI의 의존성 주입을 오버라이드하여 실제 함수 대신 모의 객체를 사용하도록 설정합니다.
    app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user
    client = TestClient(app)
    response = client.get("/api/v1/admin/debug/auth_test")
    assert response.status_code == 200
    assert response.json() == {"username": "admin"}
    app.dependency_overrides.clear()


def test_admin_stats_success(mock_admin_user, mock_db_session):
    """관리자 통계 조회 성공 테스트 (dependency_overrides 사용)"""
    # MOCK: mock_db_session.query
    # mock_db_session.query 호출 시 반환될 MagicMock 객체의 동작을 정의합니다.
    def query_side_effect(model):
        query_mock = MagicMock()
        if model == User:
            query_mock.count.return_value = 5
        elif model == SimulatedTrade:
            query_mock.count.return_value = 25
        elif model == PredictionHistory:
            query_mock.count.return_value = 15
        return query_mock
    mock_db_session.query.side_effect = query_side_effect

    # FastAPI의 의존성 주입을 오버라이드하여 실제 함수 대신 모의 객체를 사용하도록 설정합니다.
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user

    client = TestClient(app)
    response = client.get("/api/v1/admin/admin_stats")

    assert response.status_code == 200
    assert response.json() == {
        "user_count": 5,
        "trade_count": 25,
        "prediction_count": 15
    }
    app.dependency_overrides.clear()


def test_admin_stats_unauthorized():
    """관리자가 아닌 사용자가 통계 조회 시 401 오류 테스트"""
    from fastapi import HTTPException
    # FastAPI의 의존성 주입을 오버라이드하여 HTTPException을 발생시키도록 설정합니다.
    app.dependency_overrides[get_current_active_admin_user] = \
        lambda: (_ for _ in ()).throw(HTTPException(status_code=401, detail="Not authenticated"))

    client = TestClient(app)
    response = client.get("/api/v1/admin/admin_stats")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}

@pytest.mark.timeout(10)
def test_reset_database_success_in_development(mock_db_session):
    """개발 환경에서 DB 초기화 성공 테스트 (dependency_overrides 사용)"""
    # MOCK: os.environ, src.api.main.seed_test_data, src.api.routers.admin.APP_ENV
    # os.environ을 모의하여 APP_ENV를 "development"로 설정합니다.
    # seed_test_data 함수를 모의하여 실제 데이터 시딩을 방지합니다.
    # src.api.routers.admin.APP_ENV를 "development"로 설정합니다.
    with patch.dict(os.environ, {"APP_ENV": "development"}), \
         patch('src.api.main.seed_test_data') as mock_seed_data, \
         patch('src.api.routers.admin.APP_ENV', 'development'):

        # FastAPI dependencies are mocked with `dependency_overrides` for stability
        app.dependency_overrides[get_db] = lambda: mock_db_session

        client = TestClient(app)
        response = client.post("/api/v1/admin/debug/reset-database")

        assert response.status_code == 200
        assert response.json() == {"message": "DB 초기화 및 데이터 시딩이 완료되었습니다."}
        # mock_seed_data (MagicMock)가 mock_db_session 인자로 한 번 호출되었는지 확인합니다.
        mock_seed_data.assert_called_once_with(mock_db_session)
        # mock_db_session.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db_session.commit.assert_called_once()

        app.dependency_overrides.clear()

def test_reset_database_forbidden_in_production():
    """운영 환경에서 DB 초기화 시 403 오류 테스트"""
    # MOCK: os.environ, src.api.routers.admin.APP_ENV
    # os.environ을 모의하여 APP_ENV를 "production"으로 설정합니다.
    # src.api.routers.admin.APP_ENV를 "production"으로 설정합니다.
    with patch.dict(os.environ, {"APP_ENV": "production"}), \
         patch('src.api.routers.admin.APP_ENV', 'production'):
        client = TestClient(app)
        response = client.post("/api/v1/admin/debug/reset-database")
        assert response.status_code == 403
        assert response.json() == {"detail": "이 기능은 개발 환경에서만 사용할 수 있습니다."}

@pytest.mark.asyncio
async def test_update_master_success(mock_admin_user, mock_db_session): # Removed mock_stock_service_fixture
    """종목마스터 갱신 성공 테스트 (dependency_overrides 사용)"""
    # MOCK: StockMasterService instance
    mock_stock_master_service = MagicMock(spec=StockMasterService)
    mock_stock_master_service.update_stock_master.return_value = {"success": True, "updated_count": 10}

    # Both `StockMasterService` and `get_current_active_admin_user` are FastAPI dependencies
    app.dependency_overrides[StockMasterService] = lambda: mock_stock_master_service
    app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user
    app.dependency_overrides[get_db] = lambda: mock_db_session # Ensure get_db is also mocked

    client = TestClient(app)
    response = client.post("/api/v1/admin/update_master")

    assert response.status_code == 200
    assert "종목마스터 갱신 완료" in response.json()["message"]
    assert response.json()["updated_count"] == 10
    assert "timestamp" in response.json()

    mock_stock_master_service.update_stock_master.assert_called_once_with(mock_db_session)

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_price_success(mock_admin_user, mock_db_session):
    """일별시세 갱신 성공 테스트 (dependency_overrides 사용)"""
    # MOCK: MarketDataService instance
    mock_market_data_service = MagicMock(spec=MarketDataService)
    mock_market_data_service.update_daily_prices.return_value = {
        "success": True,
        "updated_count": 80,
        "errors": []
    }
    app.dependency_overrides[MarketDataService] = lambda: mock_market_data_service # Override MarketDataService
    app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user

    client = TestClient(app)
    response = client.post("/api/v1/admin/update_price")

    assert response.status_code == 200
    assert "일별시세 갱신 완료" in response.json()["message"]
    assert response.json()["updated_count"] == 80
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_get_schedule_status_success(mock_admin_user):
    """스케줄러 상태 조회 성공 테스트"""
    # MOCK: httpx.AsyncClient
    # `httpx.AsyncClient`는 외부 라이브러리이므로 `patch`를 사용하여 모의합니다.
    with patch('httpx.AsyncClient') as mock_async_client:
        # MagicMock: HTTP 응답 객체를 모의합니다. 동기적으로 동작합니다.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "running", "jobs": 5}
        # mock_async_client의 비동기 컨텍스트 매니저 진입 시 반환될 객체를 모의합니다.
        mock_client_instance = mock_async_client.return_value.__aenter__.return_value
        # mock_client_instance.get (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다가가
        mock_client_instance.get.return_value = mock_response

        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user

        client = TestClient(app)
        response = client.get("/api/v1/admin/schedule/status")

        assert response.status_code == 200
        assert response.json() == {"status": "running", "jobs": 5}
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_trigger_schedule_job_success(mock_admin_user):
    """스케줄러 잡 실행 성공 테스트"""
    # MOCK: httpx.AsyncClient
    # `httpx.AsyncClient`는 외부 라이브러리이므로 `patch`를 사용하여 모의합니다.
    with patch('httpx.AsyncClient') as mock_async_client:
        # MagicMock: HTTP 응답 객체를 모의합니다. 동기적으로 동작합니다가가
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Job triggered"}
        # mock_async_client의 비동기 컨텍스트 매니저 진입 시 반환될 객체를 모의합니다.
        mock_client_instance = mock_async_client.return_value.__aenter__.return_value
        # mock_client_instance.post (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
        mock_client_instance.post.return_value = mock_response

        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user

        client = TestClient(app)
        response = client.post("/api/v1/admin/schedule/trigger/some_job_id", json={"chat_id": 123})

        assert response.status_code == 200
        assert response.json() == {"message": "Job triggered"}
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_disclosure_all_stocks_success(mock_admin_user, mock_db_session):
    """모든 종목 공시 이력 갱신 성공 테스트"""
    # MOCK: DisclosureService instance
    mock_disclosure_service = MagicMock(spec=DisclosureService)
    mock_disclosure_service.update_disclosures_for_all_stocks.return_value = {
        "success": True,
        "inserted": 400,
        "skipped": 0,
        "errors": []
    }

    app.dependency_overrides[DisclosureService] = lambda: mock_disclosure_service # Override DisclosureService
    app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    client = TestClient(app)
    response = client.post("/api/v1/admin/update_disclosure")

    assert response.status_code == 200
    assert response.json() == {
        "message": "전체 종목 공시 이력 갱신 완료: 400건 추가, 0건 중복",
        "inserted": 400,
        "skipped": 0,
        "errors": []
    }
    mock_disclosure_service.update_disclosures_for_all_stocks.assert_called_once_with(mock_db_session)
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_disclosure_specific_stock_success(mock_admin_user, mock_db_session):
    """특정 종목 공시 이력 갱신 성공 테스트"""
    # MOCK: StockMaster 객체
    # MagicMock: StockMaster 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_stock = MagicMock(corp_code="0012345", symbol="005930", spec=StockMaster)
    mock_stock.name = "삼성전자"

    # MOCK: StockMasterService instance
    mock_stock_master_service = MagicMock(spec=StockMasterService)
    mock_stock_master_service.search_stocks.return_value = [mock_stock]

    # MOCK: DisclosureService instance
    mock_disclosure_service = MagicMock(spec=DisclosureService)
    mock_disclosure_service.update_disclosures.return_value = {
        "success": True,
        "inserted": 3,
        "skipped": 1,
        "errors": []
    }

    # MOCK: dart_get_disclosures
    with patch('src.common.utils.dart_utils.dart_get_disclosures') as mock_dart_get_disclosures:
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "1", "report_nm": "test1"},
            {"rcept_no": "2", "report_nm": "test2"},
            {"rcept_no": "3", "report_nm": "test3"}
        ]

        app.dependency_overrides[StockMasterService] = lambda: mock_stock_master_service
        app.dependency_overrides[DisclosureService] = lambda: mock_disclosure_service
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user
        app.dependency_overrides[get_db] = lambda: mock_db_session

        client = TestClient(app)
        response = client.post("/api/v1/admin/update_disclosure?code_or_name=삼성전자")

        assert response.status_code == 200
        assert response.json() == {
            "message": "'삼성전자' 공시 이력 갱신 완료: 3건 추가, 1건 중복",
            "inserted": 3,
            "skipped": 1,
            "errors": []
        }
        mock_stock_master_service.search_stocks.assert_called_once_with("삼성전자", mock_db_session, limit=1)
        mock_disclosure_service.update_disclosures.assert_called_once_with(
            mock_db_session, corp_code="0012345", stock_code="005930", stock_name="삼성전자"
        )
        app.dependency_overrides.clear()