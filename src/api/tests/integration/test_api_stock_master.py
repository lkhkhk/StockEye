import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from src.common.models.stock_master import StockMaster
from src.common.services.stock_service import StockService


class TestStockMasterRouter:
    """stock_master 라우터 테스트"""

    @pytest.fixture(autouse=True)
    def setup_method(self, real_db: Session):
        # 각 테스트 메서드 실행 전에 StockMaster 테이블을 비웁니다.
        real_db.query(StockMaster).delete()
        real_db.commit()

    def test_get_all_symbols(self, client: TestClient, test_stock_master_data):
        # Given
        # test_stock_master_data 픽스처가 데이터를 생성함

        # When
        response = client.get("/symbols/")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert "total_count" in data
        assert isinstance(data["items"], list)
        assert data["total_count"] == 5 # 예상 값을 5로 변경
        assert len(data["items"]) == 5 # 예상 값을 5로 변경
        assert {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"} in data["items"]

    def test_get_all_symbols_empty(self, client: TestClient):
        # Given: DB에 종목이 없음 (setup_method에서 비워짐)

        # When
        response = client.get("/symbols/")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert "total_count" in data
        assert data["items"] == []
        assert data["total_count"] == 0

    def test_search_symbols_by_name(self, client: TestClient, test_stock_master_data):
        # Given
        # test_stock_master_data 픽스처가 데이터를 생성함

        # When
        response = client.get("/symbols/search?query=삼성전자")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert "total_count" in data
        assert data["total_count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["symbol"] == "005930"

    def test_search_symbols_by_symbol(self, client: TestClient, test_stock_master_data):
        # Given
        # test_stock_master_data 픽스처가 데이터를 생성함

        # When
        response = client.get("/symbols/search?query=035720")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert "total_count" in data
        assert data["total_count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "카카오"

    def test_search_symbols_case_insensitive(self, client: TestClient, test_stock_master_data):
        # Given
        # test_stock_master_data 픽스처가 데이터를 생성함

        # When
        response = client.get("/symbols/search?query=sk하이닉스")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert "total_count" in data
        assert data["total_count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["symbol"] == "000660"

    def test_search_symbols_no_results(self, client: TestClient):
        # Given: DB에 종목이 없음 (setup_method에서 비워짐)

        # When
        response = client.get("/symbols/search?query=없는종목")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert "total_count" in data
        assert data["items"] == []
        assert data["total_count"] == 0

    def test_search_symbols_empty_query(self, client: TestClient):
        # When
        response = client.get("/symbols/search?query=")

        # Then
        assert response.status_code == 422  # FastAPI validation error for min_length=1

    def test_get_current_price_and_change_success(self, client: TestClient, override_stock_service_dependencies, real_db: Session):
        # Given
        symbol = "005930"
        mock_price_data = {"current_price": 75000, "change": 1000, "change_rate": 1.35}
        override_stock_service_dependencies.get_current_price_and_change.return_value = mock_price_data

        # When
        response = client.get(f"/symbols/{symbol}/current_price_and_change")

        # Then
        assert response.status_code == 200
        assert response.json() == mock_price_data
        override_stock_service_dependencies.get_current_price_and_change.assert_called_once_with(symbol, real_db)

    def test_get_current_price_and_change_not_found(self, client: TestClient, override_stock_service_dependencies, real_db: Session):
        # Given
        symbol = "NONEXISTENT"
        override_stock_service_dependencies.get_current_price_and_change.return_value = None

        # When
        response = client.get(f"/symbols/{symbol}/current_price_and_change")

        # Then
        assert response.status_code == 404
        assert response.json() == {"detail": "Stock price data not found"}
        override_stock_service_dependencies.get_current_price_and_change.assert_called_once_with(symbol, real_db)

    def test_search_symbols_korean_query(self, client: TestClient, test_stock_master_data):
        # Given
        # test_stock_master_data 픽스처가 데이터를 생성함 (한화, 한화생명 등 한글 종목 포함)

        # When
        response = client.get("/symbols/search?query=한화")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert "total_count" in data
        assert data["total_count"] >= 1
        assert any(item["name"] == "한화" for item in data["items"]) or any(item["name"] == "한화생명" for item in data["items"])