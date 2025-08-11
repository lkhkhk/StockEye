import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os
import httpx
import zipfile
import io
from src.common.dart_utils import dart_get_all_stocks, dart_get_disclosures
from src.common.exceptions import DartApiError

@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {"DART_API_KEY": "test_api_key"}):
        yield

@pytest.fixture
def mock_get_retry_client():
    with patch('src.common.dart_utils.get_retry_client') as mock_client:
        # __aenter__와 __aexit__를 포함하는 AsyncMock을 설정합니다.
        async_mock_client = AsyncMock()
        mock_get = AsyncMock()
        async_mock_client.__aenter__.return_value = mock_get
        mock_client.return_value = async_mock_client
        yield mock_get

class TestDartUtils:
    @pytest.mark.asyncio
    async def test_dart_get_all_stocks_success(self, mock_get_retry_client):
        # Mocking the zip file content
        mock_zip_content = io.BytesIO()
        with zipfile.ZipFile(mock_zip_content, 'w') as zf:
            # Create a dummy XML content for CORPCODE.xml
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

        disclosures = await dart_get_disclosures(corp_code="00123456")

        assert len(disclosures) == 1
        assert disclosures[0]["corp_name"] == "삼성전자"
        mock_get_retry_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_dart_get_disclosures_api_key_missing(self):
        with patch.dict(os.environ, {"DART_API_KEY": ""}):
            with pytest.raises(ValueError, match="DART_API_KEY가 환경변수에 없거나 인자로 전달되지 않았습니다."):
                await dart_get_disclosures(corp_code="00123456")

    @pytest.mark.asyncio
    async def test_dart_get_disclosures_request_error(self, mock_get_retry_client):
        mock_get_retry_client.get.side_effect = httpx.RequestError("Network error", request=httpx.Request("GET", "http://test.com"))
        with pytest.raises(DartApiError, match="DART API 요청 실패"):
            await dart_get_disclosures(corp_code="00123456")

    @pytest.mark.asyncio
    async def test_dart_get_disclosures_api_error_response(self, mock_get_retry_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "001",
            "message": "API 호출 오류"
        }
        mock_response.raise_for_status = MagicMock()
        mock_get_retry_client.get.return_value = mock_response

        with pytest.raises(DartApiError, match="API 호출 오류"):
            await dart_get_disclosures(corp_code="00123456")