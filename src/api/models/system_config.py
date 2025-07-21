from sqlalchemy import Column, String, DateTime
from src.common.db_connector import Base
from sqlalchemy.sql import func

class SystemConfig(Base):
    __tablename__ = 'system_config'
    
    key = Column(String, primary_key=True)
    value = Column(String)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now()) 