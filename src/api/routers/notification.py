from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from src.common.db_connector import get_db
from src.api.schemas.price_alert import PriceAlertCreate, PriceAlertRead, PriceAlertUpdate
from src.api.services.price_alert_service import PriceAlertService
from src.api.auth.jwt_handler import get_current_active_user
from typing import List
from src.api.models.price_alert import PriceAlert
from src.api.models.user import User # User 모델 임포트 추가
from src.common.notify_service import send_telegram_message

router = APIRouter(prefix="/alerts", tags=["notification"])

def get_price_alert_service():
    return PriceAlertService()

@router.post("/", response_model=PriceAlertRead)
def create_alert(alert: PriceAlertCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db), alert_service: PriceAlertService = Depends(get_price_alert_service)):
    """가격 알림 생성"""
    result = alert_service.create_alert(db, user_id=current_user.id, alert=alert)
    return PriceAlertRead.model_validate(result)

@router.get("/", response_model=List[PriceAlertRead])
def get_my_alerts(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db), alert_service: PriceAlertService = Depends(get_price_alert_service)):
    """내 가격 알림 목록 조회"""
    results = alert_service.get_alerts(db, user_id=current_user.id)
    return [PriceAlertRead.model_validate(r) for r in results]

@router.get("/user/{user_id}/symbol/{symbol}", response_model=PriceAlertRead)
def get_alert_by_user_and_symbol(user_id: int, symbol: str, db: Session = Depends(get_db), alert_service: PriceAlertService = Depends(get_price_alert_service)):
    """사용자 ID와 종목코드로 특정 알림 조회 (봇 내부용)"""
    alert = alert_service.get_alert_by_user_and_symbol(db, user_id=user_id, symbol=symbol)
    if not alert:
        raise HTTPException(status_code=404, detail="해당 종목에 대한 알림 설정을 찾을 수 없습니다.")
    return alert


@router.put("/{alert_id}", response_model=PriceAlertRead)
def update_alert(alert_id: int, alert_update: PriceAlertUpdate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db), alert_service: PriceAlertService = Depends(get_price_alert_service)):
    """가격 알림 수정"""
    alert = alert_service.update_alert(db, alert_id, alert_update)
    if alert.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한 없음")
    return PriceAlertRead.model_validate(alert)

@router.delete("/{alert_id}")
def delete_alert(alert_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db), alert_service: PriceAlertService = Depends(get_price_alert_service)):
    """가격 알림 삭제"""
    alert = db.query(PriceAlert).filter_by(id=alert_id).first()
    if alert and alert.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한 없음")
    alert_service.delete_alert(db, alert_id)
    return {"result": True}

@router.post("/test_notify")
async def test_notify_api(chat_id: int = Body(...), text: str = Body("[API 테스트] 공시 알림 테스트 메시지입니다.")):
    """(관리자 테스트용) chat_id로 텔레그램 메시지 전송 테스트"""
    try:
        await send_telegram_message(chat_id, text)
        return {"result": True, "message": "메시지 전송 성공"}
    except Exception as e:
        return {"result": False, "error": str(e)} 