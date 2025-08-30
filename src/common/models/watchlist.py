from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime, func
from src.common.database.db_connector import Base
from sqlalchemy.orm import relationship

class Watchlist(Base):
    __tablename__ = 'watch_list'
    user_id = Column(BigInteger, primary_key=True)
    symbol = Column(String(20), primary_key=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False) 