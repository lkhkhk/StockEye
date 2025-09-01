from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
import re
import os

from src.common.models.disclosure import Disclosure
from src.common.models.price_alert import PriceAlert
from src.common.models.user import User
from src.common.models.system_config import SystemConfig
from src.common.models.stock_master import StockMaster
from src.common.utils.exceptions import DartApiError
from src.common.utils.dart_utils import dart_get_disclosures
from src.common.services.notify_service import send_telegram_message

logger = logging.getLogger(__name__)

def _parse_disclosure_type(report_nm: str) -> str:
    """공시 보고서명에서 '[기재정정]'과 같은 접두사를 제거하고 보고서 유형을 추출합니다."""
    if not report_nm:
        return ''
    return re.sub(r'^\s*\[[^\]]+\]\s*', '', report_nm).strip()

class DisclosureService:
    def __init__(self):
        self.last_checked_rcept_no = None

    async def check_and_notify_new_disclosures(self, db: Session):
        """
        DART에서 최신 공시를 확인하고, 구독자에게 알림을 보낸 후 관리자에게 요약 리포트를 보냅니다.
        """
        logger.debug("check_and_notify_new_disclosures 함수 시작.")
        try:
            last_checked_config = db.query(SystemConfig).filter(SystemConfig.key == 'last_checked_rcept_no').first()
            last_checked_rcept_no = last_checked_config.value if last_checked_config else None
            logger.debug(f"마지막 확인 공시 접수번호 (DB): {last_checked_rcept_no}")

            logger.info("DART에서 최신 공시 목록을 조회합니다.")
            try:
                latest_disclosures = await dart_get_disclosures(corp_code=None, last_rcept_no=last_checked_rcept_no)
                logger.debug(f"DART에서 조회된 최신 공시 수: {len(latest_disclosures)}")
            except DartApiError as e:
                if e.status_code == '020':
                    logger.critical(f"DART API 사용 한도를 초과했습니다: {e}")
                else:
                    logger.error(f"DART 공시 조회 중 API 오류 발생: {e}", exc_info=True)
                return

            if not latest_disclosures:
                logger.info("새로운 공시가 없습니다.")
                return

            if last_checked_rcept_no is None:
                new_disclosures = latest_disclosures
                logger.info(f"최초 실행으로 모든 공시 ({len(new_disclosures)}건)를 신규로 간주합니다.")
                new_rcept_no_for_config = latest_disclosures[0]['rcept_no']
                if last_checked_config:
                    last_checked_config.value = new_rcept_no_for_config
                else:
                    db.add(SystemConfig(key='last_checked_rcept_no', value=new_rcept_no_for_config))
                db.commit()
                logger.info(f"최초 실행. 기준 접수번호를 {new_rcept_no_for_config}로 DB에 설정합니다.")
            else:
                new_disclosures = [d for d in latest_disclosures if d['rcept_no'] > last_checked_rcept_no]
                if not new_disclosures:
                    logger.info(f"신규 공시가 없습니다. (DB 기준: {last_checked_rcept_no})")
                    return

            logger.info(f"{len(new_disclosures)}건의 신규 공시를 발견했습니다. DB에 저장 및 알림을 시작합니다.")
            
            disclosures_to_add = []
            for item in new_disclosures:
                existing = db.query(Disclosure).filter(Disclosure.rcept_no == item.get('rcept_no')).first()
                if not existing:
                    disclosures_to_add.append(Disclosure(
                        stock_code=item.get('stock_code'),
                        corp_code=item.get('corp_code'),
                        title=item.get('report_nm', ''),
                        rcept_no=item.get('rcept_no'),
                        disclosed_at=datetime.strptime(item.get('rcept_dt'), "%Y%m%d"),
                        url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no')}",
                        disclosure_type=_parse_disclosure_type(item.get('report_nm', ''))
                    ))
            
            if disclosures_to_add:
                db.bulk_save_objects(disclosures_to_add)
                db.commit()
                logger.info(f"신규 공시 {len(disclosures_to_add)}건을 DB에 추가했습니다.")

            total_notified_users = 0
            if disclosures_to_add:
                for disclosure in reversed(disclosures_to_add):
                    if not disclosure.stock_code:
                        logger.info("상장되지 않은 기업 공시 알림 건너뛰기")
                        continue

                    subscriptions = db.query(PriceAlert).filter(
                        PriceAlert.symbol == disclosure.stock_code,
                        PriceAlert.notify_on_disclosure == True,
                        PriceAlert.is_active == True
                    ).all()
                    
                    if not subscriptions:
                        logger.info(f"종목 {disclosure.stock_code}에 대한 활성 공시 알림 구독자가 없습니다.")
                        continue

                    user_ids = [sub.user_id for sub in subscriptions]
                    users = db.query(User).filter(User.id.in_(user_ids)).all()
                    stock_info = db.query(StockMaster).filter(StockMaster.symbol == disclosure.stock_code).first()
                    stock_name_for_msg = stock_info.name if stock_info else disclosure.corp_code
                    
                    for user in users:
                        if user.telegram_id:
                            msg = (
                                f"🔔 [{stock_name_for_msg}] 신규 공시\n\n"
                                f"📑 {disclosure.title}\n"
                                f"🕒 {disclosure.disclosed_at.strftime('%Y%m%d')}\n"
                                f"🔗 {disclosure.url}"
                            )
                            await send_telegram_message(user.telegram_id, msg)
                            total_notified_users += 1
                        else:
                            logger.warning(f"사용자 {user.id}의 Telegram ID가 없어 알림")

            admin_id = os.getenv("TELEGRAM_ADMIN_ID")
            if admin_id:
                summary_msg = (
                    f"📈 공시 알림 요약 리포트\n\n"
                    f"- 발견된 신규 공시: {len(new_disclosures)}건\n"
                    f"- DB에 추가된 공시: {len(disclosures_to_add)}건\n"
                    f"- 총 알림 발송 건수: {total_notified_users}건"
                )
                await send_telegram_message(int(admin_id), summary_msg)

            if disclosures_to_add:
                newest_rcept_no = max(d.rcept_no for d in disclosures_to_add)
                if last_checked_config:
                    last_checked_config.value = newest_rcept_no
                else:
                    db.add(SystemConfig(key='last_checked_rcept_no', value=newest_rcept_no))
                db.commit()
                logger.info(f"마지막 확인 접수번호를 {newest_rcept_no}로 DB에 갱신합니다.")

        except Exception as e:
            db.rollback()
            logger.error(f"신규 공시 확인 및 알림 작업 중 예상치 못한 오류 발생: {e}", exc_info=True)

    async def update_disclosures_for_all_stocks(self, db: Session, days_to_fetch: int = 1):
        """
        DART API에서 최근 N일간의 전체 공시를 조회하여 DB에 신규 공시만 저장합니다.
        """
        logger.debug(f"update_disclosures_for_all_stocks 호출: days_to_fetch={days_to_fetch}")
        result = {'success': True, 'inserted': 0, 'skipped': 0, 'errors': []}
        try:
            end_de = datetime.now()
            bgn_de = end_de - timedelta(days=days_to_fetch)
            disclosures_from_dart = await dart_get_disclosures(
                corp_code=None, 
                bgn_de=bgn_de.strftime("%Y%m%d"), 
                end_de=end_de.strftime("%Y%m%d")
            )
            logger.info(f"DART에서 {len(disclosures_from_dart)}건의 공시를 조회했습니다.")

            if not disclosures_from_dart:
                # 공시가 없어도 commit은 호출되어야 함 (예: skipped만 있는 경우)
                db.commit() 
                return result

            candidate_rcept_nos = []
            for item in disclosures_from_dart:
                rcept_no = item.get('rcept_no')
                stock_code = item.get('stock_code')
                
                if rcept_no and stock_code:
                    candidate_rcept_nos.append(rcept_no)

            db_check_batch_size = 1000
            existing_rcept_nos_in_db = set()

            for i in range(0, len(candidate_rcept_nos), db_check_batch_size):
                batch_rcept_nos = candidate_rcept_nos[i:i + db_check_batch_size]
                existing_in_batch = db.query(Disclosure.rcept_no).filter(Disclosure.rcept_no.in_(batch_rcept_nos)).all()
                existing_rcept_nos_in_db.update([r[0] for r in existing_in_batch])
            
            logger.debug(f"DB에 이미 존재하는 공시 수 (후보군 중): {len(existing_rcept_nos_in_db)}")

            new_disclosures_to_add = []
            for item in disclosures_from_dart:
                rcept_no = item.get('rcept_no')
                stock_code = item.get('stock_code')

                if not rcept_no or not stock_code:
                    continue

                if rcept_no in existing_rcept_nos_in_db:
                    continue

                new_disclosure = Disclosure(
                    stock_code=stock_code,
                    corp_code=item.get('corp_code'),
                    title=item.get('report_nm', ''),
                    rcept_no=rcept_no,
                    disclosed_at=datetime.strptime(item.get('rcept_dt'), "%Y%m%d"),
                    url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                    disclosure_type=_parse_disclosure_type(item.get('report_nm', ''))
                )
                new_disclosures_to_add.append(new_disclosure)

            if new_disclosures_to_add:
                db.bulk_save_objects(new_disclosures_to_add)
                db.commit()
                result['inserted'] = len(new_disclosures_to_add)
                logger.info(f"신규 공시 {result['inserted']}건을 DB에 추가했습니다.")
            else:
                logger.info("추가할 신규 공시가 없습니다.")
                db.commit() # 추가된 부분: new_disclosures_to_add가 비어있어도 commit 호출
            
            # 최종 skipped 계산
            result['skipped'] = len(disclosures_from_dart) - result['inserted'] - len([item for item in disclosures_from_dart if not item.get('rcept_no') or not item.get('stock_code')])

        except Exception as e:
            db.rollback()
            result['success'] = False
            result['errors'].append(str(e))
            logger.error(f"전체 공시 갱신 실패: {e}", exc_info=True)
        return result

    async def update_disclosures(self, db: Session, corp_code: str, stock_code: str, stock_name: str, max_count: int = 10):
        """
        DART API에서 특정 기업의 최근 공시를 조회하여 DB에 신규 공시만 저장합니다.
        """
        logger.debug(f"update_disclosures 호출: corp_code={corp_code}, stock_code={stock_code}, max_count={max_count}")
        result = {'success': True, 'inserted': 0, 'skipped': 0, 'errors': []}
        try:
            disclosures = await dart_get_disclosures(corp_code, page_size=max_count)
            logger.debug(f"DART에서 {len(disclosures)}개 특정 종목 공시 데이터 가져옴.")
            
            for item in disclosures:
                rcept_no = item.get('rcept_no')
                if not rcept_no:
                    result['errors'].append(f"공시 항목에 rcept_no 없음: {item}")
                    continue

                existing = db.query(Disclosure).filter(Disclosure.rcept_no == rcept_no).first()
                if existing:
                    result['skipped'] += 1
                    continue

                disclosure = Disclosure(
                    stock_code=stock_code,
                    corp_code=corp_code,
                    title=item.get('report_nm', ''),
                    rcept_no=rcept_no,
                    disclosed_at=datetime.strptime(item.get('rcept_dt'), "%Y%m%d"),
                    url=f"https.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                    disclosure_type=_parse_disclosure_type(item.get('report_nm', ''))
                )
                db.add(disclosure)
                result['inserted'] += 1
            db.commit()
            logger.info(f"공시 갱신 완료. 삽입: {result['inserted']}건, 건너뜀: {result['skipped']}건.")
        except Exception as e:
            db.rollback()
            result['success'] = False
            result['errors'].append(str(e))
            logger.error(f"공시 갱신 실패 (corp_code={corp_code}): {e}", exc_info=True)
        return result