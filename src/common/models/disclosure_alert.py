from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.common.database.db_connector import Base

class DisclosureAlert(Base):
    __tablename__ = 'disclosure_alerts'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('app_users.id'), nullable=False)
    symbol = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="disclosure_alerts")
