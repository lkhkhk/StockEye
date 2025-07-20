import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from uuid import uuid4

client = TestClient(app)

def test_user_register():
    unique = str(uuid4())[:8]
    username = f"testuser_{unique}"
    email = f"testuser_{unique}@example.com"
    password = "testpass"
    payload = {"username": username, "email": email, "password": password}
    response = client.post("/users/register", json=payload)
    assert response.status_code == 200 or response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "username" in data
    assert "email" in data
    assert "role" in data

def test_user_login():
    unique = str(uuid4())[:8]
    username = f"testuser_{unique}"
    email = f"testuser_{unique}@example.com"
    password = "testpass"
    # 먼저 회원가입
    reg_payload = {"username": username, "email": email, "password": password}
    reg_resp = client.post("/users/register", json=reg_payload)
    assert reg_resp.status_code == 200 or reg_resp.status_code == 201
    # 로그인
    payload = {"username": username, "password": password}
    response = client.post("/users/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert "user" in data

def test_user_stats():
    unique = str(uuid4())[:8]
    username = f"testuser_{unique}"
    email = f"testuser_{unique}@example.com"
    password = "testpass"
    # 회원가입
    reg_payload = {"username": username, "email": email, "password": password}
    reg_resp = client.post("/users/register", json=reg_payload)
    assert reg_resp.status_code == 200 or reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]
    # 통계 조회
    response = client.get(f"/users/stats/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert "username" in data
    assert "trade_count" in data
    assert "prediction_count" in data 