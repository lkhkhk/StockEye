# src/api/tests/integration/test_seed_data_integration.py
"""
**테스트 데이터베이스 시딩(Seeding) 스크립트**

**주의: 이 파일은 일반적인 테스트 파일이 아닙니다.**

이 파일은 `pytest`를 실행 도구로 사용하여, 테스트 데이터베이스에 초기 데이터를
생성(seed)하기 위한 스크립트입니다. `assert` 구문을 포함하고 있지 않으며,
오직 DB 상태를 변경하는 역할만 합니다.

**사용 목적**:
- 다른 통합 테스트나 E2E 테스트를 실행하기 전에, 필요한 기본 데이터를 DB에 미리 채워 넣기 위함입니다.
- 개발 환경에서 특정 데이터가 있는 상태를 만들어 테스트할 때 수동으로 실행할 수 있습니다.

**실행 방법**:
`docker compose exec stockeye-api pytest tests/integration/test_seed_data_integration.py`
"""

import pytest
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
from datetime import datetime, timedelta

from src.common.models.user import User
from src.common.models.stock_master import StockMaster
from src.common.models.price_alert import PriceAlert
from src.common.models.daily_price import DailyPrice

# --- 데이터베이스 연결 설정 --- #
# 환경 변수에서 DB 정보를 가져오거나 기본값을 사용합니다.
DB_USER = os.getenv("DB_USER", "testuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "testpassword")
DB_HOST = os.getenv("DB_HOST", "stockeye-db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "test_stocks_db")
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module", autouse=True)
def cleanup_db():
    """
    모듈의 모든 테스트 실행 전, 관련 테이블의 모든 데이터를 삭제하는 Fixture.

    - **목적**: 매번 실행 시 깨끗한 상태에서 데이터를 생성하기 위함입니다.
    - **적용**: `autouse=True`로 설정되어 이 모듈 실행 시 자동으로 가장 먼저 실행됩니다.
    """
    print("\nCleaning up database for seeding...")
    db = SessionLocal()
    try:
        # 의존성 순서를 고려하여 자식 테이블부터 삭제
        db.query(PriceAlert).delete()
        db.query(DailyPrice).delete()
        db.query(User).delete()
        db.query(StockMaster).delete()
        db.commit()
        print("Database cleaned up.")
    finally:
        db.close()


def test_seed_data():
    """
    - **테스트 대상**: 테스트 데이터베이스
    - **목적**: 테스트에 필요한 기본 데이터를 DB에 생성합니다.
    - **시나리오**:
        1. 테스트 사용자 1명을 생성합니다.
        2. 삼성전자 종목 정보 1건을 생성합니다.
        3. 위 종목에 대한 40일 치의 가상 일별 가격 데이터를 생성합니다.
    - **Mock 대상**: 없음
    """
    print("Seeding database with test data...")
    db = SessionLocal()
    try:
        # 1. 사용자 생성
        user = User(
            username="testuser_12345",
            password_hash="testpassword",  # 실제 앱에서는 해시된 비밀번호 사용
            email="testuser_12345@example.com",
            telegram_id=12345
        )
        db.add(user)

        # 2. 종목 마스터 생성
        stock = StockMaster(
            symbol="005930",
            name="Samsung Electronics",
            market="KOSPI"
        )
        db.add(stock)

        # 3. 40일 치의 일별 가격 데이터 생성
        today = datetime.utcnow().date()
        for i in range(40):
            past_date = today - timedelta(days=i)
            # 가상의 가격 데이터 생성 (매일 1씩 증가)
            price = 100.0 + i
            daily_price = DailyPrice(
                symbol="005930",
                date=past_date,
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000000
            )
            db.add(daily_price)

        db.commit()
        print(f"Seeding complete. User '{user.username}' and 40 days of price data for '{stock.symbol}' created.")
    finally:
        db.close()