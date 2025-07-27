from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Float, ForeignKey, func, Integer
from src.common.db_connector import Base
from sqlalchemy.orm import relationship

class PriceAlert(Base):
    __tablename__ = 'price_alerts'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('app_users.id'), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    target_price = Column(Float, nullable=True) # 공시 알림만 원하는 경우 Null 허용
    condition = Column(String(10), nullable=True)  # 'gte'(이상), 'lte'(이하)
    change_percent = Column(Float, nullable=True) # N% 변동률
    change_type = Column(String(10), nullable=True) # 'up', 'down' (변동률 조건과 함께 사용)
    notify_on_disclosure = Column(Boolean, default=False, nullable=False) # 공시 알림 수신 여부
    repeat_interval = Column(String(20), nullable=True) # 반복 알림 주기 (예: 'daily', 'weekly', None)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)