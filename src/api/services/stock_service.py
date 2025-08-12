from sqlalchemy.orm import Session
from src.api.models.stock_master import StockMaster
from src.api.models.daily_price import DailyPrice
from src.common.db_connector import get_db
import yfinance as yf
import logging
from datetime import datetime, timedelta
import re

from src.common.dart_utils import dart_get_all_stocks
from src.api.models.disclosure import Disclosure
from src.common.dart_utils import dart_get_disclosures
from src.api.models.price_alert import PriceAlert
from src.api.models.user import User
from src.api.models.system_config import SystemConfig
from src.common.exceptions import DartApiError

logger = logging.getLogger(__name__)

def _parse_disclosure_type(report_nm: str) -> str:
    """공시 보고서명에서 '[기재정정]'과 같은 접두사를 제거하고 보고서 유형을 추출합니다."""
    if not report_nm:
        return ''
    # 정규식으로 대괄호로 묶인 접두사 제거 (예: [기재정정] 사업보고서 -> 사업보고서)
    # 양쪽 공백도 제거
    return re.sub(r'^\s*\[[^\]]+\]\s*', '', report_nm).strip()

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
                latest_disclosures = await dart_get_disclosures(corp_code=None, last_rcept_no=last_checked_rcept_no)
                logger.debug(f"dart_get_disclosures 호출 직후 latest_disclosures 길이: {len(latest_disclosures)}") # Added debug log
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

            # 3. 신규 공시 필터링 및 최초 실행 시 기준점 설정
            if last_checked_rcept_no is None:
                new_disclosures = latest_disclosures
                logger.info(f"최초 실행으로 모든 공시 ({len(new_disclosures)}건)를 신규로 간주합니다.")
                # Set the initial last_checked_rcept_no for the SystemConfig
                new_rcept_no_for_config = latest_disclosures[0]['rcept_no']
                if last_checked_config:
                    last_checked_config.value = new_rcept_no_for_config
                else:
                    last_checked_config = SystemConfig(key='last_checked_rcept_no', value=new_rcept_no_for_config)
                    db.add(last_checked_config)
                db.commit()
                logger.info(f"최초 실행. 기준 접수번호를 {new_rcept_no_for_config}로 DB에 설정합니다.")
            else:
                new_disclosures = [d for d in latest_disclosures if d['rcept_no'] > last_checked_rcept_no]
                if not new_disclosures:
                    logger.info(f"신규 공시가 없습니다. (DB 기준: {last_checked_rcept_no})")
                    logger.debug("check_and_notify_new_disclosures 함수 종료 (신규 공시 없음).")
                    return

            logger.info(f"{len(new_disclosures)}건의 신규 공시를 발견했습니다. DB에 저장 및 알림을 시작합니다.")
            logger.debug(f"신규 공시 목록: {[d['rcept_no'] for d in new_disclosures]}")
            
            disclosures_to_add = []
            inserted_count = 0
            skipped_count = 0

            for item in new_disclosures:
                rcept_no = item.get('rcept_no')
                stock_code = item.get('stock_code')

                # Skip if no rcept_no or no stock_code (should ideally not happen with new_disclosures)
                if not rcept_no or not stock_code:
                    skipped_count += 1
                    logger.debug(f"공시 항목에 rcept_no 또는 stock_code 없음 (신규 공시 필터링 후): {item}")
                    continue

                # Check if already exists in DB (double-check, though new_disclosures should prevent this)
                existing = db.query(Disclosure).filter(Disclosure.rcept_no == rcept_no).first()
                if existing:
                    skipped_count += 1
                    logger.debug(f"기존 공시 건너뛰기 (신규 공시 필터링 후): {rcept_no}")
                    continue

                try:
                    disclosed_at = datetime.strptime(item.get('rcept_dt'), "%Y%m%d")
                except (ValueError, TypeError):
                    logger.warning(f"날짜 파싱 실패: {item.get('rcept_dt')}, 현재 시간으로 대체합니다.")
                    disclosed_at = datetime.now()

                new_disclosure_obj = Disclosure(
                    stock_code=stock_code,
                    corp_code=item.get('corp_code'),
                    title=item.get('report_nm', ''),
                    rcept_no=rcept_no,
                    disclosed_at=disclosed_at,
                    url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                    disclosure_type=_parse_disclosure_type(item.get('report_nm', ''))
                )
                disclosures_to_add.append(new_disclosure_obj)
            
            if disclosures_to_add:
                db.bulk_save_objects(disclosures_to_add)
                db.commit()
                inserted_count = len(disclosures_to_add)
                logger.info(f"신규 공시 {inserted_count}건을 DB에 추가했습니다. (건너뜀: {skipped_count}건)")
            else:
                logger.info(f"DB에 추가할 신규 공시가 없습니다. (건너뜀: {skipped_count}건)")

            total_notified_users = 0
            
            # 5. 신규 공시별로 구독자에게 알림 전송 (inserted_count > 0 인 경우에만)
            if inserted_count > 0:
                for disclosure in reversed(disclosures_to_add): # Iterate over actually inserted disclosures
                    stock_code = disclosure.stock_code # Use the object's attribute
                    logger.debug(f"공시 알림 처리 중: corp_code={disclosure.corp_code}, title={disclosure.title}, stock_code={stock_code}")
                    if not stock_code:
                        logger.debug(f"상장되지 않은 기업 공시 알림 건너뛰기: {disclosure.corp_code}")
                        continue

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
                                f"🔔 [{disclosure.corp_code}] 신규 공시\n\n" # Use corp_code as name might not be available
                                f"📑 {disclosure.title}\n"
                                f"🕒 {disclosure.disclosed_at.strftime('%Y%m%d')}\n"
                                f"🔗 {disclosure.url}"
                            )
                            await send_telegram_message(user.telegram_id, msg)
                            notified_count_per_disclosure += 1
                            logger.debug(f"공시 알림 전송: user_id={user.id}, telegram_id={user.telegram_id}, symbol={stock_code}")
                    
                    total_notified_users += notified_count_per_disclosure
                    logger.info(f"'{disclosure.corp_code}' 공시를 {notified_count_per_disclosure}명에게 알렸습니다.")

            # 6. 관리자에게 요약 리포트 전송
            admin_id = os.getenv("TELEGRAM_ADMIN_ID")
            if admin_id:
                summary_msg = (
                    f"📈 공시 알림 요약 리포트\n\n"
                    f"- 발견된 신규 공시: {len(new_disclosures)}건\n"
                    f"- DB에 추가된 공시: {inserted_count}건\n"
                    f"- 총 알림 발송 건수: {total_notified_users}건"
                )
                await send_telegram_message(int(admin_id), summary_msg)
                logger.debug(f"관리자({admin_id})에게 공시 알림 요약 리포트 전송 완료.")
            
            # 7. 마지막 확인 번호 DB에 갱신 (실제로 DB에 추가된 공시 중 가장 최신 번호로 갱신)
            if inserted_count > 0:
                newest_rcept_no = max(d.rcept_no for d in disclosures_to_add) # Get max rcept_no from inserted
                if last_checked_config:
                    last_checked_config.value = newest_rcept_no
                else: # Should not happen if last_checked_rcept_no was None initially
                    db.add(SystemConfig(key='last_checked_rcept_no', value=newest_rcept_no))
                db.commit()
                logger.info(f"마지막 확인 접수번호를 {newest_rcept_no}로 DB에 갱신합니다.")
            else:
                logger.info("DB에 추가된 공시가 없어 마지막 확인 접수번호를 갱신하지 않습니다.")
            
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
        """실제 주식 시세 API를 통해 일별시세 갱신 (모든 종목 대상)"""
        logger.debug("update_daily_prices 호출.")
        updated_count = 0
        error_stocks = []
        batch_size = 100 # Define batch size
        offset = 0
        
        try:
            while True:
                # Fetch stocks in batches
                stocks_batch = db.query(StockMaster).offset(offset).limit(batch_size).all()
                if not stocks_batch:
                    break # No more stocks to process

                logger.debug(f"DB에서 {len(stocks_batch)}개 종목 (offset: {offset}) 가져옴.")
                prices_to_add = [] # List to collect DailyPrice objects for bulk insertion

                for stock in stocks_batch:
                    logger.debug(f"종목 {stock.symbol} ({stock.name}) 일별시세 갱신 시작.")
                    try:
                        # yfinance를 사용하여 일별 시세 데이터 가져오기
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
                                    volume=int(row['Volume']),
                                    created_at=datetime.now()
                                )
                                prices_to_add.append(new_price) # Collect for bulk insertion
                                updated_count += 1
                                logger.debug(f"새 일별시세 추가 예정: {stock.symbol} - {target_date}")
                    except Exception as e:
                        logger.error(f"일별시세 갱신 중 '{stock.symbol}' 처리에서 오류 발생: {e}")
                        error_stocks.append(stock.symbol)
                
                # Bulk insert after processing each batch of stocks
                if prices_to_add:
                    db.bulk_save_objects(prices_to_add)
                    db.commit() # Commit after each batch
                    logger.info(f"배치 처리 완료: {len(prices_to_add)}개 일별시세 데이터 삽입.")
                else:
                    db.rollback() # Rollback if no prices were added in this batch (e.g., all existed or errors)

                offset += batch_size # Move to the next batch

            logger.info(f"일별시세 갱신 완료. 총 {updated_count}개 데이터 처리. 오류: {len(error_stocks)}개 종목")
            return {"success": True, "updated_count": updated_count, "errors": error_stocks}
        except Exception as e:
            db.rollback()
            logger.error(f"일별시세 갱신 작업 전체 실패: {e}", exc_info=True)
            return {"success": False, "error": f"일별시세 갱신 중 심각한 오류 발생: {e}"}

    async def update_disclosures_for_all_stocks(self, db: Session, days_to_fetch: int = 1):
        """
        DART API에서 최근 N일간의 전체 공시를 조회하여 DB에 신규 공시만 저장합니다.
        """
        import datetime
        logger.debug(f"update_disclosures_for_all_stocks 호출: days_to_fetch={days_to_fetch}")
        result = {'success': True, 'inserted': 0, 'skipped': 0, 'errors': []}
        try:
            # 1. DART API에서 최신 공시 목록 조회
            end_de = datetime.datetime.now()
            bgn_de = end_de - datetime.timedelta(days=days_to_fetch)
            disclosures_from_dart = await dart_get_disclosures(
                corp_code=None, 
                bgn_de=bgn_de.strftime("%Y%m%d"), 
                end_de=end_de.strftime("%Y%m%d")
            )
            logger.info(f"DART에서 {len(disclosures_from_dart)}건의 공시를 조회했습니다.")

            if not disclosures_from_dart:
                return result

            # Collect rcept_nos from DART disclosures that are candidates for insertion
            candidate_rcept_nos = []
            for item in disclosures_from_dart:
                rcept_no = item.get('rcept_no')
                stock_code = item.get('stock_code')
                
                # Only consider disclosures with a receipt number and stock code
                if rcept_no and stock_code:
                    candidate_rcept_nos.append(rcept_no)
                else:
                    # Increment skipped count for items without rcept_no or stock_code
                    result['skipped'] += 1 
                    logger.debug(f"공시 항목에 rcept_no 또는 stock_code 없음: {item}")

            # Batch size for checking existing disclosures in DB
            db_check_batch_size = 1000
            existing_rcept_nos_in_db = set()

            # Query DB in batches to find existing disclosures among candidates
            for i in range(0, len(candidate_rcept_nos), db_check_batch_size):
                batch_rcept_nos = candidate_rcept_nos[i:i + db_check_batch_size]
                existing_in_batch = db.query(Disclosure.rcept_no).filter(Disclosure.rcept_no.in_(batch_rcept_nos)).all()
                existing_rcept_nos_in_db.update([r[0] for r in existing_in_batch])
            
            logger.debug(f"DB에 이미 존재하는 공시 수 (후보군 중): {len(existing_rcept_nos_in_db)}")

            # Filter new disclosures to add based on DB check
            new_disclosures_to_add = []
            for item in disclosures_from_dart:
                rcept_no = item.get('rcept_no')
                stock_code = item.get('stock_code')

                # Skip if no rcept_no, no stock_code, or already exists in DB
                if not rcept_no or not stock_code or rcept_no in existing_rcept_nos_in_db:
                    result['skipped'] += 1
                    continue

                try:
                    disclosed_at = datetime.datetime.strptime(item.get('rcept_dt'), "%Y%m%d")
                except (ValueError, TypeError):
                    logger.warning(f"날짜 파싱 실패: {item.get('rcept_dt')}, 현재 시간으로 대체합니다.")
                    disclosed_at = datetime.datetime.now()

                new_disclosure = Disclosure(
                    stock_code=stock_code,
                    corp_code=item.get('corp_code'),
                    title=item.get('report_nm', ''),
                    rcept_no=rcept_no,
                    disclosed_at=disclosed_at,
                    url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                    disclosure_type=_parse_disclosure_type(item.get('report_nm', ''))
                )
                new_disclosures_to_add.append(new_disclosure)

            # 4. 신규 공시 일괄 추가
            if new_disclosures_to_add:
                db.bulk_save_objects(new_disclosures_to_add)
                db.commit()
                result['inserted'] = len(new_disclosures_to_add)
                logger.info(f"신규 공시 {result['inserted']}건을 DB에 추가했습니다.")
            else:
                logger.info("추가할 신규 공시가 없습니다.")

        except Exception as e:
            db.rollback()
            result['success'] = False
            result['errors'].append(str(e))
            logger.error(f"전체 공시 갱신 실패: {e}", exc_info=True)
        return result

    async def update_disclosures(self, db: Session, corp_code: str, stock_code: str, stock_name: str, max_count: int = 10):
        """
        DART API에서 특정 기업의 최근 공시를 조회하여 DB에 신규 공시만 저장합니다.
        반환: {'success': True/False, 'inserted': n, 'skipped': m, 'errors': [...]} 
        """
        import datetime
        logger.debug(f"update_disclosures 호출: corp_code={corp_code}, stock_code={stock_code}, max_count={max_count}")
        result = {'success': True, 'inserted': 0, 'skipped': 0, 'errors': []}
        try:
            disclosures = await dart_get_disclosures(corp_code, max_count=max_count)
            logger.debug(f"DART에서 {len(disclosures)}개 특정 종목 공시 데이터 가져옴.")
            
            for item in disclosures:
                rcept_no = item.get('rcept_no')
                if not rcept_no:
                    result['errors'].append(f"공시 항목에 rcept_no 없음: {item}")
                    logger.warning(f"공시 항목에 rcept_no 없음: {item}")
                    continue

                existing = db.query(Disclosure).filter(Disclosure.rcept_no == rcept_no).first()
                if existing:
                    result['skipped'] += 1
                    logger.debug(f"기존 공시 건너뛰기: {rcept_no}")
                    continue

                try:
                    disclosed_at = datetime.datetime.strptime(item.get('rcept_dt'), "%Y%m%d")
                except (ValueError, TypeError):
                     logger.warning(f"날짜 파싱 실패: {item.get('rcept_dt')}, 현재 시간으로 대체합니다.")
                     disclosed_at = datetime.datetime.now()

                disclosure = Disclosure(
                    stock_code=stock_code,
                    corp_code=corp_code,
                    title=item.get('report_nm', ''),
                    rcept_no=rcept_no,
                    disclosed_at=disclosed_at,
                    url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                    disclosure_type=_parse_disclosure_type(item.get('report_nm', ''))
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
