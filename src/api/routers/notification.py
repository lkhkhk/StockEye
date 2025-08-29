from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from src.common.db_connector import get_db
from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertRead, PriceAlertUpdate
from src.common.services.price_alert_service import PriceAlertService
from src.api.auth.jwt_handler import get_current_active_user
from src.api.services.user_service import UserService
from typing import List
from src.common.models.price_alert import PriceAlert
from src.common.models.user import User # User 모델 임포트 추가
from src.common.notify_service import send_telegram_message

router = APIRouter(prefix="/alerts", tags=["notification"])

def get_price_alert_service():
    return PriceAlertService()

from src.api.services.user_service import UserService

# ... (기존 임포트)

def get_user_service():
    return UserService()

@router.post("/", response_model=PriceAlertRead)
async def create_alert(alert: PriceAlertCreate, db: Session = Depends(get_db), alert_service: PriceAlertService = Depends(get_price_alert_service), user_service: UserService = Depends(get_user_service)):
    print(f"Creating alert with payload: {alert}")
    user = user_service.get_user_by_telegram_id(db, alert.telegram_id)
    if not user:
        # 사용자가 없으면 생성
        user = user_service.create_user_from_telegram(
            db,
            telegram_id=alert.telegram_id,
            username=f"tg_{alert.telegram_id}",
            first_name="Telegram",
            last_name="User"
        )

    result = await alert_service.create_alert(db, user_id=user.id, alert=alert)
    return PriceAlertRead.model_validate(result)

@router.get("/{telegram_id}", response_model=List[PriceAlertRead])
def get_my_alerts(telegram_id: int, db: Session = Depends(get_db), alert_service: PriceAlertService = Depends(get_price_alert_service), user_service: UserService = Depends(get_user_service)):
    """내 가격 알림 목록 조회 (봇 내부용)"""
    user = user_service.get_user_by_telegram_id(db, telegram_id)
    if not user:
        return [] # 사용자가 없으면 빈 목록 반환

    results = alert_service.get_alerts(db, user_id=user.id)
    return [PriceAlertRead.model_validate(r) for r in results]

@router.get("/user/{user_id}/symbol/{symbol}", response_model=PriceAlertRead)
def get_alert_by_user_and_symbol(user_id: int, symbol: str, db: Session = Depends(get_db), alert_service: PriceAlertService = Depends(get_price_alert_service)):
    """사용자 ID와 종목코드로 특정 알림 조회 (봇 내부용)"""
    alert = alert_service.get_alert_by_user_and_symbol(db, user_id=user_id, symbol=symbol)
    if not alert:
        raise HTTPException(status_code=404, detail="해당 종목에 대한 알림 설정을 찾을 수 없습니다.")
    return alert


@router.put("/{telegram_id}/{symbol}", response_model=PriceAlertRead)
async def update_alert(telegram_id: int, symbol: str, alert_update: PriceAlertUpdate, db: Session = Depends(get_db), alert_service: PriceAlertService = Depends(get_price_alert_service), user_service: UserService = Depends(get_user_service)):
    """가격 알림 수정 (봇 내부용)"""
    user = user_service.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    alert = alert_service.get_alert_by_user_and_symbol(db, user_id=user.id, symbol=symbol)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    updated_alert = await alert_service.update_alert(db, alert.id, alert_update)
    return PriceAlertRead.model_validate(updated_alert)

@router.delete("/{telegram_id}/{symbol}")
async def delete_alert(telegram_id: int, symbol: str, db: Session = Depends(get_db), alert_service: PriceAlertService = Depends(get_price_alert_service), user_service: UserService = Depends(get_user_service)):
    """가격 알림 삭제 (봇 내부용)"""
    user = user_service.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    alert = alert_service.get_alert_by_user_and_symbol(db, user_id=user.id, symbol=symbol)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    await alert_service.delete_alert(db, alert.id)
    return {"result": True}

@router.post("/test_notify")
async def test_notify_api(chat_id: int = Body(...), text: str = Body("[API 테스트] 공시 알림 테스트 메시지입니다.")):
    """(관리자 테스트용) chat_id로 텔레그램 메시지 전송 테스트"""
    try:
        await send_telegram_message(chat_id, text)
        return {"result": True, "message": "메시지 전송 성공"}
    except Exception as e:
        return {"result": False, "error": str(e)} 