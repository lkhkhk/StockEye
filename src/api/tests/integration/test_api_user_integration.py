# src/api/tests/integration/test_api_user_integration.py
"""
API 통합 테스트: 사용자 관리 API

이 파일은 `/api/v1/users/` 엔드포인트 그룹에 대한 통합 테스트를 포함합니다.
사용자 가입, 로그인, 정보 조회/수정, 텔레그램 연동, 통계 조회 등
사용자 관리와 관련된 전반적인 기능을 검증합니다.

`TestClient`를 사용하여 API 요청을 보내고, `real_db` fixture를 통해 실제 데이터베이스와의
상호작용을 검증합니다. 서비스 계층에 대한 모의(Mock)는 사용하지 않습니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
import random

from src.api.tests.helpers import create_test_user, get_auth_headers
from src.common.schemas.user import UserRead, Token

# --- Registration Tests ---

def test_register_user_success(client: TestClient, real_db: Session):
    """
    - **테스트 대상**: `POST /api/v1/users/register`
    - **목적**: 새로운 사용자가 성공적으로 가입하는지 확인합니다.
    - **시나리오**:
        1. 고유한 사용자 이름과 이메일로 가입을 요청합니다.
        2. 200 OK 응답과 함께, 생성된 사용자 정보가 반환되는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    username = f"testuser_{uuid4().hex}"
    email = f"{username}@test.com"
    password = "password123"

    # When
    response = client.post("/api/v1/users/register", json={"username": username, "email": email, "password": password})

    # Then
    assert response.status_code == 200
    data = UserRead.model_validate(response.json())
    assert data.username == username


def test_register_user_duplicate_username(client: TestClient, real_db: Session):
    """
    - **테스트 대상**: `POST /api/v1/users/register`
    - **목적**: 이미 존재하는 사용자 이름으로 가입 시도 시, 400 에러를 반환하는지 확인합니다.
    - **시나리오**:
        1. 테스트 사용자를 미리 생성합니다.
        2. 동일한 사용자 이름으로 다시 가입을 요청합니다.
        3. 400 Bad Request 응답과 함께, 중복 가입 오류 메시지가 반환되는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    user = create_test_user(real_db)

    # When
    response = client.post("/api/v1/users/register", json={"username": user.username, "email": f"new_{user.email}", "password": "new_password"})

    # Then
    assert response.status_code == 400
    assert "Username or email already registered" in response.json()["detail"]

# --- Login Tests ---

def test_login_user_success(client: TestClient, real_db: Session):
    """
    - **테스트 대상**: `POST /api/v1/users/login`
    - **목적**: 올바른 정보로 로그인 시, 성공적으로 JWT 토큰을 발급받는지 확인합니다.
    - **시나리오**:
        1. 테스트 사용자를 생성합니다.
        2. 해당 사용자의 정보로 로그인을 요청합니다.
        3. 200 OK 응답과 함께, `access_token`과 `token_type`이 포함된 응답을 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    user = create_test_user(real_db)

    # When
    response = client.post("/api/v1/users/login", json={"username": user.username, "password": "password123"})

    # Then
    assert response.status_code == 200
    data = Token.model_validate(response.json())
    assert data.token_type == "bearer"

def test_login_user_wrong_password(client: TestClient, real_db: Session):
    """
    - **테스트 대상**: `POST /api/v1/users/login`
    - **목적**: 틀린 비밀번호로 로그인 시, 401 에러를 반환하는지 확인합니다.
    - **시나리오**:
        1. 테스트 사용자를 생성합니다.
        2. 틀린 비밀번호로 로그인을 요청합니다.
        3. 401 Unauthorized 응답을 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    user = create_test_user(real_db)

    # When
    response = client.post("/api/v1/users/login", json={"username": user.username, "password": "wrongpassword"})

    # Then
    assert response.status_code == 401

# --- Get/Update Me Tests ---

def test_get_me_success(client: TestClient, real_db: Session):
    """
    - **테스트 대상**: `GET /api/v1/users/me`
    - **목적**: 인증된 사용자가 자신의 정보를 성공적으로 조회하는지 확인합니다.
    - **시나리오**:
        1. 테스트 사용자를 생성하고 인증 헤더를 발급받습니다.
        2. `/me` 엔드포인트를 호출합니다.
        3. 200 OK 응답과 함께, 자신의 사용자 정보가 반환되는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    user = create_test_user(real_db)
    headers = get_auth_headers(user)

    # When
    response = client.get("/api/v1/users/me", headers=headers)

    # Then
    assert response.status_code == 200
    assert UserRead.model_validate(response.json()).username == user.username

def test_get_me_unauthenticated(client: TestClient):
    """
    - **테스트 대상**: `GET /api/v1/users/me`
    - **목적**: 인증되지 않은 사용자가 `/me` 정보 조회 시, 접근이 거부되는지 확인합니다.
    - **시나리오**:
        1. 인증 헤더 없이 `/me` 엔드포인트를 호출합니다.
        2. 403 Forbidden 응답을 확인합니다. (수정 필요: 401 Unauthorized가 더 적절)
    - **Mock 대상**: 없음
    """
    # When
    response = client.get("/api/v1/users/me")
    # Then
    # TODO: 미인증 요청에 대해서는 403이 아닌 401을 반환하도록 수정해야 합니다.
    assert response.status_code == 401

def test_update_me_success(client: TestClient, real_db: Session):
    """
    - **테스트 대상**: `PUT /api/v1/users/me`
    - **목적**: 인증된 사용자가 자신의 정보를 성공적으로 수정하는지 확인합니다.
    - **시나리오**:
        1. 테스트 사용자를 생성하고 인증 헤더를 발급받습니다.
        2. 새로운 이메일 주소를 포함하여 수정 API를 호출합니다.
        3. 200 OK 응답과 함께, 이메일이 수정된 사용자 정보가 반환되는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    user = create_test_user(real_db)
    headers = get_auth_headers(user)
    new_email = f"updated_{user.email}"

    # When
    response = client.put("/api/v1/users/me", json={"email": new_email}, headers=headers)

    # Then
    assert response.status_code == 200
    assert UserRead.model_validate(response.json()).email == new_email

# --- Telegram Registration Tests ---

def test_telegram_register_new_user(client: TestClient, real_db: Session):
    """
    - **테스트 대상**: `PUT /api/v1/users/telegram_register`
    - **목적**: 새로운 텔레그램 ID로 요청 시, 신규 사용자가 생성되는지 확인합니다.
    - **시나리오**:
        1. 고유한 텔레그램 ID로 등록 API를 호출합니다.
        2. 200 OK 응답과 함께 `result`가 "registered"로 반환되는지 확인합니다.
        3. 사용자 조회 API를 통해 해당 텔레그램 ID의 사용자가 실제로 생성되었는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    telegram_id = random.randint(1000000000, 9999999999)

    # When
    response = client.put("/api/v1/users/telegram_register", json={"telegram_id": str(telegram_id), "is_active": True})

    # Then
    assert response.status_code == 200
    assert response.json()["result"] == "registered"
    response_get = client.get(f"/api/v1/users/telegram/{telegram_id}")
    assert response_get.status_code == 200
    assert response_get.json()["telegram_id"] == telegram_id

# --- Stats and Admin Tests ---

def test_get_user_stats_success(client: TestClient, real_db: Session):
    """
    - **테스트 대상**: `GET /api/v1/users/stats/{user_id}`
    - **목적**: 특정 사용자의 통계 정보를 성공적으로 조회하는지 확인합니다.
    - **시나리오**:
        1. 테스트 사용자를 생성합니다.
        2. 해당 사용자의 ID로 통계 조회 API를 호출합니다.
        3. 200 OK 응답과 함께, `trade_count` 등의 통계 정보가 포함된 응답을 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    user = create_test_user(real_db)

    # When
    response = client.get(f"/api/v1/users/stats/{user.id}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user.id
    assert data["trade_count"] == 0

def test_get_all_users_as_admin(client: TestClient, real_db: Session):
    """
    - **테스트 대상**: `GET /api/v1/users/`
    - **목적**: 관리자 권한으로 모든 사용자 목록을 조회하는 기능을 확인합니다.
    - **시나리오**:
        1. 관리자 사용자를 포함하여 여러 사용자를 생성합니다.
        2. 관리자 인증 헤더로 사용자 목록 API를 호출합니다.
        3. 200 OK 응답과 함께, 생성된 사용자들이 포함된 목록이 반환되는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    admin_user = create_test_user(real_db, role="admin")
    headers = get_auth_headers(admin_user)
    create_test_user(real_db)  # 일반 사용자 추가

    # When
    response = client.get("/api/v1/users/", headers=headers)

    # Then
    assert response.status_code == 200
    assert len(response.json()) >= 2

def test_get_all_users_as_user(client: TestClient, real_db: Session):
    """
    - **테스트 대상**: `GET /api/v1/users/`
    - **목적**: 일반 사용자가 전체 사용자 목록 조회 시, 403 에러를 받는지 확인합니다.
    - **시나리오**:
        1. 일반 사용자를 생성하고 인증 헤더를 발급받습니다.
        2. 사용자 목록 API를 호출합니다.
        3. 403 Forbidden 응답을 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given
    user = create_test_user(real_db, role="user")
    headers = get_auth_headers(user)

    # When
    response = client.get("/api/v1/users/", headers=headers)

    # Then
    assert response.status_code == 403