from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, BigInteger
import sqlalchemy as sa
from src.common.db_connector import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = 'app_users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    role = Column(String(20), default='user', nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    alerts = relationship("PriceAlert", back_populates="user")