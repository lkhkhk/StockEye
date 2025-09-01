import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine, Column, String, DateTime, BigInteger, Integer, Boolean, Float, ForeignKey, event, types, Date
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
import datetime
import redis
import sqlite3

# Import the service and schemas
from src.common.services.price_alert_service import PriceAlertService

# ======================================================================================
# [중요] SQLAlchemy/SQLite DATETIME 호환성 해결을 위한 커스텀 타입
# --------------------------------------------------------------------------------------
# 문제점:
#   - Python의 datetime.isoformat()은 'T' 구분자를 사용 (예: 2023-10-27T10:00:00).
#   - SQLite는 'T'가 없는 공백 구분 형식으로 datetime을 저장하는 경우가 많음.
#   - 마이크로초(microseconds)의 포함 여부가 경우에 따라 달라져 파싱 오류를 유발함.
# 해결책:
#   - process_bind_param: Python의 datetime 객체를 DB에 저장할 때 일관된 ISO 형식으로 변환.
#   - process_result_value: DB에서 문자열을 읽어올 때, 발생 가능한 여러 형식('T'/
#     공백 구분자, 마이크로초 유/무)을 모두 처리할 수 있도록 try-except로 파싱 시도.
# 주의:
#   - 이 클래스는 단위 테스트의 안정성을 위해 매우 중요하므로 임의로 수정하지 마십시오.
#   - 날짜만 필요한 경우, 이 클래스 대신 SQLAlchemy의 `Date` 타입을 사용하십시오.
# ======================================================================================
class SQLiteDateTime(types.TypeDecorator):
    impl = types.String # Use String as the underlying type

    def process_bind_param(self, value, dialect):
        if isinstance(value, datetime.datetime):
            return value.isoformat().split('.')[0]
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return datetime.datetime.fromisoformat(value)
        return value

# Define a new Base for testing purposes
TestBase = declarative_base()

# Define test models that mirror the actual models but use TestBase
@pytest.mark.skip(reason="Not a test class, used for SQLAlchemy model definition")
class TestUser(TestBase):
    __tablename__ = 'app_users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(128), nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    nickname = Column(String(50), unique=True, nullable=True)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), default='user', nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    created_at = Column(SQLiteDateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(SQLiteDateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    alerts = relationship("TestPriceAlert", back_populates="user")

@pytest.mark.skip(reason="Not a test class, used for SQLAlchemy model definition")
class TestStockMaster(TestBase):
    __tablename__ = 'stock_master'
    symbol = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    market = Column(String(20), nullable=True)
    corp_code = Column(String(20), nullable=True, index=True)
    created_at = Column(SQLiteDateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(SQLiteDateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    price_alerts = relationship("TestPriceAlert", back_populates="stock")

@pytest.mark.skip(reason="Not a test class, used for SQLAlchemy model definition")
class TestPriceAlert(TestBase):
    __tablename__ = 'price_alerts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('app_users.id'), nullable=False)
    symbol = Column(String(10), ForeignKey('stock_master.symbol'), nullable=False)
    target_price = Column(Float, nullable=True)
    condition = Column(String(5), nullable=True)
    change_percent = Column(Float, nullable=True)
    change_type = Column(String(5), nullable=True)
    notify_on_disclosure = Column(Boolean, default=True, nullable=False)
    notification_interval_hours = Column(Integer, nullable=False, default=24) # 알림 주기 (시간 단위)
    last_notified_at = Column(SQLiteDateTime, nullable=True) # 마지막 알림 전송 시간
    notification_count = Column(Integer, default=0, nullable=False) # 알림 전송 횟수
    is_active = Column(Boolean, default=True, nullable=False)
    repeat_interval = Column(String, nullable=True)
    created_at = Column(SQLiteDateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(SQLiteDateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user = relationship("TestUser", back_populates="alerts")
    stock = relationship("TestStockMaster", back_populates="price_alerts")


@pytest.mark.skip(reason="Not a test class, used for SQLAlchemy model definition")
class TestDailyPrice(TestBase):
    __tablename__ = 'daily_prices'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False)
    # [중요] 날짜만 필요한 경우, 복잡한 파싱 문제를 피하기 위해 `Date` 타입을 사용합니다.
    date = Column(Date, default=datetime.date.today, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    created_at = Column(SQLiteDateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(SQLiteDateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

# Setup in-memory SQLite database for testing
@pytest.fixture(scope='function')
def db_session():
    engine = create_engine('sqlite:///:memory:')
    TestBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    TestBase.metadata.drop_all(engine)

@pytest.fixture(scope='function')
def price_alert_service():
    # Patch the original models to use the test models
    with patch('src.common.models.price_alert.PriceAlert', TestPriceAlert), \
         patch('src.common.models.user.User', TestUser), \
         patch('src.common.models.stock_master.StockMaster', TestStockMaster), \
         patch('src.common.models.daily_price.DailyPrice', TestDailyPrice):
        yield PriceAlertService()

@pytest.fixture
def mock_redis_client():
    """Fixture to mock redis.asyncio.Redis client."""
    # Create a mock for the Redis instance with async methods
    mock_instance = AsyncMock()
    mock_instance.publish = AsyncMock()
    mock_instance.close = AsyncMock()

    # Patch redis.asyncio.Redis to return our mock_instance
    with patch('redis.asyncio.Redis', return_value=mock_instance) as mock_redis_class:
        yield mock_instance
