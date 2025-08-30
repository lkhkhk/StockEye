from sqlalchemy import Column, String, DateTime, BigInteger, func
from src.common.database.db_connector import Base

class Disclosure(Base):
    __tablename__ = 'disclosures'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, index=True)  # 6자리 종목코드
    corp_code = Column(String(20), nullable=False, index=True)   # DART 고유번호
    title = Column(String(200), nullable=False)
    rcept_no = Column(String(20), nullable=False, unique=True)   # DART 접수번호(공시 고유)
    disclosed_at = Column(DateTime, nullable=False, index=True)  # 공시 일시
    url = Column(String(300), nullable=False)
    disclosure_type = Column(String(200), nullable=True)          # 보고서 유형 등
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)