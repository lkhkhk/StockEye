# 이 파일은 src.common.http_client 모듈의 단위 테스트를 포함합니다.
#
# http_client 모듈은 로드될 때 환경 변수를 읽어 AsyncClient를 초기화합니다.
# 이 테스트는 실제 HTTP 클라이언트를 생성하거나 외부와 통신하는 대신,
# httpx.AsyncClient와 os.getenv를 모의(mock)하여, 클라이언트가
# 올바른 설정(base_url, retries 등)으로 초기화되는지를 검증합니다.

import pytest
from unittest.mock import patch, MagicMock
import httpx
import os
import importlib

# http_client 모듈을 import 하기 전에 필요한 mock을 설정해야 할 수 있으므로,
# 테스트 함수 내에서 import 또는 reload를 수행합니다.

@patch('os.getenv')
def test_get_retry_client_initialization(mock_getenv):
    """HTTP 클라이언트의 기본 초기화 로직을 테스트합니다."""
    # 1. Setup
    from src.common.utils import http_client
    
    # MOCK: os.getenv
    # os.getenv가 특정 호스트 이름을 반환하도록 설정합니다.
    mock_getenv.return_value = "defaulthost"

    # MOCK: httpx.AsyncHTTPTransport, httpx.AsyncClient
    # httpx의 AsyncHTTPTransport와 AsyncClient 클래스를 모의 객체로 대체합니다.
    # MagicMock: AsyncHTTPTransport와 AsyncClient는 클래스이므로 MagicMock을 사용합니다.
    with patch('httpx.AsyncHTTPTransport') as mock_transport_class, \
         patch('httpx.AsyncClient') as mock_async_client_class:
        
        # MagicMock: AsyncHTTPTransport 클래스의 인스턴스를 모의합니다.
        mock_transport_instance = MagicMock(spec=httpx.AsyncHTTPTransport)
        mock_transport_class.return_value = mock_transport_instance
        
        # MagicMock: AsyncClient 클래스의 인스턴스를 모의합니다.
        mock_async_client_instance = MagicMock(spec=httpx.AsyncClient)
        mock_async_client_class.return_value = mock_async_client_instance

        # 2. Execute
        # 모듈이 로드될 때 getenv가 호출되므로, reload를 통해
        # 모의 객체가 적용된 상태에서 모듈 로직을 다시 실행시킵니다.
        importlib.reload(http_client)
        client = http_client.get_retry_client()

        # 3. Assert
        # getenv가 올바른 인자로 호출되었는지 확인합니다.
        mock_getenv.assert_called_with("API_HOST", "localhost")
        # AsyncHTTPTransport가 올바른 재시도 횟수로 초기화되었는지 확인합니다.
        mock_transport_class.assert_called_once_with(retries=3)
        # AsyncClient가 올바른 base_url과 transport로 초기화되었는지 확인합니다.
        mock_async_client_class.assert_called_once_with(
            base_url='http://defaulthost:8000',
            transport=mock_transport_instance,
            timeout=10.0
        )
        # get_retry_client()가 생성된 모의 클라이언트 인스턴스를 반환하는지 확인합니다.
        assert client == mock_async_client_instance
