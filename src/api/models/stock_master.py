from sqlalchemy import Column, String, DateTime, func
from src.api.models.base import Base

class StockMaster(Base):
    __tablename__ = 'stock_master'
    symbol = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    market = Column(String(20), nullable=True)
    corp_code = Column(String(20), nullable=True, index=True)  # DART 고유번호
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False) 