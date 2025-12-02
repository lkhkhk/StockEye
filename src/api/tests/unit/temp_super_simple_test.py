import pytest
from fastapi.testclient import TestClient
from src.api.main import app # Import the main app

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

@pytest.mark.asyncio
async def test_super_simple_endpoint_success(client):
    # WHEN
    response = client.get("/super_simple_test")

    # THEN
    assert response.status_code == 200
    assert response.json() == {"message": "Super simple test successful!"}
    # Check for print statement in logs
