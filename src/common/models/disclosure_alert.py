"""
DisclosureAlert 모델 정의 파일입니다.
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from src.common.database.db_connector import Base
from src.common.models.user import User

class DisclosureAlert(Base):
    """
    disclosure_alerts 테이블과 매핑되는 DisclosureAlert 모델 클래스입니다.

    Attributes:
        id (Integer): 알림의 고유 ID.
        user_id (Integer): 알림을 설정한 사용자의 ID.
        symbol (String): 종목 코드.
        is_active (Boolean): 알림 활성 상태.
        created_at (DateTime): 알림 생성 시간.
        updated_at (DateTime): 알림 마지막 수정 시간.
        user (relationship): 알림을 설정한 사용자.
    """
    __tablename__ = 'disclosure_alerts'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('app_users.id'), nullable=False)
    symbol = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="disclosure_alerts")

# User 모델에 disclosure_alerts relationship 추가
User.disclosure_alerts = relationship("DisclosureAlert", order_by=DisclosureAlert.id, back_populates="user")