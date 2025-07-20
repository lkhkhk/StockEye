import sys
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from uuid import uuid4

client = TestClient(app)

def get_token():
    unique = str(uuid4())[:8]
    username = f"alertuser_{unique}"
    email = f"alertuser_{unique}@example.com"
    password = "testpass"
    # 회원가입
    reg_payload = {"username": username, "email": email, "password": password}
    reg_resp = client.post("/users/register", json=reg_payload)
    assert reg_resp.status_code == 200 or reg_resp.status_code == 201
    # 로그인
    login_payload = {"username": username, "password": password}
    login_resp = client.post("/users/login", json=login_payload)
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    return token

def test_create_price_alert():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"symbol": "005930", "target_price": 70000, "condition": "gte"}
    resp = client.post("/alerts/", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "005930"
    assert data["target_price"] == 70000
    assert data["condition"] == "gte"
    assert data["is_active"] is True

def test_get_my_alerts():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    # 알림 생성
    payload = {"symbol": "000660", "target_price": 120000, "condition": "lte"}
    client.post("/alerts/", json=payload, headers=headers)
    # 내 알림 목록 조회
    resp = client.get("/alerts/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["symbol"] in ["000660", "005930"]

def test_update_and_delete_alert():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    # 알림 생성
    payload = {"symbol": "035420", "target_price": 400000, "condition": "gte"}
    resp = client.post("/alerts/", json=payload, headers=headers)
    alert_id = resp.json()["id"]
    # 알림 수정
    update_payload = {"target_price": 410000, "is_active": False}
    resp2 = client.put(f"/alerts/{alert_id}", json=update_payload, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["target_price"] == 410000
    assert resp2.json()["is_active"] is False
    # 알림 삭제
    resp3 = client.delete(f"/alerts/{alert_id}", headers=headers)
    assert resp3.status_code == 200
    assert resp3.json()["result"] is True 