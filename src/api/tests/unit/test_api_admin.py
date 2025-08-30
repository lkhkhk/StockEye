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
from src.api.routers.admin import get_current_active_admin_user, get_stock_service
from src.common.models.stock_master import StockMaster # Added this import for spec=StockMaster

# Fixture for a mock admin user, reused across tests
@pytest.fixture
def mock_admin_user():
    return User(id=1, username="admin", email="admin@test.com", role="admin")

# Fixture for a mock DB session, can be reused
@pytest.fixture
def mock_db_session():
    db = MagicMock(spec=Session)
    yield db
    app.dependency_overrides.clear()

# Fixture for a mock stock service, can be reused
@pytest.fixture
def mock_stock_service_fixture():
    service = MagicMock()
    yield service
    app.dependency_overrides.clear()


@pytest.mark.skip(reason="디버깅용 임시 테스트. 평상시에는 비활성화합니다.")
def test_auth_dependency_override_hang(mock_admin_user):
    """임시 테스트: 인증 의존성 주입만 테스트하여 멈춤 현상 확인"""
    app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user
    client = TestClient(app)
    response = client.get("/api/v1/admin/debug/auth_test")
    assert response.status_code == 200
    assert response.json() == {"username": "admin"}
    app.dependency_overrides.clear()


def test_admin_stats_success(mock_admin_user, mock_db_session):
    """관리자 통계 조회 성공 테스트 (dependency_overrides 사용)"""
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
    app.dependency_overrides[get_current_active_admin_user] = \
        lambda: (_ for _ in ()).throw(HTTPException(status_code=401, detail="Not authenticated"))

    client = TestClient(app)
    response = client.get("/api/v1/admin/admin_stats")
    assert response.status_code == 401
    app.dependency_overrides.clear()

@pytest.mark.timeout(10)
def test_reset_database_success_in_development(mock_db_session):
    """개발 환경에서 DB 초기화 성공 테스트 (dependency_overrides 사용)"""
    # Non-dependency patches are still needed and are kept as `patch`
    with patch.dict(os.environ, {"APP_ENV": "development"}), \
         patch('src.api.main.seed_test_data') as mock_seed_data, \
         patch('src.api.routers.admin.APP_ENV', 'development'):

        # FastAPI dependencies are mocked with `dependency_overrides` for stability
        app.dependency_overrides[get_db] = lambda: mock_db_session

        client = TestClient(app)
        response = client.post("/api/v1/admin/debug/reset-database")

        assert response.status_code == 200
        assert response.json() == {"message": "DB 초기화 및 데이터 시딩이 완료되었습니다."}
        mock_seed_data.assert_called_once_with(mock_db_session)
        mock_db_session.commit.assert_called_once()

        app.dependency_overrides.clear()

def test_reset_database_forbidden_in_production():
    """운영 환경에서 DB 초기화 시 403 오류 테스트"""
    # This test does not involve FastAPI dependencies, so `patch` is appropriate
    with patch.dict(os.environ, {"APP_ENV": "production"}), \
         patch('src.api.routers.admin.APP_ENV', 'production'):
        client = TestClient(app)
        response = client.post("/api/v1/admin/debug/reset-database")
        assert response.status_code == 403
        assert response.json() == {"detail": "이 기능은 개발 환경에서만 사용할 수 있습니다."}

@pytest.mark.asyncio
async def test_update_master_success(mock_admin_user, mock_stock_service_fixture):
    """종목마스터 갱신 성공 테스트 (dependency_overrides 사용)"""
    mock_stock_service_fixture.update_stock_master = AsyncMock(return_value={
        "success": True,
        "updated_count": 10
    })

    # Both `get_stock_service` and `get_current_active_admin_user` are FastAPI dependencies
    app.dependency_overrides[get_stock_service] = lambda: mock_stock_service_fixture
    app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user

    client = TestClient(app)
    response = client.post("/api/v1/admin/update_master")

    assert response.status_code == 200
    assert "종목마스터 갱신 완료" in response.json()["message"]
    assert response.json()["updated_count"] == 10
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_price_success(mock_admin_user, mock_stock_service_fixture):
    """일별시세 갱신 성공 테스트 (dependency_overrides 사용)"""
    mock_stock_service_fixture.update_daily_prices = AsyncMock(return_value={
        "success": True,
        "updated_count": 100,
        "errors": []
    })
    app.dependency_overrides[get_stock_service] = lambda: mock_stock_service_fixture
    app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user

    client = TestClient(app)
    response = client.post("/api/v1/admin/update_price")

    assert response.status_code == 200
    assert "일별시세 갱신 완료" in response.json()["message"]
    assert response.json()["updated_count"] == 100
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_get_schedule_status_success(mock_admin_user):
    """스케줄러 상태 조회 성공 테스트"""
    # `httpx.AsyncClient` is an external library, not a FastAPI dependency, so `patch` is correct here
    with patch('httpx.AsyncClient') as mock_async_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "running", "jobs": 5}
        mock_client_instance = mock_async_client.return_value.__aenter__.return_value
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
    # `httpx.AsyncClient` is an external library, not a FastAPI dependency, so `patch` is correct here
    with patch('httpx.AsyncClient') as mock_async_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Job triggered"}
        mock_client_instance = mock_async_client.return_value.__aenter__.return_value
        mock_client_instance.post.return_value = mock_response

        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user

        client = TestClient(app)
        response = client.post("/api/v1/admin/schedule/trigger/some_job_id", json={"chat_id": 123})

        assert response.status_code == 200
        assert response.json() == {"message": "Job triggered"}
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_disclosure_all_stocks_success(mock_admin_user, mock_stock_service_fixture, mock_db_session):
    """모든 종목 공시 이력 갱신 성공 테스트"""
    mock_stock_service_fixture.update_disclosures_for_all_stocks = AsyncMock(return_value={
        "success": True,
        "inserted": 5,
        "skipped": 2,
        "errors": []
    })

    app.dependency_overrides[get_stock_service] = lambda: mock_stock_service_fixture
    app.dependency_overrides[get_current_active_admin_user] = lambda: mock_admin_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    client = TestClient(app)
    response = client.post("/api/v1/admin/update_disclosure")

    assert response.status_code == 200
    assert response.json() == {
        "message": "전체 종목 공시 이력 갱신 완료: 5건 추가, 2건 중복",
        "inserted": 5,
        "skipped": 2,
        "errors": []
    }
    mock_stock_service_fixture.update_disclosures_for_all_stocks.assert_called_once_with(mock_db_session)
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_disclosure_specific_stock_success(mock_admin_user, mock_stock_service_fixture, mock_db_session):
    """특정 종목 공시 이력 갱신 성공 테스트"""
    mock_stock = MagicMock(corp_code="0012345", symbol="005930", spec=StockMaster)
    mock_stock.name = "삼성전자"
    mock_stock_service_fixture.search_stocks.return_value = [mock_stock]
    mock_stock_service_fixture.update_disclosures = AsyncMock(return_value={
        "success": True,
        "inserted": 3,
        "skipped": 1,
        "errors": []
    })

    app.dependency_overrides[get_stock_service] = lambda: mock_stock_service_fixture
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
    mock_stock_service_fixture.search_stocks.assert_called_once_with("삼성전자", mock_db_session, limit=1)
    mock_stock_service_fixture.update_disclosures.assert_called_once_with(
        mock_db_session, corp_code="0012345", stock_code="005930", stock_name="삼성전자"
    )
    app.dependency_overrides.clear()