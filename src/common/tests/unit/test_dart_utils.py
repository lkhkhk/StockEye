# 이 파일은 src.common.utils.dart_utils 모듈의 단위 테스트를 포함합니다.
#
# DART API와의 실제 네트워크 통신을 방지하기 위해, 모든 테스트는
# httpx 클라이언트(`get_retry_client`)를 모의(mock)하여 진행합니다.
# 이를 통해 네트워크 불안정성이나 API 키 없이도 순수 로직(데이터 파싱 등)의
# 정확성을 검증할 수 있습니다.

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os
import httpx
import zipfile
import io
from src.common.utils.dart_utils import dart_get_all_stocks, dart_get_disclosures
from src.common.utils.exceptions import DartApiError

@pytest.fixture(autouse=True)
def mock_env_vars():
    # DART_API_KEY 환경 변수를 모의하여, 실제 키 없이 테스트를 실행합니다.
    with patch.dict(os.environ, {"DART_API_KEY": "test_api_key"}):
        yield

@pytest.fixture
def mock_get_retry_client():
    # get_retry_client 함수를 모의하여 실제 HTTP 요청을 보내지 않도록 합니다.
    # AsyncMock을 사용하여 비동기 컨텍스트 매니저를 흉내 냅니다.
    with patch('src.common.utils.dart_utils.get_retry_client') as mock_client:
        async_mock_client = AsyncMock()
        mock_get = AsyncMock()
        async_mock_client.__aenter__.return_value = mock_get
        mock_client.return_value = async_mock_client
        yield mock_get

class TestDartUtils:
    @pytest.mark.asyncio
    async def test_dart_get_all_stocks_success(self, mock_get_retry_client):
        # 모의 zip 파일 콘텐츠 생성
        mock_zip_content = io.BytesIO()
        with zipfile.ZipFile(mock_zip_content, 'w') as zf:
            xml_data = """
            <result>
                <list>
                    <corp_code>00123456</corp_code>
                    <corp_name>삼성전자</corp_name>
                    <stock_code>005930</stock_code>
                </list>
                <list>
                    <corp_code>00678901</corp_code>
                    <corp_name>카카오</corp_name>
                    <stock_code>035720</stock_code>
                </list>
                <list>
                    <corp_code>00987654</corp_code>
                    <corp_name>비상장회사</corp_name>
                    <stock_code></stock_code>
                </list>
            </result>
            """
            zf.writestr('CORPCODE.xml', xml_data)
        mock_zip_content.seek(0)

        mock_response = MagicMock()
        mock_response.content = mock_zip_content.read()
        mock_response.raise_for_status = MagicMock()
        mock_get_retry_client.get.return_value = mock_response

        stocks = await dart_get_all_stocks()

        assert len(stocks) == 2
        assert stocks[0]["symbol"] == "005930"
        assert stocks[0]["name"] == "삼성전자"
        assert stocks[1]["symbol"] == "035720"
        assert stocks[1]["name"] == "카카오"
        mock_get_retry_client.get.assert_called_once_with("https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key=test_api_key", timeout=60)

    @pytest.mark.asyncio
    async def test_dart_get_all_stocks_api_key_missing(self):
        with patch.dict(os.environ, {"DART_API_KEY": ""}):
            with pytest.raises(ValueError, match="DART_API_KEY가 환경변수에 없거나 인자로 전달되지 않았습니다."):
                await dart_get_all_stocks()

    @pytest.mark.asyncio
    async def test_dart_get_all_stocks_request_error(self, mock_get_retry_client):
        mock_get_retry_client.get.side_effect = httpx.RequestError("Network error", request=httpx.Request("GET", "http://test.com"))
        with pytest.raises(DartApiError, match="DART API 요청 실패"):
            await dart_get_all_stocks()

    @pytest.mark.asyncio
    async def test_dart_get_all_stocks_zip_file_missing_xml(self, mock_get_retry_client):
        mock_zip_content = io.BytesIO()
        with zipfile.ZipFile(mock_zip_content, 'w') as zf:
            zf.writestr('other.xml', '<data/>')
        mock_zip_content.seek(0)

        mock_response = MagicMock()
        mock_response.content = mock_zip_content.read()
        mock_response.raise_for_status = MagicMock()
        mock_get_retry_client.get.return_value = mock_response

        with pytest.raises(RuntimeError, match="ZIP 파일 내에 CORPCODE.xml이 없습니다."):
            await dart_get_all_stocks()

    @pytest.mark.asyncio
    async def test_dart_get_disclosures_success(self, mock_get_retry_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "000",
            "message": "정상",
            "list": [
                {"corp_name": "삼성전자", "report_nm": "사업보고서", "rcept_no": "12345", "rcept_dt": "20230101"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get_retry_client.get.return_value = mock_response

        disclosures = await dart_get_disclosures()

        assert len(disclosures) == 1
        assert disclosures[0]["corp_name"] == "삼성전자"
        mock_get_retry_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_dart_get_disclosures_api_key_missing(self):
        with patch.dict(os.environ, {"DART_API_KEY": ""}):
            with pytest.raises(ValueError, match="DART_API_KEY가 환경변수에 없거나 인자로 전달되지 않았습니다."):
                await dart_get_disclosures()

    @pytest.mark.asyncio
    async def test_dart_get_disclosures_request_error(self, mock_get_retry_client):
        mock_get_retry_client.get.side_effect = httpx.RequestError("Network error", request=httpx.Request("GET", "http://test.com"))
        with pytest.raises(DartApiError, match="DART API 요청 실패"):
            await dart_get_disclosures()

    @pytest.mark.asyncio
    async def test_dart_get_disclosures_api_error_status(self, mock_get_retry_client):
        """DART API가 정상 응답했으나, status 필드가 에러(e.g., '013')인 경우를 테스트합니다."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "013",
            "message": "조회된 데이터가 없습니다."
        }
        mock_response.raise_for_status = MagicMock()
        mock_get_retry_client.get.return_value = mock_response

        with pytest.raises(DartApiError, match="조회된 데이터가 없습니다.") as excinfo:
            await dart_get_disclosures()
        assert excinfo.value.status_code == "013"

    @pytest.mark.asyncio
    async def test_dart_get_disclosures_pagination(self, mock_get_retry_client):
        """여러 페이지에 걸친 공시 정보를 모두 가져오는지 페이지네이션 로직을 테스트합니다."""
        # 1페이지 응답 모의
        mock_response_page1 = MagicMock()
        mock_response_page1.json.return_value = {
            "status": "000",
            "message": "정상",
            "page_no": 1,
            "total_page": 2,
            "total_count": 2,
            "page_count": 1,
            "list": [{"corp_name": "회사1", "rcept_no": "1"}]
        }
        mock_response_page1.raise_for_status = MagicMock()

        # 2페이지 응답 모의
        mock_response_page2 = MagicMock()
        mock_response_page2.json.return_value = {
            "status": "000",
            "message": "정상",
            "page_no": 2,
            "total_page": 2,
            "total_count": 2,
            "page_count": 1,
            "list": [{"corp_name": "회사2", "rcept_no": "2"}]
        }
        mock_response_page2.raise_for_status = MagicMock()

        # get 메서드가 호출될 때마다 다른 응답을 반환하도록 설정
        mock_get_retry_client.get.side_effect = [
            mock_response_page1,
            mock_response_page2
        ]

        disclosures = await dart_get_disclosures()

        assert len(disclosures) == 2
        assert disclosures[0]["corp_name"] == "회사1"
        assert disclosures[1]["corp_name"] == "회사2"
        assert mock_get_retry_client.get.call_count == 2