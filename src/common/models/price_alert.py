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
    
    # 공시 알림 여부
    notify_on_disclosure = Column(Boolean, default=False, nullable=False)
    
    # 알림 주기 및 이력 관리
    notification_interval_hours = Column(Integer, nullable=False, default=24)  # 알림 주기 (시간 단위)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)  # 마지막 알림 전송 시간
    notification_count = Column(Integer, default=0, nullable=False)  # 알림 전송 횟수

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 반복 알림 설정 ('daily', 'weekly', 'monthly')
    repeat_interval = Column(String, nullable=True)

    user = relationship("User", back_populates="price_alerts")
    stock = relationship("StockMaster", foreign_keys=[symbol], primaryjoin="PriceAlert.symbol == StockMaster.symbol")

    @property
    def stock_name(self):
        return self.stock.name if self.stock else None

