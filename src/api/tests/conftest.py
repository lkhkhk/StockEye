import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
import psycopg2
import importlib
import pkgutil

from src.api.main import app
from src.common.database.db_connector import Base, get_db

# --- DB 설정 ---
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
TEST_DB_NAME = "test_stocks_db"

# --- 모델 임포트 ---
def import_all_models():
    models_package = importlib.import_module("src.common.models")
    for _, name, _ in pkgutil.iter_modules(models_package.__path__):
        if name != "__init__":
            importlib.import_module(f"src.common.models.{name}")

import_all_models()

@pytest.fixture(scope="session")
def db_engine():
    """세션 스코프 fixture: 테스트 DB를 생성/삭제하고 SQLAlchemy 엔진을 제공합니다."""
    # 기본 DB에 연결하여 테스트 DB 관리
    conn_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres"
    conn = psycopg2.connect(conn_url)
    conn.autocommit = True
    cur = conn.cursor()

    # 기존 연결 종료 및 DB 삭제
    cur.execute(f"SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '{TEST_DB_NAME}';")
    cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME};")
    cur.execute(f"CREATE DATABASE {TEST_DB_NAME};")
    cur.close()
    conn.close()

    # 테스트 DB로의 엔진 생성
    test_db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TEST_DB_NAME}"
    engine = create_engine(test_db_url)
    
    yield engine

    # 세션 종료 후 정리
    engine.dispose()
    conn = psycopg2.connect(conn_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '{TEST_DB_NAME}';")
    cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME};")
    cur.close()
    conn.close()

@pytest.fixture(scope="function")
def real_db(db_engine):
    """함수 스코프 fixture: 각 테스트에 대해 깨끗한 테이블과 세션을 제공합니다."""
    # 테이블 생성
    Base.metadata.create_all(bind=db_engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()

    yield session

    # 테스트 종료 후 정리
    session.close()
    Base.metadata.drop_all(bind=db_engine)

from src.common.models.user import User
from src.common.models.stock_master import StockMaster
from src.api.services.user_service import UserService
from src.common.schemas.user import UserCreate # Added import
from uuid import uuid4

@pytest.fixture(scope="function")
def test_user(real_db: Session):
    """테스트용 사용자 생성 및 반환"""
    user_service = UserService()
    telegram_id = int(f"123{uuid4().hex[:7]}", 16) # Unique telegram_id
    username = f"test_user_{uuid4().hex[:8]}"
    email = f"{username}@test.com"
    password = "test_password"

    user_create_data = UserCreate(
        username=username,
        email=email,
        password=password,
        telegram_id=telegram_id # telegram_id는 UserCreate 스키마에 없으므로, 필요시 User 모델에 직접 할당하거나 스키마에 추가해야 합니다.
    )

    user = user_service.create_user(
        real_db,
        user=user_create_data
    )
    real_db.commit()
    real_db.refresh(user)
    return user

@pytest.fixture(scope="function")
def test_stock_master_data(real_db: Session):
    """테스트용 StockMaster 데이터 삽입"""
    stocks = [
        StockMaster(symbol="005930", name="삼성전자", market="KOSPI"),
        StockMaster(symbol="000660", name="SK하이닉스", market="KOSPI"),
        StockMaster(symbol="035720", name="카카오", market="KOSPI"),
        StockMaster(symbol="005380", name="현대차", market="KOSPI"),
        StockMaster(symbol="000270", name="기아", market="KOSPI"),
        StockMaster(symbol="GOOG", name="Alphabet Inc.", market="NASDAQ"),
        StockMaster(symbol="AAPL", name="Apple Inc.", market="NASDAQ"),
        StockMaster(symbol="MSFT", name="Microsoft Corp.", market="NASDAQ"),
        StockMaster(symbol="AMZN", name="Amazon.com Inc.", market="NASDAQ"),
        StockMaster(symbol="NFLX", name="Netflix Inc.", market="NASDAQ"),
    ]
    real_db.add_all(stocks)
    real_db.commit()
    for stock in stocks:
        real_db.refresh(stock)
    return stocks

@pytest.fixture(scope="function")
def client(real_db):
    """TestClient fixture: get_db 의존성을 오버라이드합니다."""
    def override_get_db():
        try:
            yield real_db
        finally:
            real_db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()