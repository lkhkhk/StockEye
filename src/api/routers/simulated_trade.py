# 각 엔드포인트에 tags를 명시적으로 지정해야 Swagger UI에서 그룹화가 100% 보장됩니다.
# (FastAPI 라우터의 tags만으로는 일부 환경에서 그룹화가 누락될 수 있음)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.common.schemas.simulated_trade import SimulatedTradeItem
from src.common.models.simulated_trade import SimulatedTrade
from src.common.services.market_data_service import MarketDataService
from src.api.services.user_service import UserService # UserService 임포트
from src.common.database.db_connector import get_db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trade", tags=["simulated_trade"])

def get_market_data_service():
    return MarketDataService()

def get_user_service(): # UserService 의존성 주입 함수 추가
    return UserService()

@router.post("/simulate", tags=["simulated_trade"])
def simulate_trade(trade: SimulatedTradeItem, db: Session = Depends(get_db), market_data_service: MarketDataService = Depends(get_market_data_service), user_service: UserService = Depends(get_user_service)): # user_service 추가
    """모의매매 기록"""
    logger.debug(f"simulate_trade 호출: user_id={trade.user_id}, symbol={trade.symbol}, trade_type={trade.trade_type}")
    try:
        # 사용자 존재 여부 확인
        user = user_service.get_user_by_id(db, trade.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 현재가 조회 (실제로는 외부 API에서 가져옴)
        current_price = market_data_service.get_current_price_and_change(trade.symbol, db)['current_price']
        logger.debug(f"종목 {trade.symbol}의 현재가: {current_price}")
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
                logger.debug(f"매도 거래 수익률 계산: profit_loss={profit_loss}, profit_rate={profit_rate}")
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
        logger.info(f"모의매매 기록 완료: user_id={trade.user_id}, symbol={trade.symbol}, trade_type={trade.trade_type}")
        return {"message": "모의매매 기록 완료"}
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"모의매매 기록 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"모의매매 기록 실패: {str(e)}")

@router.get("/history/{user_id}", tags=["simulated_trade"])
def get_trade_history(user_id: int, db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service)): # user_service 추가
    """사용자의 모의매매 이력 조회"""
    logger.debug(f"get_trade_history 호출: user_id={user_id}")
    # 사용자 존재 여부 확인
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    trades = db.query(SimulatedTrade).filter(
        SimulatedTrade.user_id == user_id
    ).order_by(SimulatedTrade.trade_time.desc()).all()
    
    logger.debug(f"사용자({user_id})의 모의매매 이력 {len(trades)}건 조회됨.")
    # 수익률 통계 계산
    total_profit_loss = sum(t.profit_loss or 0 for t in trades if t.profit_loss is not None)
    total_trades = len(trades)
    profitable_trades = len([t for t in trades if t.profit_loss and t.profit_loss > 0])
    
    statistics = {
        "total_trades": total_trades,
        "total_profit_loss": total_profit_loss,
        "profitable_trades": profitable_trades,
        "win_rate": (profitable_trades / total_trades * 100) if total_trades > 0 else 0
    }
    logger.debug(f"모의매매 통계: {statistics}")

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
        "statistics": statistics
    }