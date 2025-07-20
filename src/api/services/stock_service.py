from sqlalchemy.orm import Session
from src.api.models.stock_master import StockMaster
from src.api.models.daily_price import DailyPrice
from src.api.db import get_db
import logging
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

class StockService:
    def __init__(self):
        pass

    def get_stock_by_symbol(self, symbol: str, db: Session):
        """종목코드로 종목 정보 조회"""
        return db.query(StockMaster).filter(StockMaster.symbol == symbol).first()

    def get_stock_by_name(self, name: str, db: Session):
        """종목명으로 종목 정보 조회"""
        return db.query(StockMaster).filter(StockMaster.name.like(f"%{name}%")).first()

    def search_stocks(self, keyword: str, db: Session, limit: int = 10):
        """종목 검색 (종목코드 또는 종목명)"""
        return db.query(StockMaster).filter(
            (StockMaster.symbol.like(f"%{keyword}%")) | 
            (StockMaster.name.like(f"%{keyword}%"))
        ).limit(limit).all()

    def get_current_price(self, symbol: str, db: Session):
        """종목의 현재가 조회 (실제로는 외부 API에서 가져옴)"""
        # 최신 일별시세 데이터에서 현재가 조회
        latest_price = db.query(DailyPrice).filter(
            DailyPrice.symbol == symbol
        ).order_by(DailyPrice.date.desc()).first()
        
        if latest_price:
            return latest_price.close_price
        else:
            # 데이터가 없으면 임시 가격 생성
            return random.randint(50000, 200000)

    def get_daily_prices(self, symbol: str, db: Session, days: int = 30):
        """종목의 일별 시세 조회"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return db.query(DailyPrice).filter(
            DailyPrice.symbol == symbol,
            DailyPrice.date >= start_date,
            DailyPrice.date <= end_date
        ).order_by(DailyPrice.date.desc()).all()

    def update_stock_master(self, db: Session):
        """종목마스터 정보 갱신"""
        try:
            logger.info("종목마스터 갱신 시작")
            
            # 기존 종목 목록 (실제로는 외부 API에서 가져옴)
            sample_stocks = [
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
            
            updated_count = 0
            for stock_data in sample_stocks:
                existing_stock = db.query(StockMaster).filter(
                    StockMaster.symbol == stock_data["symbol"]
                ).first()
                
                if existing_stock:
                    # 기존 종목 정보 업데이트
                    existing_stock.name = stock_data["name"]
                    existing_stock.market = stock_data["market"]
                    existing_stock.updated_at = datetime.now()
                else:
                    # 새 종목 추가
                    new_stock = StockMaster(
                        symbol=stock_data["symbol"],
                        name=stock_data["name"],
                        market=stock_data["market"],
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(new_stock)
                
                updated_count += 1
            
            db.commit()
            logger.info(f"종목마스터 갱신 완료: {updated_count}개 종목 처리")
            return {"success": True, "updated_count": updated_count}
            
        except Exception as e:
            logger.error(f"종목마스터 갱신 실패: {str(e)}")
            db.rollback()
            return {"success": False, "error": str(e)}

    def update_daily_prices(self, db: Session):
        """일별시세 갱신"""
        try:
            logger.info("일별시세 갱신 시작")
            
            # 모든 종목 조회
            stocks = db.query(StockMaster).all()
            updated_count = 0
            
            for stock in stocks:
                # 최근 30일간의 일별시세 생성/갱신
                for i in range(30):
                    target_date = datetime.now() - timedelta(days=i)
                    
                    # 해당 날짜의 기존 데이터 확인
                    existing_price = db.query(DailyPrice).filter(
                        DailyPrice.symbol == stock.symbol,
                        DailyPrice.date == target_date.date()
                    ).first()
                    
                    if not existing_price:
                        # 새로운 일별시세 데이터 생성
                        base_price = random.randint(50000, 200000)  # 기본 가격
                        price_change = random.randint(-5000, 5000)  # 가격 변동
                        
                        new_price = DailyPrice(
                            symbol=stock.symbol,
                            date=target_date.date(),
                            open=base_price,
                            high=base_price + random.randint(0, 3000),
                            low=base_price - random.randint(0, 3000),
                            close=base_price + price_change,
                            volume=random.randint(1000000, 10000000),
                            created_at=datetime.now()
                        )
                        db.add(new_price)
                        updated_count += 1
            
            db.commit()
            logger.info(f"일별시세 갱신 완료: {updated_count}개 데이터 처리")
            return {"success": True, "updated_count": updated_count}
            
        except Exception as e:
            logger.error(f"일별시세 갱신 실패: {str(e)}")
            db.rollback()
            return {"success": False, "error": str(e)}

    def get_scheduler_status(self):
        """스케줄러 상태 조회"""
        from src.api.main import scheduler
        
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "scheduler_running": scheduler.running,
            "job_count": len(jobs),
            "jobs": jobs
        } 