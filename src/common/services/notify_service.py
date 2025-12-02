import logging
import os
from typing import Dict, List, Optional, Any

from .notification.channel import NotificationChannel
from .notification.telegram_channel import TelegramChannel
from .notification.email_channel import EmailChannel

logger = logging.getLogger(__name__)

class NotificationService:
    """알림 서비스를 관리하는 클래스입니다."""
    
    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {
            'telegram': TelegramChannel(),
            'email': EmailChannel(),
        }

    async def send_message(self, recipient: str, message: str, channel_name: str = 'telegram', **kwargs) -> bool:
        """
        지정된 채널로 메시지를 전송합니다.

        Args:
            recipient (str): 수신자 식별자
            message (str): 메시지 내용
            channel_name (str): 채널 이름 ('telegram', 'email')
            **kwargs: 채널별 추가 옵션

        Returns:
            bool: 전송 성공 여부
        """
        channel = self.channels.get(channel_name)
        if not channel:
            logger.error(f"Unknown notification channel: {channel_name}")
            return False
            
        return await channel.send(recipient, message, **kwargs)

    async def broadcast(self, recipients: List[Dict[str, Any]], message: str, **kwargs):
        """
        여러 수신자에게 메시지를 전송합니다.
        
        Args:
            recipients (List[Dict]): 수신자 정보 목록
                - 기존 방식: [{'id': '...', 'channel': '...'}, ...]
                - 설정 기반: [{'targets': {'telegram': '...', 'email': '...'}, 'preferences': {'telegram': True, ...}}, ...]
            message (str): 메시지 내용
        """
        for recipient in recipients:
            # 설정 기반 다중 채널 발송
            if 'targets' in recipient and 'preferences' in recipient:
                targets = recipient['targets']
                preferences = recipient['preferences']
                
                for channel_name, target_id in targets.items():
                    # 설정이 True인 경우에만 발송
                    if preferences.get(channel_name, False):
                        await self.send_message(
                            recipient=target_id,
                            message=message,
                            channel_name=channel_name,
                            **kwargs
                        )
            # 기존 방식 지원 (단일 채널)
            elif 'id' in recipient:
                await self.send_message(
                    recipient=recipient['id'], 
                    message=message, 
                    channel_name=recipient.get('channel', 'telegram'),
                    **kwargs
                )

# 싱글톤 인스턴스
notification_service = NotificationService()

# 하위 호환성을 위한 함수
async def send_telegram_message(chat_id: int, text: str):
    """
    텔레그램 메시지를 전송합니다. (Deprecated: Use notification_service.send_message instead)
    """
    return await notification_service.send_message(str(chat_id), text, channel_name='telegram')