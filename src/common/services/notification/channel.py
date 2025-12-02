from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class NotificationChannel(ABC):
    """알림 채널을 위한 추상 기본 클래스입니다."""

    @abstractmethod
    async def send(self, recipient: str, message: str, **kwargs) -> bool:
        """
        메시지를 전송합니다.

        Args:
            recipient (str): 수신자 식별자 (예: chat_id, email)
            message (str): 전송할 메시지 내용
            **kwargs: 채널별 추가 옵션

        Returns:
            bool: 전송 성공 여부
        """
        pass
