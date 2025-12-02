"""
이메일 전송 테스트 스크립트

Gmail SMTP를 통해 실제 이메일을 전송하여 설정이 올바른지 확인합니다.
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, '/app')

from src.common.services.notify_service import notification_service
from src.common.config.email_config import email_config


async def test_email_sending():
    """이메일 전송 테스트"""
    
    print("=" * 60)
    print("📧 이메일 전송 테스트")
    print("=" * 60)
    
    # 설정 확인
    print(f"\n✅ SMTP 설정 확인:")
    print(f"   Host: {email_config.smtp_host}")
    print(f"   Port: {email_config.smtp_port}")
    print(f"   Username: {email_config.smtp_username}")
    print(f"   Sender: {email_config.sender_email}")
    print(f"   Configured: {email_config.is_configured}")
    
    if not email_config.is_configured:
        print("\n❌ SMTP가 설정되지 않았습니다!")
        print("   .env.development 파일에 SMTP_USERNAME과 SMTP_PASSWORD를 설정하세요.")
        return False
    
    # 테스트 1: 기본 알림 이메일
    print(f"\n📨 테스트 1: 기본 알림 이메일 전송 중...")
    result1 = await notification_service.send_message(
        recipient="lkhkhk@gmail.com",
        message="StockEye 이메일 알림 테스트입니다.\n\n이 메시지가 수신되었다면 SMTP 설정이 올바르게 완료된 것입니다!",
        channel_name="email",
        subject="[StockEye] 이메일 알림 테스트"
    )
    
    if result1:
        print("   ✅ 기본 알림 이메일 전송 성공!")
    else:
        print("   ❌ 기본 알림 이메일 전송 실패")
        return False
    
    # 테스트 2: 가격 알림 템플릿 이메일
    print(f"\n📨 테스트 2: 가격 알림 템플릿 이메일 전송 중...")
    result2 = await notification_service.send_message(
        recipient="lkhkhk@gmail.com",
        message="삼성전자(005930)의 가격이 목표가에 도달했습니다!",
        channel_name="email",
        subject="[StockEye] 가격 알림 - 삼성전자",
        template="price_alert.html",
        template_vars={
            "symbol": "삼성전자 (005930)",
            "current_price": "70,000",
            "target_price": "70,000",
            "condition": "이상 (≥)"
        }
    )
    
    if result2:
        print("   ✅ 가격 알림 템플릿 이메일 전송 성공!")
    else:
        print("   ❌ 가격 알림 템플릿 이메일 전송 실패")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 모든 이메일 전송 테스트 성공!")
    print("=" * 60)
    print(f"\n📬 lkhkhk@gmail.com 메일함을 확인하세요.")
    print("   - 기본 알림 이메일 1통")
    print("   - 가격 알림 템플릿 이메일 1통")
    print("\n💡 스팸 폴더도 확인해보세요.")
    
    return True


if __name__ == "__main__":
    result = asyncio.run(test_email_sending())
    sys.exit(0 if result else 1)
