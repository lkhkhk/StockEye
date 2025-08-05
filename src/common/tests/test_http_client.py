import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock

from src.common.http_client import get_retry_client
from httpx import AsyncClient, AsyncHTTPTransport


@pytest.mark.asyncio
@patch('src.common.http_client.AsyncClient') # Patch the AsyncClient class directly
@patch('httpx.AsyncHTTPTransport') # Patch the AsyncHTTPTransport class directly
async def test_get_retry_client_retries_on_5xx_error(mock_transport_class, mock_async_client_class):
    """Test that the HTTP client retries on 503 Service Unavailable and then succeeds."""
    # 1. Setup
    # Mock the transport instance that AsyncHTTPTransport() will return
    mock_transport_instance = MagicMock(spec=AsyncHTTPTransport)
    mock_transport_instance.handle_async_request.side_effect = [
        httpx.Response(503, request=httpx.Request('GET', 'https://test.com')),
        httpx.Response(200, json={"message": "success"}, request=httpx.Request('GET', 'https://test.com')),
    ]
    mock_transport_class.return_value = mock_transport_instance # When AsyncHTTPTransport() is called, return this mock

    mock_response_503 = MagicMock()
    mock_response_503.status_code = 503
    mock_response_503.request = httpx.Request('GET', 'https://test.com')

    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {"message": "success"}
    mock_response_200.request = httpx.Request('GET', 'https://test.com')

    # Mock the AsyncClient instance that AsyncClient() will return
    mock_async_client_instance = MagicMock(spec=AsyncClient)
    mock_async_client_instance.get.side_effect = [
        httpx.Response(503, request=httpx.Request('GET', 'https://test.com')),
        httpx.Response(200, json={"message": "success"}, request=httpx.Request('GET', 'https://test.com')),
    ]
    mock_async_client_class.return_value = mock_async_client_instance # When AsyncClient() is called, return this mock

    # 2. Execute
    http_client = get_retry_client() # This will call AsyncClient() and AsyncHTTPTransport()

    # Now, call the get method on the mocked AsyncClient instance
    response = await http_client.get('https://test.com')

    # 3. Assert
    # Assert that AsyncHTTPTransport was initialized with retries=3
    mock_transport_class.assert_called_once_with(retries=3)

    # Assert that AsyncClient was initialized with the mocked transport and timeout
    mock_async_client_class.assert_called_once_with(transport=mock_transport_instance, timeout=10.0)

    # Assert the response and call count on the mocked AsyncClient's get method
    assert response.status_code == 200
    assert response.json() == {"message": "success"}
    assert mock_async_client_instance.get.call_count == 2


@pytest.mark.asyncio
@patch('src.common.http_client.AsyncClient')
@patch('httpx.AsyncHTTPTransport')
async def test_get_retry_client_timeout(mock_transport_class, mock_async_client_class):
    """Test that the HTTP client raises a TimeoutException after exhausting retries."""
    # 1. Setup
    mock_transport_instance = MagicMock(spec=AsyncHTTPTransport)
    mock_transport_instance.handle_async_request.side_effect = httpx.TimeoutException("Timeout", request=httpx.Request('GET', 'https://test.com'))
    mock_transport_class.return_value = mock_transport_instance

    mock_response_timeout = MagicMock()
    mock_response_timeout.request = httpx.Request('GET', 'https://test.com')
    mock_async_client_instance = MagicMock(spec=AsyncClient)
    mock_async_client_instance.get.side_effect = httpx.TimeoutException("Timeout", request=mock_response_timeout.request)
    mock_async_client_class.return_value = mock_async_client_instance

    # 2. Execute
    http_client = get_retry_client()

    # 3. Assert
    mock_transport_class.assert_called_once_with(retries=3)
    mock_async_client_class.assert_called_once_with(transport=mock_transport_instance, timeout=10.0)

    with pytest.raises(httpx.TimeoutException):
        await http_client.get('https://test.com')
    
    # Total attempts = 1 initial + 3 retries = 4
    assert mock_async_client_instance.get.call_count == 4
