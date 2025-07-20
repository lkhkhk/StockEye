from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, func
from src.api.models.base import Base

class User(Base):
    __tablename__ = 'app_users'
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    role = Column(String(20), default='user', nullable=False)  # 'user' or 'admin'
    is_active = Column(Boolean, default=True, nullable=False)
    telegram_id = Column(String(50), unique=True, nullable=True)  # 텔레그램 ID
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False) 