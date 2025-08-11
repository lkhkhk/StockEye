import pytest
from unittest.mock import patch, MagicMock
import httpx
import os
import importlib

# http_client 모듈을 import 하기 전에 필요한 mock을 설정해야 할 수 있으므로, 
# 테스트 함수 내에서 import 또는 reload를 수행합니다.

@pytest.mark.asyncio
@patch('os.getenv')
def test_get_retry_client_initialization(mock_getenv):
    """Test the default initialization of the HTTP client."""
    # 1. Setup
    from src.common import http_client
    
    mock_getenv.return_value = "defaulthost"

    # 모듈이 로드될 때 getenv가 호출되므로, reload를 통해 다시 호출하게 만듭니다.
    with patch('httpx.AsyncHTTPTransport') as mock_transport_class, \
         patch('httpx.AsyncClient') as mock_async_client_class:
        
        mock_transport_instance = MagicMock(spec=httpx.AsyncHTTPTransport)
        mock_transport_class.return_value = mock_transport_instance
        
        mock_async_client_instance = MagicMock(spec=httpx.AsyncClient)
        mock_async_client_class.return_value = mock_async_client_instance

        # 2. Execute
        importlib.reload(http_client)
        client = http_client.get_retry_client()

        # 3. Assert
        mock_getenv.assert_called_with("API_HOST", "localhost")
        mock_transport_class.assert_called_once_with(retries=3)
        mock_async_client_class.assert_called_once_with(
            base_url='http://defaulthost:8000',
            transport=mock_transport_instance,
            timeout=10.0
        )
        # get_retry_client()는 새로 생성된 인스턴스를 반환해야 합니다.
        assert client == mock_async_client_instance
