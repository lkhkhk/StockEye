import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
from uuid import uuid4
import json

from src.api.main import app
from src.common.models.user import User
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice
from src.common.services.user_service import UserService
from src.common.schemas.user import UserCreate
import src.api.routers.auth as auth_router # Import the auth router module
import httpx # Import httpx

@pytest.fixture
def admin_user_token(client: TestClient, real_db: Session, mocker):
    # Create an admin user for testing
    user_service = UserService()
    telegram_id = 1234567890 # Use a fixed, valid integer for telegram_id
    username = f"admin_test_user_{uuid4().hex[:8]}"
    email = f"{username}@test.com"
    password = "admin_password"

    admin_user_create_data = UserCreate(
        username=username,
        email=email,
        password=password,
        telegram_id=telegram_id
    )
    admin_user = user_service.create_user(real_db, user=admin_user_create_data)
    admin_user.role = "admin" # Set role to admin
    real_db.commit()
    real_db.refresh(admin_user)

    print(f"DEBUG: Created admin_user with ID: {admin_user.id}, telegram_id: {admin_user.telegram_id}, role: {admin_user.role}")

    # Mock BOT_SECRET_KEY directly in the auth router module
    mocker.patch.object(auth_router, "BOT_SECRET_KEY", "test_secret_key")

    # Get token for the admin user using the bot token endpoint
    headers = {"X-Bot-Secret-Key": "test_secret_key"}
    payload = {"telegram_id": admin_user.telegram_id}
    response = client.post("/api/v1/auth/bot/token/admin", headers=headers, json=payload)
    assert response.status_code == 200, f"Failed to get admin token: {response.text}"
    return response.json()["access_token"]

def test_update_historical_prices_for_specific_stock(client: TestClient, real_db: Session, admin_user_token: str, test_stock_master_data, mocker):
    # Given
    stock_to_update = test_stock_master_data[0] # 삼성전자
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    payload = {
        "start_date": start_date,
        "end_date": end_date,
        "stock_identifier": stock_to_update.symbol,
        "chat_id": 12345 # Dummy chat_id for testing
    }

    # Mock httpx.AsyncClient.post
    mock_response = httpx.Response(200, json={"message": "Mocked success", "status": "triggered"})
    mock_response.request = httpx.Request("POST", "http://mocked-url.com") # Add a dummy request object
    mock_post = mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

    # When
    response = client.post("/api/v1/admin/update_historical_prices", headers=headers, json=payload)

    # Then
    assert response.status_code == 200
    assert response.json()["message"] == "과거 일별 시세 갱신 작업이 성공적으로 트리거되었습니다."
    assert response.json()["status"] == "triggered"

    # Verify that the worker endpoint was called with the correct payload
    mock_post.assert_called_once()
    called_url = mock_post.call_args[0][0]
    called_json = mock_post.call_args[1]["json"]
    assert "/scheduler/trigger_historical_prices_update" in str(called_url)
    assert called_json["start_date"] == start_date
    assert called_json["end_date"] == end_date
    assert called_json["stock_identifier"] == stock_to_update.symbol
    assert called_json["chat_id"] == 12345

    # Verify that no daily prices exist for this stock yet (worker will create them)
    daily_prices = real_db.query(DailyPrice).filter(DailyPrice.symbol == stock_to_update.symbol).all()
    assert len(daily_prices) == 0

def test_update_historical_prices_for_all_stocks(client: TestClient, real_db: Session, admin_user_token: str, test_stock_master_data, mocker):
    # Given
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    payload = {
        "start_date": start_date,
        "end_date": end_date,
        "chat_id": 12345 # Dummy chat_id for testing
    }

    # Mock httpx.AsyncClient.post
    mock_response = httpx.Response(200, json={"message": "Mocked success", "status": "triggered"})
    mock_response.request = httpx.Request("POST", "http://mocked-url.com") # Add a dummy request object
    mock_post = mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

    # When
    response = client.post("/api/v1/admin/update_historical_prices", headers=headers, json=payload)

    # Then
    assert response.status_code == 200
    assert response.json()["message"] == "과거 일별 시세 갱신 작업이 성공적으로 트리거되었습니다."
    assert response.json()["status"] == "triggered"

    # Verify that the worker endpoint was called with the correct payload
    mock_post.assert_called_once()
    called_url = mock_post.call_args[0][0]
    called_json = mock_post.call_args[1]["json"]
    assert "/scheduler/trigger_historical_prices_update" in str(called_url)
    assert called_json["start_date"] == start_date
    assert called_json["end_date"] == end_date
    assert called_json["stock_identifier"] is None # Should be None for all stocks update
    assert called_json["chat_id"] == 12345

    # Verify that no daily prices exist yet (worker will create them)
    daily_prices = real_db.query(DailyPrice).all()
    assert len(daily_prices) == 0

def test_update_historical_prices_invalid_date_format(client: TestClient, admin_user_token: str, mocker):
    # Given
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    payload = {
        "start_date": "2023-01-01",
        "end_date": "invalid-date",
        "chat_id": 12345
    }

    # Mock httpx.AsyncClient.post to ensure it's not called
    mock_post = mocker.patch("httpx.AsyncClient.post")

    # When
    response = client.post("/api/v1/admin/update_historical_prices", headers=headers, json=payload)

    # Then
    assert response.status_code == 400
    assert response.json()["detail"] == "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해주세요."
    mock_post.assert_not_called() # Worker should not be called for invalid input

def test_update_historical_prices_missing_chat_id_and_telegram_id(client: TestClient, real_db: Session, admin_user_token: str, mocker):
    # Given
    # Create a user without telegram_id
    user_service = UserService()
    username = f"no_telegram_{uuid4().hex[:8]}"
    email = f"{username}@test.com"
    password = "test_password"
    user_create_data = UserCreate(username=username, email=email, password=password)
    user_without_telegram_id = user_service.create_user(real_db, user=user_create_data)
    real_db.commit()
    real_db.refresh(user_without_telegram_id)

    # Mock httpx.AsyncClient.post to raise an HTTPStatusError
    mock_response_detail = {"detail": "텔레그램 ID가 없거나 요청에 chat_id가 포함되지 않았습니다."}
    mock_response = httpx.Response(400, json=mock_response_detail)
    mock_response.request = httpx.Request("POST", "http://mocked-url.com")
    mock_post = mocker.patch("httpx.AsyncClient.post", side_effect=httpx.HTTPStatusError(
        message="Client error '400 Bad Request' for url 'http://mocked-url.com'",
        request=mock_response.request,
        response=mock_response
    ))

    headers = {"Authorization": f"Bearer {admin_user_token}"}
    payload = {
        "start_date": "2023-01-01",
        "end_date": "2023-01-01",
        "stock_identifier": "005930"
        # No chat_id provided
    }

    # When
    response = client.post("/api/v1/admin/update_historical_prices", headers=headers, json=payload)

    # Then
    assert response.status_code == 400
    # Compare parsed JSON objects
    expected_detail_dict = {"detail": "텔레그램 ID가 없거나 요청에 chat_id가 포함되지 않았습니다."}
    # Parse the actual response detail string as JSON
    actual_detail_str = response.json()["detail"].replace("워커 서비스 오류: ", "")
    actual_detail_dict = json.loads(actual_detail_str)
    assert actual_detail_dict == expected_detail_dict
