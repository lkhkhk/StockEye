import pytest
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
from datetime import datetime, timedelta

from src.api.models.user import User
from src.api.models.stock_master import StockMaster
from src.api.models.price_alert import PriceAlert # Import PriceAlert model
from src.api.models.daily_price import DailyPrice # Import DailyPrice model

# Database connection
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
    """Cleans up the database before each test function."""
    print("Cleaning up database...")
    db = SessionLocal()
    try:
        db.query(PriceAlert).delete()
        db.query(User).delete()
        db.query(StockMaster).delete()
        db.query(DailyPrice).delete() # Add DailyPrice cleanup
        db.commit()
    finally:
        db.close()
    print("Database cleaned up.")

def test_seed_data():
    """Seeds the database with a test user, stock symbol, and daily price data."""
    db = SessionLocal()
    try:
        # Create user
        user = User(
            username="testuser_12345",
            password_hash="testpassword", # In a real app, this would be a hash
            email="testuser_12345@example.com",
            telegram_id=12345
        )
        db.add(user)

        # Create stock symbol
        stock = StockMaster(
            symbol="005930",
            name="Samsung Electronics",
            market="KOSPI"
        )
        db.add(stock)

        # Create 40 days of DailyPrice data
        today = datetime.utcnow().date()
        for i in range(40):
            # Insert dates from today backwards for 40 days
            past_date = today - timedelta(days=i)
            price = 100.0 + i # Dummy price data
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
    finally:
        db.close()
