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

        latest_time = disclosures[0]['rcept_dt'] + disclosures[0]['rcept_tm']
        
        if stock_code not in self.last_disclosure_time:
            self.last_disclosure_time[stock_code] = latest_time
            return
        
        if latest_time > self.last_disclosure_time[stock_code]:
            new_disclosures = [
                item for item in disclosures
                if item['rcept_dt'] + item['rcept_tm'] > self.last_disclosure_time[stock_code]
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
            date_str = f"{item['rcept_dt'][:4]}-{item['rcept_dt'][4:6]}-{item['rcept_dt'][6:]}"
            time_str = f"{item['rcept_tm'][:2]}:{item['rcept_tm'][2:4]}"
            report_link = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item['rcept_no']}"
            
            message += f"📄 <b>{item['report_nm']}</b>\n"
            message += f"⏰ {date_str} {time_str}\n"
            message += f"🔗 <a href='{report_link}'>공시 보기</a>\n\n"
        
        return message

disclosure_service = DisclosureService() 