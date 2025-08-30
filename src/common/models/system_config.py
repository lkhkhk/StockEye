from sqlalchemy import Column, String, DateTime
from src.common.database.db_connector import Base
from sqlalchemy.sql import func

class SystemConfig(Base):
    __tablename__ = 'system_config'
    
    key = Column(String, primary_key=True)
    value = Column(String)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False) 