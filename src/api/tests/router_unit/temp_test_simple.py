import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.routers.notification import router as notification_router

@pytest.fixture
def client():
    test_app = FastAPI()
    test_app.include_router(notification_router, prefix="/api/v1")
    with TestClient(test_app) as client:
        yield client

@pytest.mark.asyncio
async def test_simple_endpoint_success(client):
    # WHEN
    response = client.get("/api/v1/alerts/test_simple")

    # THEN
    assert response.status_code == 200
    assert response.json() == {"message": "Simple endpoint reached"}
