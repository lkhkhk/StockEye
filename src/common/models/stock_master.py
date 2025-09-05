from sqlalchemy import Column, String, DateTime, Boolean 
from src.common.database.db_connector import Base
from sqlalchemy.sql import func

class StockMaster(Base):
    __tablename__ = 'stock_master'
    symbol = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    market = Column(String(20), nullable=True)
    corp_code = Column(String(20), nullable=True, index=True)
    is_delisted = Column(Boolean, default=False, nullable=False) 
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)