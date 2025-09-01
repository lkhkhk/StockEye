from sqlalchemy.orm import Session
from src.common.models.stock_master import StockMaster
import logging
from datetime import datetime

from src.common.utils.exceptions import DartApiError
from src.common.utils.dart_utils import dart_get_all_stocks

logger = logging.getLogger(__name__)

class StockMasterService:
    def get_stock_by_symbol(self, symbol: str, db: Session):
        logger.debug(f"get_stock_by_symbol 호출: symbol={symbol}")
        stock = db.query(StockMaster).filter(StockMaster.symbol == symbol).first()
        if stock:
            logger.debug(f"종목 발견: {stock.name} ({stock.symbol})")
        else:
            logger.debug(f"종목 없음: {symbol}")
        return stock

    def get_stock_by_name(self, name: str, db: Session):
        logger.debug(f"get_stock_by_name 호출: name={name}")
        stock = db.query(StockMaster).filter(StockMaster.name.like(f"%{name}%")).first()
        if stock:
            logger.debug(f"종목 발견: {stock.name} ({stock.symbol})")
        else:
            logger.debug(f"종목 없음: {name}")
        return stock

    def search_stocks(self, keyword: str, db: Session, limit: int = 10):
        logger.debug(f"search_stocks 호출: keyword={keyword}, limit={limit}")
        stocks = db.query(StockMaster).filter(
            (StockMaster.symbol.like(f"%{keyword}%")) | 
            (StockMaster.name.like(f"%{keyword}%"))
        ).limit(limit).all()
        logger.debug(f"검색 결과: {len(stocks)}개 종목 발견.")
        return stocks

    @staticmethod
    def get_sample_stocks_for_test():
        logger.debug("get_sample_stocks_for_test 호출.")
        return [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"},
            {"symbol": "000660", "name": "SK하이닉스", "market": "KOSPI"},
            {"symbol": "035420", "name": "NAVER", "market": "KOSPI"},
            {"symbol": "051910", "name": "LG화학", "market": "KOSPI"},
            {"symbol": "006400", "name": "삼성SDI", "market": "KOSPI"},
            {"symbol": "035720", "name": "카카오", "market": "KOSPI"},
            {"symbol": "207940", "name": "삼성바이오로직스", "market": "KOSPI"},
            {"symbol": "068270", "name": "셀트리온", "market": "KOSPI"},
            {"symbol": "323410", "name": "카카오뱅크", "market": "KOSPI"},
            {"symbol": "373220", "name": "LG에너지솔루션", "market": "KOSPI"}
        ]

    async def update_stock_master(self, db: Session, use_dart: bool = True):
        """DART API를 통해 전체 종목 마스터를 DB에 업데이트/삽입합니다."""
        logger.debug(f"update_stock_master 호출: use_dart={use_dart}")
        updated_count = 0
        try:
            if use_dart:
                try:
                    all_stocks = await dart_get_all_stocks()
                    logger.debug(f"DART API에서 {len(all_stocks)}개 종목 데이터 가져옴.")
                except DartApiError as e:
                    logger.error(f"DART API 연동 실패: {e}", exc_info=True)
                    return {"success": False, "error": str(e)}
            else:
                all_stocks = self.get_sample_stocks_for_test()
                logger.debug(f"샘플 데이터에서 {len(all_stocks)}개 종목 데이터 가져옴.")

            for stock_data in all_stocks:
                existing_stock = db.query(StockMaster).filter(
                    StockMaster.symbol == stock_data["symbol"]
                ).first()
                if existing_stock:
                    existing_stock.name = stock_data["name"]
                    existing_stock.market = stock_data.get("market", "")
                    existing_stock.corp_code = stock_data.get("corp_code", None)
                    existing_stock.updated_at = datetime.now()
                else:
                    now = datetime.now()
                    new_stock = StockMaster(
                        symbol=stock_data["symbol"],
                        name=stock_data["name"],
                        market=stock_data.get("market", ""),
                        corp_code=stock_data.get("corp_code", None),
                        created_at=now,
                        updated_at=now
                    )
                    db.add(new_stock)
                updated_count += 1
            db.commit()
            logger.info(f"종목마스터 갱신 완료. 총 {updated_count}개 종목 처리.")
            return {"success": True, "updated_count": updated_count}
        except Exception as e:
            db.rollback()
            logger.error(f"종목마스터 갱신 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}