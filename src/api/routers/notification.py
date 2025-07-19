from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/notifications", tags=["notifications"])

# 임시 메모리 저장소 (실제 DB 연동 전)
alert_store = []

class PriceAlertRequest(BaseModel):
    user_id: int
    symbol: str
    target_price: float
    is_above: bool

class PriceAlertResponse(BaseModel):
    alert_id: int
    message: str

class AlertHistoryResponse(BaseModel):
    alert_id: int
    user_id: int
    symbol: str
    target_price: float
    is_above: bool

@router.post("/alerts/price", response_model=PriceAlertResponse)
def create_price_alert(alert: PriceAlertRequest):
    alert_id = len(alert_store) + 1
    alert_data = alert.dict()
    alert_data["alert_id"] = alert_id
    alert_store.append(alert_data)
    return {"alert_id": alert_id, "message": "알림이 등록되었습니다."}

@router.get("/history/{user_id}", response_model=List[AlertHistoryResponse])
def get_alert_history(user_id: int):
    return [a for a in alert_store if a["user_id"] == user_id] 