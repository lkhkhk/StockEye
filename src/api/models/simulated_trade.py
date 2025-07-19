from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from src.api.models.base import Base
from datetime import datetime

class SimulatedTrade(Base):
    __tablename__ = 'simulated_trades'
    trade_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    symbol = Column(String(20), nullable=False)
    trade_type = Column(String(10), nullable=False)  # 'buy' or 'sell'
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    trade_time = Column(DateTime, default=datetime.utcnow) 