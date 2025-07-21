from sqlalchemy import Column, BigInteger, String, Float, DateTime, ForeignKey, func, Integer
from src.common.db_connector import Base
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
    profit_loss = Column(Float, nullable=True)  # 수익/손실
    profit_rate = Column(Float, nullable=True)  # 수익률 (%)
    current_price = Column(Float, nullable=True)  # 현재가
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False) 
