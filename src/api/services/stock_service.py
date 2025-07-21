from sqlalchemy.orm import Session
from src.api.models.stock_master import StockMaster
from src.api.models.daily_price import DailyPrice
from src.api.db import get_db
import logging
from datetime import datetime, timedelta
import random
from src.common.dart_utils import dart_get_all_stocks
from src.api.models.disclosure import Disclosure
from src.common.dart_utils import dart_get_disclosures

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
            return latest_price.close
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

    def get_sample_stocks_for_test():
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

    def update_stock_master(self, db: Session, use_dart: bool = True):
        """종목마스터 정보 갱신 (운영: DART 전체 종목, 테스트: 샘플)"""
        try:
            logger.info("종목마스터 갱신 시작")
            if use_dart:
                try:
                    stocks = dart_get_all_stocks()
                    logger.info(f"DART 전체 종목 수집: {len(stocks)}개")
                except Exception as e:
                    logger.error(f"DART API 연동 실패: {e}")
                    stocks = get_sample_stocks_for_test()
                    logger.info("DART 실패시 샘플 데이터로 대체")
            else:
                stocks = get_sample_stocks_for_test()
            updated_count = 0
            for stock_data in stocks:
                existing_stock = db.query(StockMaster).filter(
                    StockMaster.symbol == stock_data["symbol"]
                ).first()
                if existing_stock:
                    existing_stock.name = stock_data["name"]
                    existing_stock.market = stock_data.get("market", "")
                    existing_stock.corp_code = stock_data.get("corp_code", None)
                    existing_stock.updated_at = datetime.now()
                else:
                    new_stock = StockMaster(
                        symbol=stock_data["symbol"],
                        name=stock_data["name"],
                        market=stock_data.get("market", ""),
                        corp_code=stock_data.get("corp_code", None),
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

    def update_disclosures(self, db: Session, corp_code: str, stock_code: str, stock_name: str = "", max_count: int = 10):
        """
        DART API에서 해당 기업의 최근 공시를 조회하여 DB에 신규 공시만 저장(upsert)
        반환: {'success': True/False, 'inserted': n, 'skipped': m, 'errors': [...]} 
        """
        import datetime
        result = {'success': True, 'inserted': 0, 'skipped': 0, 'errors': []}
        try:
            disclosures = dart_get_disclosures(corp_code, max_count=max_count)
            for item in disclosures:
                rcept_no = item.get('rcept_no')
                if not rcept_no:
                    result['errors'].append(f"공시 항목에 rcept_no 없음: {item}")
                    continue
                # 이미 존재하는지 확인
                existing = db.query(Disclosure).filter(Disclosure.rcept_no == rcept_no).first()
                if existing:
                    result['skipped'] += 1
                    continue
                # disclosed_at 파싱 (YYYYMMDD HHMM -> datetime)
                rcept_dt = item.get('rcept_dt')
                rcept_tm = item.get('rcept_tm', '0000')
                try:
                    disclosed_at = datetime.datetime.strptime(f"{rcept_dt}{rcept_tm}", "%Y%m%d%H%M")
                except Exception:
                    disclosed_at = datetime.datetime.strptime(rcept_dt, "%Y%m%d")
                disclosure = Disclosure(
                    stock_code=stock_code,
                    corp_code=corp_code,
                    title=item.get('report_nm', ''),
                    rcept_no=rcept_no,
                    disclosed_at=disclosed_at,
                    url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                    disclosure_type=item.get('report_nm', ''),
                )
                db.add(disclosure)
                result['inserted'] += 1
            db.commit()
        except Exception as e:
            db.rollback()
            result['success'] = False
            result['errors'].append(str(e))
        return result

    def get_scheduler_status(self):
        """스케줄러 상태 조회"""
        try:
            from src.api.main import scheduler
            if scheduler is None:
                raise RuntimeError("scheduler 객체가 None입니다. 초기화 실패 또는 import 순서 문제")
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
        except Exception as e:
            import logging
            logging.error(f"get_scheduler_status 예외: {e}", exc_info=True)
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail=f"스케줄러 상태 조회 실패: {e}") 