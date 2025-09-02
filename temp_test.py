import pytest
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

app = FastAPI()

class MockUser:
    def __init__(self, username="testuser"):
        self.username = username

def get_mock_user_success():
    return MockUser()

def get_mock_user_exception():
    raise Exception("Auth error from dependency")

@app.get("/test_endpoint")
def test_endpoint(user: MockUser = Depends(get_mock_user_exception)):
    return {"username": user.username}

client = TestClient(app)

def test_endpoint_exception_handling():
    response = client.get("/test_endpoint")
    assert response.status_code == 500
    assert response.json()["detail"] == "Auth error from dependency"