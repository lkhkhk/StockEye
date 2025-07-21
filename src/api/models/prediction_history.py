from sqlalchemy import Column, BigInteger, String, Float, DateTime, ForeignKey, func
from src.common.db_connector import Base
from datetime import datetime

class PredictionHistory(Base):
    __tablename__ = 'prediction_history'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    symbol = Column(String(20), nullable=False)
    prediction = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False) 
