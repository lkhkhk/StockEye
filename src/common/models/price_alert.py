from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.common.database.db_connector import Base

class PriceAlert(Base):
    __tablename__ = 'price_alerts'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('app_users.id'), nullable=False)
    symbol = Column(String, nullable=False)
    target_price = Column(Float)
    condition = Column(String)  # 'gte' (>=) or 'lte' (<=)
    
    # N% 이상/이하 변동률 조건
    change_percent = Column(Float, nullable=True) 
    change_type = Column(String, nullable=True) # 'up' or 'down'

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 반복 알림 설정 ('daily', 'weekly', 'monthly')
    repeat_interval = Column(String, nullable=True)

    user = relationship("User", back_populates="price_alerts")
