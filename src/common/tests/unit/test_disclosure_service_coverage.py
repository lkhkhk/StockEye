import pytest
from unittest.mock import MagicMock, patch, AsyncMock, ANY
from src.common.services.disclosure_service import DisclosureService
from src.common.models.system_config import SystemConfig
from src.common.models.disclosure import Disclosure
import os

@pytest.fixture
def disclosure_service():
    """DisclosureService 인스턴스를 생성하는 pytest fixture"""
    return DisclosureService()

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.send_telegram_message', new_callable=AsyncMock)
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
@patch.dict(os.environ, {"TELEGRAM_ADMIN_ID": "123"})
async def test_check_and_notify_new_disclosures_sends_admin_summary_isolated(
    mock_dart_get_disclosures, mock_send_telegram_message, disclosure_service
):
    """
    check_and_notify_new_disclosures: 관리자에게 요약 메시지를 보내는지 독립적으로 테스트
    """
    # Given
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = None  # No last_checked_rcept_no

    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101', 'corp_code': '123', 'stock_code': '005930'}
    ]
    mock_dart_get_disclosures.return_value = dart_data
    mock_db_session.query.return_value.filter.return_value.all.return_value = [] # no subscriptions

    # When
    await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    mock_send_telegram_message.assert_called_once_with(123, ANY)