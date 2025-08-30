import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.common.services.price_alert_service import PriceAlertService
from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
from src.common.models.price_alert import PriceAlert
from src.common.models.daily_price import DailyPrice
import redis.asyncio as redis
import json
import asyncio
from src.common.models.user import User
from src.common.models.stock_master import StockMaster
from datetime import date, timedelta

# Fixture for PriceAlertService instance
@pytest.fixture
def price_alert_service():
    return PriceAlertService()

# Fixture for a mock database session
@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

# --- Integration Test for Redis Publish ---

REDIS_HOST = "stockeye-redis"
REDIS_PORT = 6379

@pytest.mark.asyncio
async def test_check_price_alerts_publishes_to_redis_on_trigger(price_alert_service, real_db):
    """알림 조건 충족 시 check_price_alerts가 Redis에 메시지를 발행하는지 통합 테스트"""
    # 1. Redis 구독 클라이언트 설정
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("notifications")
    await asyncio.sleep(0.1)

    # 2. Given: 테스트 데이터 설정
    # 사용자 생성
    test_user = User(id=1, username="testuser", email="test@example.com", telegram_id="12345", password_hash="hashed_password")
    real_db.add(test_user)

    # 주식 마스터 생성
    stock = StockMaster(symbol="005930", name="삼성전자", market="KOSPI")
    real_db.add(stock)
    real_db.commit() # User와 StockMaster를 먼저 커밋

    # 가격 알림 생성 (80,000원 이상이면 알림)
    alert = PriceAlert(user_id=test_user.id, symbol=stock.symbol, target_price=80000, condition="gte", is_active=True)
    real_db.add(alert)
    real_db.commit() # PriceAlert를 나중에 커밋

    # 3. When: 알림 조건 충족 및 서비스 메소드 호출
    # 새로운 가격 정보 추가 (81,000원)
    new_price = DailyPrice(symbol=stock.symbol, date=date.today(), open=80000, high=82000, low=79000, close=81000, volume=1000000)
    real_db.add(new_price)
    real_db.commit()

    # 서비스 메소드 호출
    await price_alert_service.check_and_notify_price_alerts(real_db)

    # 4. Then: 결과 검증
    # Redis 메시지 확인
    message = await pubsub.get_message(timeout=1)
    # Redis 제어 메시지(예: subscribe 확인)를 건너뛰고 실제 메시지를 찾습니다.
    while message and message['type'] != 'message':
        message = await pubsub.get_message(timeout=1)

    assert message is not None, "Redis 채널에서 메시지를 수신하지 못했습니다."
    assert message['channel'] == 'notifications'
    data = json.loads(message['data'])
    assert data['chat_id'] == str(test_user.telegram_id)
    assert "목표 가격 도달: 005930 80000.0 gte (현재가: 81000.0)" in data['text']
    assert "81000.0" in data['text']

    # DB 상태 확인 (알림이 비활성화되었는지)
    triggered_alert = real_db.query(PriceAlert).filter(PriceAlert.id == alert.id).first()
    assert triggered_alert.is_active is False

    # 5. Clean up
    await pubsub.unsubscribe()
    await redis_client.close()
