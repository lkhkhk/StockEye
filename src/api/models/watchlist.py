from sqlalchemy import Column, Integer, String, BigInteger, DateTime, func
from src.api.models.base import Base

class WatchList(Base):
    __tablename__ = 'watch_list'
    user_id = Column(BigInteger, primary_key=True)
    symbol = Column(String(20), primary_key=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False) 