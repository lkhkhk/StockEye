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

    async def check_and_notify_new_disclosures(self, db: Session):
        """
        DART에서 최신 공시를 확인하고, 구독자에게 알림을 보낸 후 관리자에게 요약 리포트를 보냅니다.
        """
        from src.common.notify_service import send_telegram_message
        import os

        logger.debug("check_and_notify_new_disclosures 함수 시작.")
        try:
            # 1. DB에서 마지막 확인한 공시 접수번호 조회
            last_checked_config = db.query(SystemConfig).filter(SystemConfig.key == 'last_checked_rcept_no').first()
            last_checked_rcept_no = last_checked_config.value if last_checked_config else None
            logger.debug(f"마지막 확인 공시 접수번호 (DB): {last_checked_rcept_no}")

            # 2. 최신 공시 조회
            logger.info("DART에서 최신 공시 목록을 조회합니다.")
            try:
                latest_disclosures = await dart_get_disclosures(corp_code=None, max_count=15)
                logger.debug(f"DART에서 조회된 최신 공시 수: {len(latest_disclosures)}")
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
                logger.debug("check_and_notify_new_disclosures 함수 종료 (최초 실행 설정).")
                return

            # 4. 신규 공시 필터링
            new_disclosures = [d for d in latest_disclosures if d['rcept_no'] > last_checked_rcept_no]
            if not new_disclosures:
                logger.info(f"신규 공시가 없습니다. (DB 기준: {last_checked_rcept_no})")
                logger.debug("check_and_notify_new_disclosures 함수 종료 (신규 공시 없음).")
                return

            logger.info(f"{len(new_disclosures)}건의 신규 공시를 발견했습니다.")
            logger.debug(f"신규 공시 목록: {[d['rcept_no'] for d in new_disclosures]}")
            
            total_notified_users = 0
            
            # 4. 신규 공시별로 구독자에게 알림 전송
            for disclosure in reversed(new_disclosures):
                stock_code = disclosure.get('stock_code')
                logger.debug(f"공시 처리 중: corp_name={disclosure.get('corp_name')}, report_nm={disclosure.get('report_nm')}, stock_code={stock_code}")
                if not stock_code:
                    logger.debug(f"상장되지 않은 기업 공시 건너뛰기: {disclosure.get('corp_name')}")
                    continue # 상장되지 않은 기업의 공시는 건너뜀

                # 해당 종목의 공시를 구독한 사용자 조회
                subscriptions = db.query(PriceAlert).filter(
                    PriceAlert.symbol == stock_code,
                    PriceAlert.notify_on_disclosure == True,
                    PriceAlert.is_active == True
                ).all()
                logger.debug(f"종목 {stock_code}의 공시 알림 구독자 수: {len(subscriptions)}")

                if not subscriptions:
                    logger.debug(f"종목 {stock_code}에 대한 활성 공시 알림 구독자가 없습니다.")
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
                        logger.debug(f"공시 알림 전송: user_id={user.id}, telegram_id={user.telegram_id}, symbol={stock_code}")
                
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
                logger.debug(f"관리자({admin_id})에게 공시 알림 요약 리포트 전송 완료.")
            
            # 6. 마지막 확인 번호 DB에 갱신
            newest_rcept_no = new_disclosures[0]['rcept_no']
            last_checked_config.value = newest_rcept_no
            db.commit()
            logger.info(f"마지막 확인 접수번호를 {newest_rcept_no}로 DB에 갱신합니다.")
            logger.debug("check_and_notify_new_disclosures 함수 종료 (정상 완료).")

        except Exception as e:
            db.rollback()
            logger.error(f"신규 공시 확인 및 알림 작업 중 예상치 못한 오류 발생: {e}", exc_info=True)

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

    def get_current_price_and_change(self, symbol: str, db: Session):
        logger.debug(f"get_current_price_and_change 호출: symbol={symbol}")
        
        # 최신 2일치 일별시세 데이터 조회 (오늘, 어제)
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
            logger.warning(f"현재가 없음: {symbol}. 임시 가격 생성.")
            # 데이터가 없으면 임시 가격 생성
            current_price = random.randint(50000, 200000)
            previous_close = random.randint(45000, 190000) # 임시 전일 종가
            
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
                    raise  # 예외를 다시 발생시켜 상위 except 블록에서 처리하도록 함
            else:
                # 테스트용 샘플 데이터
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
                    logger.debug(f"종목 업데이트: {stock_data['symbol']} - {stock_data['name']}")
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
                    logger.debug(f"새 종목 추가: {stock_data['symbol']} - {stock_data['name']}")
                updated_count += 1
            db.commit()
            logger.info(f"종목마스터 갱신 완료. 총 {updated_count}개 종목 처리.")
            return {"success": True, "updated_count": updated_count}
        except Exception as e:
            db.rollback()
            logger.error(f"종목마스터 갱신 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def update_daily_prices(self, db: Session):
        """30일치 일별시세 갱신 (모든 종목 대상)"""
        logger.debug("update_daily_prices 호출.")
        try:
            from src.api.models.stock_master import StockMaster
            stocks = db.query(StockMaster).all()
            logger.debug(f"DB에서 {len(stocks)}개 종목 가져옴.")
            # stocks = self.get_sample_stocks_for_test(db) # 이 라인은 테스트용이므로 실제 로직에서는 사용하지 않습니다.
            return self._update_prices_for_stocks(db, stocks)
        except Exception as e:
            logger.error(f"일별시세 갱신 작업 전체 실패: {e}", exc_info=True)
            db.rollback()
            return {"success": False, "error": f"일별시세 갱신 중 심각한 오류 발생: {e}"}

    def _update_prices_for_stocks(self, db: Session, stocks: list):
        """주어진 종목 리스트에 대한 일별시세를 갱신하는 내부 로직"""
        logger.debug(f"_update_prices_for_stocks 호출: {len(stocks)}개 종목.")
        updated_count = 0
        error_stocks = []
        
        for stock in stocks:
            logger.debug(f"종목 {stock.symbol} ({stock.name}) 일별시세 갱신 시작.")
            try:
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
                        logger.debug(f"새 일별시세 추가: {stock.symbol} - {target_date.date()}")
            except Exception as e:
                logger.error(f"일별시세 갱신 중 '{stock.symbol}' 처리에서 오류 발생: {e}")
                error_stocks.append(stock.symbol)
        
        db.commit()
        logger.info(f"일별시세 갱신 완료: {updated_count}개 데이터 처리. 오류: {len(error_stocks)}개 종목")
        logger.debug(f"_update_prices_for_stocks 함수 종료. 총 {updated_count}개 데이터 처리.")
        return {"success": True, "updated_count": updated_count, "errors": error_stocks}

    async def update_disclosures(self, db: Session, corp_code: str = None, stock_code: str = None, stock_name: str = "", max_count: int = 10):
        """
        DART API에서 해당 기업의 최근 공시를 조회하여 DB에 신규 공시만 저장(upsert)
        corp_code가 None이면 전체 공시를 조회합니다.
        반환: {'success': True/False, 'inserted': n, 'skipped': m, 'errors': [...]} 
        """
        import datetime
        logger.debug(f"update_disclosures 호출: corp_code={corp_code}, stock_code={stock_code}, max_count={max_count}")
        result = {'success': True, 'inserted': 0, 'skipped': 0, 'errors': []}
        try:
            if corp_code is None: # 전체 공시 조회 (corp_code 없이 호출)
                logger.info("전체 공시 조회를 위해 DART API를 호출합니다.")
                # 최근 1일치 공시만 가져오도록 설정 (과도한 호출 방지)
                today = datetime.datetime.now().strftime("%Y%m%d")
                disclosures = await dart_get_disclosures(corp_code=None, bgn_de=today, end_de=today, max_count=1000) # max_count 늘림
                logger.debug(f"DART에서 {len(disclosures)}개 전체 공시 데이터 가져옴.")

                # 가져온 공시에 stock_code가 없는 경우 매핑
                for item in disclosures:
                    if 'stock_code' not in item or not item['stock_code']:
                        # corp_code로 StockMaster에서 stock_code 찾기
                        stock_master_entry = db.query(StockMaster).filter(StockMaster.corp_code == item.get('corp_code')).first()
                        if stock_master_entry:
                            item['stock_code'] = stock_master_entry.symbol
                        else:
                            logger.warning(f"corp_code {item.get('corp_code')}에 해당하는 stock_code를 찾을 수 없습니다. 공시 건너뜀: {item.get('report_nm')}")
                            continue # stock_code를 찾을 수 없으면 건너뜀
            else: # 특정 종목 공시 조회
                disclosures = await dart_get_disclosures(corp_code, max_count=max_count)
                logger.debug(f"DART에서 {len(disclosures)}개 특정 종목 공시 데이터 가져옴.")
            
            for item in disclosures:
                rcept_no = item.get('rcept_no')
                if not rcept_no:
                    result['errors'].append(f"공시 항목에 rcept_no 없음: {item}")
                    logger.warning(f"공시 항목에 rcept_no 없음: {item}")
                    continue
                # 이미 존재하는지 확인
                existing = db.query(Disclosure).filter(Disclosure.rcept_no == rcept_no).first()
                if existing:
                    result['skipped'] += 1
                    logger.debug(f"기존 공시 건너뛰기: {rcept_no}")
                    continue
                # disclosed_at 파싱 (YYYYMMDD HHMM -> datetime)
                rcept_dt = item.get('rcept_dt')
                rcept_tm = item.get('rcept_tm', '0000')
                try:
                    disclosed_at = datetime.datetime.strptime(f"{rcept_dt}{rcept_tm}", "%Y%m%d%H%M")
                except Exception:
                    disclosed_at = datetime.datetime.strptime(rcept_dt, "%Y%m%d")
                
                # stock_code가 없는 경우 (전체 조회 시)
                current_stock_code = stock_code if stock_code else item.get('stock_code')
                if not current_stock_code:
                    logger.warning(f"공시 {rcept_no}에 대한 stock_code가 없어 저장 불가. corp_code: {corp_code}")
                    result['errors'].append(f"공시 {rcept_no}에 대한 stock_code 없음")
                    continue

                disclosure = Disclosure(
                    stock_code=current_stock_code,
                    corp_code=corp_code if corp_code else item.get('corp_code'),
                    title=item.get('report_nm', ''),
                    rcept_no=rcept_no,
                    disclosed_at=disclosed_at,
                    url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                    disclosure_type=item.get('report_nm', ''),
                )
                db.add(disclosure)
                result['inserted'] += 1
                logger.debug(f"새 공시 추가: {rcept_no}")
            db.commit()
            logger.info(f"공시 갱신 완료. 삽입: {result['inserted']}건, 건너뜀: {result['skipped']}건.")
        except Exception as e:
            db.rollback()
            result['success'] = False
            result['errors'].append(str(e))
            logger.error(f"공시 갱신 실패 (corp_code={corp_code}): {e}", exc_info=True)
        return result