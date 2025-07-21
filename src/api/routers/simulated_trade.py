# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.api.schemas.simulated_trade import SimulatedTradeItem
from src.api.models.simulated_trade import SimulatedTrade
from src.api.services.stock_service import StockService
from src.common.db_connector import get_db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trade", tags=["simulated_trade"])
stock_service = StockService()

@router.post("/simulate", tags=["simulated_trade"])
def simulate_trade(trade: SimulatedTradeItem, db: Session = Depends(get_db)):
    """모의매매 기록"""
    try:
        # 현재가 조회 (실제로는 외부 API에서 가져옴)
        current_price = stock_service.get_current_price(trade.symbol, db)
        # 수익률 계산
        profit_loss = None
        profit_rate = None
        if trade.trade_type == "sell":
            # 매도 시 수익률 계산
            # 이전 매수 기록을 찾아서 계산
            buy_trade = db.query(SimulatedTrade).filter(
                SimulatedTrade.user_id == trade.user_id,
                SimulatedTrade.symbol == trade.symbol,
                SimulatedTrade.trade_type == "buy"
            ).order_by(SimulatedTrade.trade_time.desc()).first()
            if buy_trade:
                profit_loss = (trade.price - buy_trade.price) * trade.quantity
                profit_rate = ((trade.price - buy_trade.price) / buy_trade.price) * 100
        # 모의매매 기록 생성
        simulated_trade = SimulatedTrade(
            user_id=trade.user_id,
            symbol=trade.symbol,
            trade_type=trade.trade_type,
            price=trade.price,
            quantity=trade.quantity,
            trade_time=datetime.utcnow(),
            profit_loss=profit_loss,
            profit_rate=profit_rate,
            current_price=current_price
        )
        db.add(simulated_trade)
        db.commit()
        return {"message": "모의매매 기록 완료"}
    except Exception as e:
        db.rollback()
        logger.error(f"모의매매 기록 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"모의매매 기록 실패: {str(e)}")

@router.get("/history/{user_id}", tags=["simulated_trade"])
def get_trade_history(user_id: int, db: Session = Depends(get_db)):
    """사용자의 모의매매 이력 조회"""
    trades = db.query(SimulatedTrade).filter(
        SimulatedTrade.user_id == user_id
    ).order_by(SimulatedTrade.trade_time.desc()).all()
    
    # 수익률 통계 계산
    total_profit_loss = sum(t.profit_loss or 0 for t in trades if t.profit_loss is not None)
    total_trades = len(trades)
    profitable_trades = len([t for t in trades if t.profit_loss and t.profit_loss > 0])
    
    return {
        "trades": [
            {
                "trade_id": t.trade_id,
                "symbol": t.symbol,
                "trade_type": t.trade_type,
                "price": t.price,
                "quantity": t.quantity,
                "trade_time": t.trade_time,
                "profit_loss": t.profit_loss,
                "profit_rate": t.profit_rate,
                "current_price": t.current_price
            } for t in trades
        ],
        "statistics": {
            "total_trades": total_trades,
            "total_profit_loss": total_profit_loss,
            "profitable_trades": profitable_trades,
            "win_rate": (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        }
    } 