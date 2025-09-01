from sqlalchemy.orm import Session
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice
import yfinance as yf
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MarketDataService:
    def get_current_price_and_change(self, symbol: str, db: Session):
        logger.debug(f"get_current_price_and_change 호출: symbol={symbol}")
        
        prices = db.query(DailyPrice).filter(
            DailyPrice.symbol == symbol
        ).order_by(DailyPrice.date.desc()).limit(2).all()
        
        current_price = None
        previous_close = None
        
        if prices:
            current_price = prices[0].close
            logger.debug(f"현재가 발견: {symbol} - {current_price}")
            
            if len(prices) > 1:
                previous_close = prices[1].close
                logger.debug(f"전일 종가 발견: {symbol} - {previous_close}")
            else:
                logger.warning(f"전일 종가 없음: {symbol}. 등락률 계산 불가.")
        else:
            logger.warning(f"현재가 없음: {symbol}.")
            
        change = None
        change_rate = None

        if current_price is not None and previous_close is not None:
            change = current_price - previous_close
            if previous_close != 0:
                change_rate = (change / previous_close) * 100
            else:
                change_rate = 0.0
        
        return {
            "current_price": current_price,
            "change": change,
            "change_rate": change_rate
        }

    def get_daily_prices(self, symbol: str, db: Session, days: int = 30):
        logger.debug(f"get_daily_prices 호출: symbol={symbol}, days={days}")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        prices = db.query(DailyPrice).filter(
            DailyPrice.symbol == symbol,
            DailyPrice.date >= start_date,
            DailyPrice.date <= end_date
        ).order_by(DailyPrice.date.desc()).all()
        logger.debug(f"일별 시세 발견: {symbol} - {len(prices)}개 데이터.")
        return prices

    async def update_daily_prices(self, db: Session):
        """실제 주식 시세 API를 통해 일별시세 갱신 (모든 종목 대상)"""
        logger.debug("update_daily_prices 호출.")
        updated_count = 0
        error_stocks = []
        batch_size = 100
        offset = 0
        
        try:
            while True:
                stocks_batch = db.query(StockMaster).offset(offset).limit(batch_size).all()
                if not stocks_batch:
                    break

                logger.debug(f"DB에서 {len(stocks_batch)}개 종목 (offset: {offset}) 가져옴.")
                prices_to_add = []

                for stock in stocks_batch:
                    logger.debug(f"종목 {stock.symbol} ({stock.name}) 일별시세 갱신 시작.")
                    try:
                        ticker = f"{stock.symbol}.KS"
                        data = yf.download(ticker, start=datetime.now() - timedelta(days=30), end=datetime.now())
                        
                        if data.empty:
                            logger.warning(f"종목 {stock.symbol} ({ticker})에 대한 일별시세 데이터가 없습니다.")
                            error_stocks.append(stock.symbol)
                            continue

                        for index, row in data.iterrows():
                            target_date = index.date()
                            
                            existing_price = db.query(DailyPrice).filter(
                                DailyPrice.symbol == stock.symbol,
                                DailyPrice.date == target_date
                            ).first()
                            
                            if not existing_price:
                                new_price = DailyPrice(
                                    symbol=stock.symbol,
                                    date=target_date,
                                    open=float(row['Open']),
                                    high=float(row['High']),
                                    low=float(row['Low']),
                                    close=float(row['Close']),
                                    volume=int(row['Volume'])
                                )
                                prices_to_add.append(new_price)
                                updated_count += 1
                    except Exception as e:
                        logger.error(f"일별시세 갱신 중 '{stock.symbol}' 처리에서 오류 발생: {e}")
                        error_stocks.append(stock.symbol)
                
                if prices_to_add:
                    db.bulk_save_objects(prices_to_add)
                    db.commit()
                    logger.info(f"배치 처리 완료: {len(prices_to_add)}개 일별시세 데이터 삽입.")
                else:
                    db.rollback()

                offset += batch_size

            logger.info(f"일별시세 갱신 완료. 총 {updated_count}개 데이터 처리. 오류: {len(error_stocks)}개 종목")
            return {"success": True, "updated_count": updated_count, "errors": error_stocks}
        except Exception as e:
            db.rollback()
            logger.error(f"일별시세 갱신 작업 전체 실패: {e}", exc_info=True)
            return {"success": False, "error": f"일별시세 갱신 중 심각한 오류 발생: {e}"}