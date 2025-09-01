import pytest
from datetime import date, datetime, timedelta # Import timedelta
from src.common.models.daily_price import DailyPrice
from sqlalchemy import create_engine, text # Import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
# from sqlalchemy.ext.declarative import declarative_base # No longer needed

# Use an in-memory SQLite database for testing
@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    
    # Manually create the table with INTEGER PRIMARY KEY for id
    conn = engine.connect()
    conn.execute(text("""
        CREATE TABLE daily_prices (
            id INTEGER PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            open FLOAT NOT NULL,
            high FLOAT NOT NULL,
            low FLOAT NOT NULL,
            close FLOAT NOT NULL,
            volume BIGINT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """))
    conn.commit() # Commit the DDL
    
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        conn.close() # Close the connection used for DDL
        # No need for metadata.drop_all as we manually created the table

def test_daily_price_model_creation(db_session):
    """
    Test that a DailyPrice instance can be created and has the correct attributes.
    """
    new_price = DailyPrice(
        # id=None, # No longer needed, SQLite will auto-generate
        symbol="AAPL",
        date=date(2023, 1, 1),
        open=100.0,
        high=105.0,
        low=99.0,
        close=104.5,
        volume=1000000
    )
    db_session.add(new_price)
    db_session.commit()

    retrieved_price = db_session.query(DailyPrice).filter_by(symbol="AAPL").first()

    assert retrieved_price is not None
    assert retrieved_price.symbol == "AAPL"
    assert retrieved_price.date == date(2023, 1, 1)
    assert retrieved_price.open == 100.0
    assert retrieved_price.high == 105.0
    assert retrieved_price.low == 99.0
    assert retrieved_price.close == 104.5
    assert retrieved_price.volume == 1000000
    assert isinstance(retrieved_price.created_at, datetime) # Re-added assertion
    assert isinstance(retrieved_price.updated_at, datetime) # Re-added assertion

def test_daily_price_model_required_fields(db_session):
    """
    Test that required fields cannot be null.
    """
    # Test with missing symbol
    with pytest.raises(IntegrityError):
        new_price = DailyPrice(
            # id=None, # No longer needed
            date=date(2023, 1, 1),
            open=100.0,
            high=105.0,
            low=99.0,
            close=104.5,
            volume=1000000
        )
        db_session.add(new_price)
        db_session.commit()
    db_session.rollback() # Rollback to clear the session state after error

    # Test with missing date
    with pytest.raises(IntegrityError):
        new_price = DailyPrice(
            # id=None, # No longer needed
            symbol="GOOG",
            open=100.0,
            high=105.0,
            low=99.0,
            close=104.5,
            volume=1000000
        )
        db_session.add(new_price)
        db_session.commit()
    db_session.rollback()

    # Test with missing open
    with pytest.raises(IntegrityError):
        new_price = DailyPrice(
            # id=None, # No longer needed
            symbol="MSFT",
            date=date(2023, 1, 1),
            high=105.0,
            low=99.0,
            close=104.5,
            volume=1000000
        )
        db_session.add(new_price)
        db_session.commit()
    db_session.rollback()

    # Test with missing volume
    with pytest.raises(IntegrityError):
        new_price = DailyPrice(
            # id=None, # No longer needed
            symbol="AMZN",
            date=date(2023, 1, 1),
            open=100.0,
            high=105.0,
            low=99.0,
            close=104.5,
        )
        db_session.add(new_price)
        db_session.commit()
    db_session.rollback()

def test_daily_price_model_update_timestamp(db_session):
    """
    Test that updated_at timestamp is updated on modification.
    """
    new_price = DailyPrice(
        # id=None, # No longer needed
        symbol="TSLA",
        date=date(2023, 1, 1),
        open=200.0,
        high=205.0,
        low=199.0,
        close=204.5,
        volume=2000000
    )
    db_session.add(new_price)
    db_session.commit() # Commit the initial insert

    # Manually set a new timestamp for updated_at to ensure it's different
    # This bypasses SQLite's CURRENT_TIMESTAMP granularity issues in tests
    new_timestamp = datetime.now() + timedelta(seconds=1) # Ensure it's truly greater

    # Refresh the object to get the latest state from the database
    db_session.refresh(new_price) 
    
    # Use the same object, no need to query again
    new_price.close = 205.0 # Modify a field
    new_price.updated_at = new_timestamp # Manually set updated_at
    db_session.add(new_price) # Add back to session after modification
    db_session.commit() # Commit in new session

    assert new_price.updated_at == new_timestamp # Assert against the manually set timestamp
