from sqlalchemy import Column, String, DateTime, Float, BigInteger, Date, func
from src.common.database.db_connector import Base

class DailyPrice(Base):
    __tablename__ = 'daily_prices'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False) 