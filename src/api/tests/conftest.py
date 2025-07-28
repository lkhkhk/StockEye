import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from src.api.main import app
from src.common.db_connector import get_db, Base
import pkgutil
import importlib
import os
import psycopg2 # Import psycopg2
from src.api.services.user_service import UserService
from src.api.services.price_alert_service import PriceAlertService

# 환경 변수 로드
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "db") # Docker 환경에서는 db 컨테이너 이름
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "stocks_db") # 실제 DB 이름
TEST_DB_NAME = "test_stocks_db" # 테스트용 DB 이름

# PostgreSQL 연결 문자열
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TEST_DB_NAME}"
ROOT_SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres" # DB 생성/삭제용 (connect to default 'postgres' db)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모든 SQLAlchemy 모델을 임포트하여 테스트 DB 스키마를 완전하게 생성
def import_all_models():
    models_package = importlib.import_module("src.api.models")
    for _, name, _ in pkgutil.iter_modules(models_package.__path__):
        if name != "__init__":
            importlib.import_module(f"src.api.models.{name}")

import_all_models()

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """테스트 세션 시작 전에 테스트 DB를 생성하고, 세션 종료 후에 삭제합니다."""
    print(f"Attempting to connect to PostgreSQL at {DB_HOST}:{DB_PORT} as user {DB_USER} for DB operations.")
    conn = None
    try:
        # Connect to the default 'postgres' database to create/drop test_db
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True # Ensure autocommit for DDL operations
        cur = conn.cursor()

        print(f"Dropping database {TEST_DB_NAME} if it exists...")
        # Drop existing test database if it exists
        cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE);")
        print(f"Creating database {TEST_DB_NAME}...")
        # Create the test database
        cur.execute(f"CREATE DATABASE {TEST_DB_NAME};")
        print(f"Database {TEST_DB_NAME} created successfully.")

        cur.close()
    except Exception as e:
        print(f"Error during test database setup: {e}")
        raise
    finally:
        if conn:
            conn.close()

    # Create all tables in the test database
    print("Creating all tables in the test database...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully.")

    # 다음번 call 될 때까지 대기상태로 있다가 call 되면 계속 실행된다.
    print("Test database setup complete. Ready to run tests.")
    yield # Run tests

    # Teardown: Drop the test database after all tests are done
    print(f"Attempting to drop database {TEST_DB_NAME} after tests...")
    conn = None
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE);")
        cur.close()
        print(f"Database {TEST_DB_NAME} dropped successfully.")
    except Exception as e:
        print(f"Error during test database teardown: {e}")
        raise
    finally:
        if conn:
            conn.close()

@pytest.fixture(scope="function")
def db():
    """함수 범위의 DB 세션을 생성하고, 각 테스트 종료 후 데이터를 롤백합니다."""
    connection = engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)

    # 각 테스트 시작 전에 테이블을 재생성
    Base.metadata.drop_all(bind=connection)
    Base.metadata.create_all(bind=connection)

    yield db

    db.close()
    transaction.rollback() # 트랜잭션 롤백 (데이터 삭제는 유지)
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    """함수 범위의 TestClient를 생성하고, get_db 의존성을 오버라이드합니다."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    del app.dependency_overrides[get_db]

@pytest.fixture(scope="function")
def user_service():
    return UserService()

import random

@pytest.fixture(name="test_user")
def test_user_fixture(db: Session):
    user_service = UserService()
    telegram_id = random.randint(1000000000, 9999999999) # 고유한 텔레그램 ID 생성
    user_data = {
        "telegram_id": telegram_id,
        "username": f"testuser_{telegram_id}",
        "first_name": "Test",
        "last_name": "User"
    }
    user = user_service.create_user_from_telegram(db, **user_data)
    yield user

@pytest.fixture(scope="function")
def price_alert_service():
    return PriceAlertService()