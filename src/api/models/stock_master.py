from sqlalchemy import Column, String
from src.api.models.base import Base

class StockMaster(Base):
    __tablename__ = 'stock_master'
    symbol = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    market = Column(String(20), nullable=True) 