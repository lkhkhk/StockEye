from sqlalchemy.orm import Session
from src.api.models.stock_master import StockMaster
from src.api.models.daily_price import DailyPrice
from src.common.db_connector import get_db
import logging
from datetime import datetime, timedelta
import random
from src.common.dart_utils import dart_get_all_stocks
from src.api.models.disclosure import Disclosure
from src.common.dart_utils import dart_get_disclosures
from src.api.models.price_alert import PriceAlert
from src.api.models.user import User
from src.api.models.system_config import SystemConfig
from src.common.exceptions import DartApiError

logger = logging.getLogger(__name__)

class StockService:
    def __init__(self):
        self.last_checked_rcept_no = None

    def check_and_notify_new_disclosures(self, db: Session):
        """
        DART에서 최신 공시를 확인하고, 구독자에게 알림을 보낸 후 관리자에게 요약 리포트를 보냅니다.
        """
        from src.common.notify_service import send_telegram_message
        import os

        try:
            # 1. DB에서 마지막 확인한 공시 접수번호 조회
            last_checked_config = db.query(SystemConfig).filter(SystemConfig.key == 'last_checked_rcept_no').first()
            last_checked_rcept_no = last_checked_config.value if last_checked_config else None

            # 2. 최신 공시 조회
            logger.info("DART에서 최신 공시 목록을 조회합니다.")
            try:
                latest_disclosures = dart_get_disclosures(corp_code=None, max_count=15)
            except DartApiError as e:
                if e.status_code == '020': # 사용한도 초과
                    logger.critical(f"DART API 사용 한도를 초과했습니다: {e}")
                else:
                    logger.error(f"DART 공시 조회 중 API 오류 발생: {e}", exc_info=True)
                return # 함수 실행 중단

            if not latest_disclosures:
                logger.info("새로운 공시가 없습니다.")
                return

            # 3. 최초 실행 시 기준점 설정 (DB에 값이 없을 때)
            if last_checked_rcept_no is None:
                new_rcept_no = latest_disclosures[0]['rcept_no']
                if last_checked_config:
                    last_checked_config.value = new_rcept_no
                else:
                    db.add(SystemConfig(key='last_checked_rcept_no', value=new_rcept_no))
                db.commit()
                logger.info(f"최초 실행. 기준 접수번호를 {new_rcept_no}로 DB에 설정합니다.")
                return

            # 4. 신규 공시 필터링
            new_disclosures = [d for d in latest_disclosures if d['rcept_no'] > last_checked_rcept_no]
            if not new_disclosures:
                logger.info(f"신규 공시가 없습니다. (DB 기준: {last_checked_rcept_no})")
                return

            logger.info(f"{len(new_disclosures)}건의 신규 공시를 발견했습니다.")
            
            total_notified_users = 0
            
            # 4. 신규 공시별로 구독자에게 알림 전송
            for disclosure in reversed(new_disclosures):
                stock_code = disclosure.get('stock_code')
                if not stock_code:
                    continue # 상장되지 않은 기업의 공시는 건너뜀

                # 해당 종목의 공시를 구독한 사용자 조회
                subscriptions = db.query(PriceAlert).filter(
                    PriceAlert.symbol == stock_code,
                    PriceAlert.notify_on_disclosure == True,
                    PriceAlert.is_active == True
                ).all()

                if not subscriptions:
                    continue

                user_ids = [sub.user_id for sub in subscriptions]
                users = db.query(User).filter(User.id.in_(user_ids)).all()
                
                notified_count_per_disclosure = 0
                for user in users:
                    if user.telegram_id:
                        msg = (
                            f"🔔 [{disclosure['corp_name']}] 신규 공시\n\n"
                            f"📑 {disclosure['report_nm']}\n"
                            f"🕒 {disclosure['rcept_dt']}\n"
                            f"🔗 https://dart.fss.or.kr/dsaf001/main.do?rcpNo={disclosure['rcept_no']}"
                        )
                        send_telegram_message(user.telegram_id, msg)
                        notified_count_per_disclosure += 1
                
                total_notified_users += notified_count_per_disclosure
                logger.info(f"'{disclosure['corp_name']}' 공시를 {notified_count_per_disclosure}명에게 알렸습니다.")

            # 5. 관리자에게 요약 리포트 전송
            admin_id = os.getenv("TELEGRAM_ADMIN_ID")
            if admin_id:
                summary_msg = (
                    f"📈 공시 알림 요약 리포트\n\n"
                    f"- 발견된 신규 공시: {len(new_disclosures)}건\n"
                    f"- 총 알림 발송 건수: {total_notified_users}건"
                )
                send_telegram_message(int(admin_id), summary_msg)
            
            # 6. 마지막 확인 번호 DB에 갱신
            newest_rcept_no = new_disclosures[0]['rcept_no']
            last_checked_config.value = newest_rcept_no
            db.commit()
            logger.info(f"마지막 확인 접수번호를 {newest_rcept_no}로 DB에 갱신합니다.")

        except Exception as e:
            db.rollback()
            logger.error(f"신규 공시 확인 및 알림 작업 중 예상치 못한 오류 발생: {e}", exc_info=True)

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