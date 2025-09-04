"""
User 모델 정의 파일입니다.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, BigInteger
from sqlalchemy.orm import relationship
from src.common.database.db_connector import Base
from src.common.models.price_alert import PriceAlert


class User(Base):
    """
    app_users 테이블과 매핑되는 User 모델 클래스입니다.

    Attributes:
        id (Integer): 사용자의 고유 ID.
        username (String): 사용자 이름.
        hashed_password (String): 해시된 사용자 비밀번호.
        email (String): 사용자 이메일.
        nickname (String): 사용자 닉네임.
        full_name (String): 사용자 전체 이름.
        role (String): 사용자 역할 (e.g., 'user', 'admin').
        is_active (Boolean): 계정 활성 상태.
        telegram_id (BigInteger): 텔레그램 사용자 ID.
        created_at (DateTime): 계정 생성 시간.
        updated_at (DateTime): 계정 정보 마지막 수정 시간.
        price_alerts (relationship): 사용자가 설정한 가격 알림 목록.
    """
    __tablename__ = 'app_users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(128), nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    nickname = Column(String(50), unique=True, nullable=True)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), default='user', nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Back-populates for relationships are defined in the related models
    price_alerts = relationship("PriceAlert", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', role='{self.role}')>"