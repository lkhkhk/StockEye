import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app # Only import app
import os
import datetime # Import datetime module

def test_client_initialization_only():
    with patch('src.api.main.on_startup'): # Patch on_startup to do nothing
        # Mock datetime.datetime.now().isoformat() for consistent timestamp assertion
        mock_now_return_value = MagicMock()
        mock_now_return_value.isoformat.return_value = "2023-01-01T00:00:00"
        with patch('src.api.main.datetime') as mock_datetime_class:
            mock_datetime_class.now.return_value = mock_now_return_value

            client = TestClient(app)
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy", "timestamp": "2023-01-01T00:00:00"}
