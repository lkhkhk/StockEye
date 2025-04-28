import aiohttp
import asyncio
from datetime import datetime
import logging
from typing import List, Dict, Set
from ..core.config import settings
from ..core.database import db

logger = logging.getLogger(__name__)

class DisclosureService:
    def __init__(self):
        self.last_disclosure_time: Dict[str, str] = {}
        self.api_url = "https://opendart.fss.or.kr/api/list.json"

    async def fetch_disclosures(self, stock_code: str) -> List[Dict]:
        """공시 정보 조회"""
        async with aiohttp.ClientSession() as session:
            params = {
                'crtfc_key': settings.DART_API_KEY,
                'corp_code': stock_code,
                'page_count': 10
            }
            
            try:
                async with session.get(self.api_url, params=params) as response:
                    data = await response.json()
                    
                    if data.get('status') != '000':
                        logger.warning(f"공시 조회 실패 (종목코드: {stock_code}): {data.get('message')}")
                        return []
                    
                    return data.get('list', [])
            except Exception as e:
                logger.error(f"공시 API 호출 중 오류 발생: {e}")
                return []

    async def process_new_disclosures(self, stock_code: str, stock_name: str, disclosures: List[Dict], user_ids: Set[str]):
        """새로운 공시 처리"""
        if not disclosures:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            message = (
                f"📢 {stock_name} 공시 현황\n\n"
                f"⏰ 확인 시각: {current_time}\n"
                f"ℹ️ 현재 등록된 공시가 없습니다."
            )
            
            for user_id in user_ids:
                try:
                    # Redis에 알림 저장
                    await db.redis.set(
                        f"notification:{user_id}:{stock_code}",
                        message,
                        ex=3600  # 1시간 유효
                    )
                except Exception as e:
                    logger.error(f"Redis 저장 중 오류 발생: {e}")
            
            return

        # Use get() with a default value to prevent KeyError
        rcept_dt = disclosures[0].get('rcept_dt', '')
        rcept_tm = disclosures[0].get('rcept_tm', '')
        latest_time = rcept_dt + rcept_tm if rcept_dt and rcept_tm else ''

        if stock_code not in self.last_disclosure_time:
            self.last_disclosure_time[stock_code] = latest_time
            return
        
        if latest_time and latest_time > self.last_disclosure_time[stock_code]: # Check if latest_time is not empty
            new_disclosures = [
                item for item in disclosures
                if item.get('rcept_dt', '') + item.get('rcept_tm', '') > self.last_disclosure_time[stock_code]
            ]
            
            if new_disclosures:
                message = self._format_disclosure_message(stock_name, new_disclosures)
                
                for user_id in user_ids:
                    try:
                        # Redis에 알림 저장
                        await db.redis.set(
                            f"notification:{user_id}:{stock_code}",
                            message,
                            ex=3600  # 1시간 유효
                        )
                    except Exception as e:
                        logger.error(f"Redis 저장 중 오류 발생: {e}")
                
                self.last_disclosure_time[stock_code] = latest_time
                logger.info(f"{stock_name}의 새로운 공시 {len(new_disclosures)}건 발견")

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

disclosure_service = DisclosureService() 
