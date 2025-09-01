# src/api/tests/integration/test_api_stock_master_integration.py
"""
API 통합 테스트: 종목 정보 API

이 파일은 `/symbols/` 엔드포인트 그룹에 대한 통합 테스트를 포함합니다.
DB에 저장된 종목 마스터 정보를 조회하고 검색하는 기능을 검증합니다.

- `/symbols/`: 페이지네이션을 통해 전체 종목 목록을 조회합니다.
- `/symbols/search`: 주어진 검색어(종목명 또는 코드)로 종목을 검색합니다.
- `/symbols/{symbol}/current_price_and_change`: 특정 종목의 현재가 및 등락 정보를 조회합니다.

대부분의 테스트는 `real_db`와 `test_stock_master_data` fixture를 통해 실제 DB와 상호작용하며,
외부 API 호출이 필요한 현재가 조회 기능은 서비스 계층을 모의(Mock)하여 테스트합니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.common.models.stock_master import StockMaster


class TestStockMasterRouter:
    """
    `/symbols` 라우터에 대한 통합 테스트 클래스.
    """

    @pytest.fixture(autouse=True)
    def setup_method(self, real_db: Session):
        """
        각 테스트 실행 전, `stock_master` 테이블을 초기화하는 Fixture.

        - **목적**: 테스트 간의 독립성을 보장하기 위해, 매 테스트 시작 전에
                  모든 종목 마스터 데이터를 삭제합니다.
        - **적용**: `autouse=True`로 설정되어 이 클래스의 모든 테스트 메서드에 자동으로 적용됩니다.
        """
        real_db.query(StockMaster).delete()
        real_db.commit()

    def test_get_all_symbols(self, client: TestClient, test_stock_master_data):
        """
        - **테스트 대상**: `GET /symbols/`
        - **목적**: 전체 종목 목록을 정상적으로 조회하는지 확인합니다.
        - **시나리오**:
            1. `test_stock_master_data` fixture를 통해 DB에 5개의 종목을 생성합니다.
            2. 전체 목록 조회 API를 호출합니다.
            3. 200 OK 응답과 함께, 5개의 종목 정보가 포함된 목록이 반환되는지 확인합니다.
        - **Mock 대상**: 없음 (DB 직접 사용)
        """
        # When
        response = client.get("/symbols/")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 5
        assert len(data["items"]) == 5
        assert {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"} in data["items"]

    def test_get_all_symbols_empty(self, client: TestClient):
        """
        - **테스트 대상**: `GET /symbols/`
        - **목적**: DB에 종목 정보가 없을 때, 빈 목록을 정상적으로 반환하는지 확인합니다.
        - **시나리오**:
            1. `setup_method` fixture가 DB를 비웁니다.
            2. 전체 목록 조회 API를 호출합니다.
            3. 200 OK 응답과 함께, `total_count`가 0인 빈 목록이 반환되는지 확인합니다.
        - **Mock 대상**: 없음
        """
        # When
        response = client.get("/symbols/")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    def test_search_symbols_by_name(self, client: TestClient, test_stock_master_data):
        """
        - **테스트 대상**: `GET /symbols/search`
        - **목적**: 종목명으로 종목을 검색하는 기능이 정상적으로 동작하는지 확인합니다.
        - **시나리오**:
            1. `test_stock_master_data` fixture로 테스트 데이터를 준비합니다.
            2. `query` 파라미터에 "삼성전자"를 넣어 검색 API를 호출합니다.
            3. 200 OK 응답과 함께, 삼성전자 종목 정보 1건이 반환되는지 확인합니다.
        - **Mock 대상**: 없음
        """
        # When
        response = client.get("/symbols/search?query=삼성전자")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["symbol"] == "005930"

    def test_search_symbols_by_symbol(self, client: TestClient, test_stock_master_data):
        """
        - **테스트 대상**: `GET /symbols/search`
        - **목적**: 종목 코드로 종목을 검색하는 기능이 정상적으로 동작하는지 확인합니다.
        - **시나리오**:
            1. `test_stock_master_data` fixture로 테스트 데이터를 준비합니다.
            2. `query` 파라미터에 "035720"(카카오)를 넣어 검색 API를 호출합니다.
            3. 200 OK 응답과 함께, 카카오 종목 정보 1건이 반환되는지 확인합니다.
        - **Mock 대상**: 없음
        """
        # When
        response = client.get("/symbols/search?query=035720")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["name"] == "카카오"

    def test_search_symbols_no_results(self, client: TestClient):
        """
        - **테스트 대상**: `GET /symbols/search`
        - **목적**: 검색 결과가 없을 때, 빈 목록을 정상적으로 반환하는지 확인합니다.
        - **시나리오**:
            1. DB에 없는 검색어로 API를 호출합니다.
            2. 200 OK 응답과 함께 빈 목록이 반환되는지 확인합니다.
        - **Mock 대상**: 없음
        """
        # When
        response = client.get("/symbols/search?query=없는종목")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    def test_search_symbols_empty_query(self, client: TestClient):
        """
        - **테스트 대상**: `GET /symbols/search`
        - **목적**: 검색어를 비워둔 채 요청 시, 422 Unprocessable Entity 에러를 반환하는지 확인합니다.
        - **시나리오**:
            1. `query` 파라미터를 빈 문자열로 하여 API를 호출합니다.
            2. FastAPI의 유효성 검사에 의해 422 에러가 발생하는지 확인합니다.
        - **Mock 대상**: 없음
        """
        # When
        response = client.get("/symbols/search?query=")

        # Then
        assert response.status_code == 422

    def test_get_current_price_and_change_success(self, client: TestClient, override_stock_service_dependencies, real_db: Session):
        """
        - **테스트 대상**: `GET /symbols/{symbol}/current_price_and_change`
        - **목적**: 특정 종목의 현재가 및 등락 정보를 성공적으로 조회하는지 확인합니다.
        - **시나리오**:
            1. `StockService`의 `get_current_price_and_change` 메서드를 모의(Mock) 처리합니다.
            2. API를 호출합니다.
            3. 200 OK 응답과 함께, 모의 처리된 가격 정보가 반환되는지 확인합니다.
        - **Mock 대상**: `StockService.get_current_price_and_change` (의존성 주입 오버라이드)
        """
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
        """
        - **테스트 대상**: `GET /symbols/{symbol}/current_price_and_change`
        - **목적**: 가격 정보가 없는 종목에 대해 404 에러를 정상적으로 반환하는지 확인합니다.
        - **시나리오**:
            1. `StockService`의 `get_current_price_and_change`가 `None`을 반환하도록 모의 처리합니다.
            2. API를 호출합니다.
            3. 404 Not Found 응답을 확인합니다.
        - **Mock 대상**: `StockService.get_current_price_and_change` (의존성 주입 오버라이드)
        """
        # Given
        symbol = "NONEXISTENT"
        override_stock_service_dependencies.get_current_price_and_change.return_value = None

        # When
        response = client.get(f"/symbols/{symbol}/current_price_and_change")

        # Then
        assert response.status_code == 404
        assert response.json() == {"detail": "Stock price data not found"}