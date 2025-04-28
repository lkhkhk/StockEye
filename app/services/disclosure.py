import aiohttp
import asyncio
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Set, Optional, Tuple
from ..core.config import settings
from ..core.database import db
import httpx
import html

logger = logging.getLogger(__name__)

class DisclosureService:
    def __init__(self):
        self.last_disclosure_time: Dict[str, str] = {}
        self.api_url = "https://opendart.fss.or.kr/api/list.json"

    async def fetch_disclosures(self, corp_code: str) -> List[Dict]:
        """공시 정보 조회 (고유번호 사용)"""
        if not corp_code:
            logger.warning("공시 조회를 위한 corp_code가 제공되지 않았습니다.")
            return []

        async with aiohttp.ClientSession() as session:
            params = {
                'crtfc_key': settings.DART_API_KEY,
                'corp_code': corp_code,
                'page_count': 10
            }
            
            try:
                async with session.get(self.api_url, params=params) as response:
                    data = await response.json()
                    
                    if data.get('status') != '000':
                        logger.warning(f"공시 조회 실패 (고유번호: {corp_code}): {data.get('message')}")
                        return []
                    
                    return data.get('list', [])
            except Exception as e:
                logger.error(f"공시 API 호출 중 오류 발생 (고유번호: {corp_code}): {e}")
                return []

    async def process_new_disclosures(self, stock_code: str, corp_code: str, stock_name: str, disclosures: List[Dict], user_ids: Set[str]):
        """새로운 공시 처리"""
        redis_key_base = f"notification:{{user_id}}:{stock_code}"

        if not disclosures:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            message = (
                f"📢 {stock_name} 공시 현황\n\n"
                f"⏰ 확인 시각: {current_time}\n"
                f"ℹ️ 현재 등록된 공시가 없습니다."
            )
            
            for user_id in user_ids:
                try:
                    await db.redis.set(
                        redis_key_base.format(user_id=user_id),
                        message,
                        ex=3600  # 1시간 유효
                    )
                except Exception as e:
                    logger.error(f"Redis 저장 중 오류 발생: {e}")
            
            return

        rcept_dt = disclosures[0].get('rcept_dt', '')
        rcept_tm = disclosures[0].get('rcept_tm', '')
        latest_time = rcept_dt + rcept_tm if rcept_dt and rcept_tm else ''

        if corp_code not in self.last_disclosure_time:
            self.last_disclosure_time[corp_code] = latest_time
            return
        
        if latest_time and latest_time > self.last_disclosure_time[corp_code]:
            new_disclosures = [
                item for item in disclosures
                if item.get('rcept_dt', '') + item.get('rcept_tm', '') > self.last_disclosure_time[corp_code]
            ]
            
            if new_disclosures:
                message = self._format_disclosure_message(stock_name, new_disclosures)
                
                for user_id in user_ids:
                    try:
                        await db.redis.set(
                            redis_key_base.format(user_id=user_id),
                            message,
                            ex=3600
                        )
                    except Exception as e:
                        logger.error(f"Redis 저장 중 오류 발생: {e}")
                
                self.last_disclosure_time[corp_code] = latest_time
                logger.info(f"{stock_name} ({corp_code})의 새로운 공시 {len(new_disclosures)}건 발견")

    def _format_disclosure_message(self, stock_name: str, disclosures: List[Dict]) -> str:
        """공시 알림 메시지 포맷팅"""
        message = f"🔔 <b>{stock_name}</b>의 새로운 공시가 등록되었습니다!\n\n"
        
        for item in disclosures:
            # Use get() with default values here as well for safety
            rcept_dt = item.get('rcept_dt', '--------') # Default to indicate missing data
            rcept_tm = item.get('rcept_tm', '----') # Default to indicate missing data
            rcept_no = item.get('rcept_no', '')
            report_nm = item.get('report_nm', '제목 없음')

            date_str = f"{rcept_dt[:4]}-{rcept_dt[4:6]}-{rcept_dt[6:]}" if len(rcept_dt) == 8 else rcept_dt
            time_str = f"{rcept_tm[:2]}:{rcept_tm[2:4]}" if len(rcept_tm) == 4 else rcept_tm
            report_link = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}" if rcept_no else "#"
            
            message += f"📄 <b>{report_nm}</b>\n" # Use HTML bold tag
            message += f"⏰ {date_str} {time_str}\n"
            message += f"🔗 <a href='{report_link}'>공시 보기</a>\n\n" # Use HTML link tag
        
        return message

async def check_disclosures():
    logger.info("주기적인 공시 확인 시작...")
    async with db.pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT us.user_id, s.code as stock_code, s.name as stock_name, s.corp_code
            FROM user_stocks us
            JOIN stocks s ON us.stock_code = s.code
        """)

        stock_users: Dict[str, Dict] = {}
        for row in rows:
            corp_code = row['corp_code']
            if not corp_code:
                logger.debug(f"Skipping disclosure check for {row['stock_name']} ({row['stock_code']}) due to missing corp_code.")
                continue
            
            if corp_code not in stock_users:
                stock_users[corp_code] = {
                    'stock_code': row['stock_code'],
                    'stock_name': row['stock_name'],
                    'user_ids': set()
                }
            stock_users[corp_code]['user_ids'].add(row['user_id'])

    tasks = []
    for corp_code, data in stock_users.items():
        tasks.append(process_single_stock(corp_code, data['stock_code'], data['stock_name'], data['user_ids']))

    if tasks:
        logger.info(f"{len(tasks)}개 종목(고유번호 기준)에 대한 공시 확인 작업 생성...")
        await asyncio.gather(*tasks)
    else:
        logger.info("모니터링 중인 주식이 없거나 고유번호가 설정되지 않아 공시 확인을 건너뛰었습니다.")

    logger.info("공시 확인 완료.")

async def process_single_stock(corp_code: str, stock_code: str, stock_name: str, user_ids: Set[str]):
    """개별 주식 공시 처리"""
    disclosures = await disclosure_service.fetch_disclosures(corp_code)
    await disclosure_service.process_new_disclosures(stock_code, corp_code, stock_name, disclosures, user_ids)

async def get_latest_disclosures(corp_code: str, limit: int = 5) -> List[Dict]:
    """특정 기업의 최근 공시 목록을 DART API에서 조회 (최대 100개까지 가능, DART 정책 따름)"""
    logger.info(f"DART 공시 목록 조회 시작: corp_code={corp_code}, limit={limit}")
    if not settings.DART_API_KEY:
        logger.error("DART API 키가 설정되지 않았습니다.")
        return []

    # DART API는 페이지당 최대 100개, limit은 보여줄 개수
    page_size = min(limit, 100) # DART는 최대 100개씩 반환
    params = {
        "crtfc_key": settings.DART_API_KEY,
        "corp_code": corp_code,
        "bgn_de": (datetime.now() - timedelta(days=90)).strftime('%Y%m%d'), # 최근 90일
        "end_de": datetime.now().strftime('%Y%m%d'),
        "page_no": 1,
        "page_count": page_size,
    }
    DART_DISCLOSURE_LIST_URL = "https://opendart.fss.or.kr/api/list.json" # URL 정의

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(DART_DISCLOSURE_LIST_URL, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("status") != "000":
            logger.warning(f"DART 공시 목록 API 오류: {data.get('status')} - {data.get('message')} (corp_code: {corp_code})")
            return []

        disclosure_list = data.get("list", [])
        logger.info(f"DART 공시 목록 조회 성공: {len(disclosure_list)}건 (corp_code: {corp_code})")
        # 필요한 정보만 추출하여 반환 (예시)
        formatted_list = []
        for item in disclosure_list[:limit]: # 실제 limit 적용
            formatted_list.append({
                "corp_name": item.get("corp_name"),
                "report_nm": item.get("report_nm"),
                "rcept_no": item.get("rcept_no"), # 공시 상세 URL 생성용
                "rcept_dt": item.get("rcept_dt"), # 접수일자
                "flr_nm": item.get("flr_nm"), # 제출인
            })
        return formatted_list

    except httpx.HTTPStatusError as e:
        logger.error(f"DART 공시 목록 API 요청 실패: {e.response.status_code} - {e.response.text} (corp_code: {corp_code})")
        return []
    except httpx.RequestError as e:
        logger.error(f"DART 공시 목록 API 요청 중 네트워크 오류: {e} (corp_code: {corp_code})")
        return []
    except Exception as e:
        logger.error(f"DART 공시 목록 처리 중 예상치 못한 오류: {e} (corp_code: {corp_code})", exc_info=True)
        return []

disclosure_service = DisclosureService() 
