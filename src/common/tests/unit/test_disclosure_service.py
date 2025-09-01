import pytest
from unittest.mock import MagicMock, patch, AsyncMock, ANY
from src.common.services.disclosure_service import DisclosureService, _parse_disclosure_type
from src.common.models.disclosure import Disclosure
from src.common.models.system_config import SystemConfig
from src.common.models.price_alert import PriceAlert
from src.common.models.user import User
from src.common.models.stock_master import StockMaster
from src.common.utils.exceptions import DartApiError
from datetime import datetime, timedelta
import os
import logging # logging 모듈 임포트

@pytest.fixture
def disclosure_service():
    """DisclosureService 인스턴스를 생성하는 pytest fixture"""
    return DisclosureService()

@pytest.mark.parametrize(
    "report_nm, expected_type",
    [
        ("[기재정정]사업보고서", "사업보고서"),
        (" 사업보고서", "사업보고서"),
        ("분기보고서", "분기보고서"),
        ("[첨부정정]반기보고서 (2023.06)", "반기보고서 (2023.06)"),
        ("", ""),
        (None, ""),
    ],
)
def test_parse_disclosure_type(report_nm, expected_type):
    """_parse_disclosure_type: 다양한 형식의 보고서명에서 정확한 유형을 추출하는지 테스트"""
    assert _parse_disclosure_type(report_nm) == expected_type

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
@patch('src.common.services.disclosure_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_new_disclosures_success(mock_send_telegram_message, mock_dart_get_disclosures, disclosure_service):
    """check_and_notify_new_disclosures: 새로운 공시를 성공적으로 확인하고 알림을 보내는 경우"""
    # Given
    mock_db_session = MagicMock()
    
    # Mock for db.query().filter().first() calls
    # First call (SystemConfig): returns None (initial run)
    # Second call (Disclosure): returns None (no existing disclosure)
    # Third call (StockMaster): returns StockMaster
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        None, # SystemConfig
        None, # Disclosure
        StockMaster(symbol='005930', name='삼성전자') # StockMaster
    ]

    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101', 'corp_code': '123', 'stock_code': '005930'}
    ]
    mock_dart_get_disclosures.return_value = dart_data

    # Mock for subscriptions and users
    mock_db_session.query.return_value.filter.return_value.all.side_effect = [
        [PriceAlert(user_id=1, symbol='005930', notify_on_disclosure=True, is_active=True)], # subscriptions
        [User(id=1, telegram_id=123)] # users
    ]

    # When
    await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    mock_db_session.bulk_save_objects.assert_called_once()
    mock_db_session.commit.assert_called()
    mock_send_telegram_message.assert_called()

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_update_disclosures_success(mock_dart_get_disclosures, disclosure_service):
    """update_disclosures: 신규 공시를 성공적으로 DB에 저장하는 경우"""
    # Given
    mock_db_session = MagicMock()
    corp_code = "00126380"
    stock_code = "005930"
    stock_name = "삼성전자"

    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101'}
    ]
    mock_dart_get_disclosures.return_value = dart_data
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # When
    result = await disclosure_service.update_disclosures(mock_db_session, corp_code, stock_code, stock_name)

    # Then
    assert result['success'] is True
    assert result['inserted'] == 1
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_update_disclosures_skip_existing(mock_dart_get_disclosures, disclosure_service):
    """update_disclosures: 이미 DB에 있는 공시를 건너뛰는 경우"""
    # Given
    mock_db_session = MagicMock()
    corp_code = "00126380"
    stock_code = "005930"
    stock_name = "삼성전자"

    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101'}
    ]
    mock_dart_get_disclosures.return_value = dart_data
    mock_db_session.query.return_value.filter.return_value.first.return_value = Disclosure()

    # When
    result = await disclosure_service.update_disclosures(mock_db_session, corp_code, stock_code, stock_name)

    # Then
    assert result['success'] is True
    assert result['inserted'] == 0
    assert result['skipped'] == 1
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_update_disclosures_api_error(mock_dart_get_disclosures, disclosure_service):
    """update_disclosures: DART API 호출 시 예외가 발생하는 경우"""
    # Given
    mock_db_session = MagicMock()
    error_message = "DART Error"
    mock_dart_get_disclosures.side_effect = Exception(error_message)

    # When
    result = await disclosure_service.update_disclosures(
        mock_db_session, "00126380", "005930", "삼성전자"
    )

    # Then
    assert result['success'] is False
    assert error_message in result['errors']
    mock_db_session.rollback.assert_called_once()

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_update_disclosures_for_all_stocks_success(mock_dart_get_disclosures, disclosure_service):
    """update_disclosures_for_all_stocks: 전체 공시를 성공적으로 업데이트하는 경우"""
    # Given
    mock_db_session = MagicMock()
    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101', 'stock_code': '005930', 'corp_code': '123'},
        {'rcept_no': '202301020000002', 'report_nm': '분기보고서', 'rcept_dt': '20230102', 'stock_code': '000660', 'corp_code': '456'}
    ]
    mock_dart_get_disclosures.return_value = dart_data
    mock_db_session.query.return_value.filter.return_value.all.return_value = [] # No existing disclosures

    # When
    result = await disclosure_service.update_disclosures_for_all_stocks(mock_db_session)

    # Then
    assert result['success'] is True
    assert result['inserted'] == 2
    assert result['skipped'] == 0
    mock_db_session.bulk_save_objects.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_update_disclosures_for_all_stocks_skip_existing(mock_dart_get_disclosures, disclosure_service):
    """update_disclosures_for_all_stocks: 기존 공시를 건너뛰는 경우"""
    # Given
    mock_db_session = MagicMock()
    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101', 'stock_code': '005930', 'corp_code': '123'}
    ]
    mock_dart_get_disclosures.return_value = dart_data
    mock_db_session.query.return_value.filter.return_value.all.return_value = [('20230101000001',)] # Existing disclosure

    # When
    result = await disclosure_service.update_disclosures_for_all_stocks(mock_db_session)

    # Then
    assert result['success'] is True
    assert result['inserted'] == 0
    assert result['skipped'] == 1
    mock_db_session.bulk_save_objects.assert_not_called()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_update_disclosures_for_all_stocks_api_error(mock_dart_get_disclosures, disclosure_service):
    """update_disclosures_for_all_stocks: DART API 호출 시 예외가 발생하는 경우"""
    # Given
    mock_db_session = MagicMock()
    error_message = "API Error"
    mock_dart_get_disclosures.side_effect = Exception(error_message)

    # When
    result = await disclosure_service.update_disclosures_for_all_stocks(mock_db_session)

    # Then
    assert result['success'] is False
    assert error_message in result['errors']
    mock_db_session.rollback.assert_called_once()

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
@patch('src.common.services.disclosure_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_new_disclosures_no_latest_disclosures(mock_send_telegram_message, mock_dart_get_disclosures, disclosure_service, caplog):
    """check_and_notify_new_disclosures: dart_get_disclosures가 빈 리스트를 반환하는 경우"""
    # Given
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = None # last_checked_config
    mock_dart_get_disclosures.return_value = [] # No latest disclosures

    # When
    with caplog.at_level(logging.INFO, logger='src.common.services.disclosure_service'):
        await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    mock_dart_get_disclosures.assert_called_once()
    mock_db_session.bulk_save_objects.assert_not_called()
    mock_db_session.commit.assert_not_called()
    mock_send_telegram_message.assert_not_called()
    assert "새로운 공시가 없습니다." in caplog.text

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
@patch('src.common.services.disclosure_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_new_disclosures_no_new_disclosures_after_filter(mock_send_telegram_message, mock_dart_get_disclosures, disclosure_service, caplog):
    """check_and_notify_new_disclosures: last_checked_rcept_no가 있고, 필터링 후 신규 공시가 없는 경우"""
    # Given
    mock_db_session = MagicMock()
    mock_config = MagicMock(spec=SystemConfig, value='20230101000001')
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config # last_checked_config
    
    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101', 'corp_code': '123', 'stock_code': '005930'}
    ]
    mock_dart_get_disclosures.return_value = dart_data

    # When
    with caplog.at_level(logging.INFO, logger='src.common.services.disclosure_service'):
        await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    mock_dart_get_disclosures.assert_called_once()
    mock_db_session.bulk_save_objects.assert_not_called()
    mock_db_session.commit.assert_not_called()
    mock_send_telegram_message.assert_not_called()
    assert "신규 공시가 없습니다. (DB 기준: 20230101000001)" in caplog.text

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
@patch('src.common.services.disclosure_service.send_telegram_message', new_callable=AsyncMock)
@patch.dict(os.environ, {"TELEGRAM_ADMIN_ID": "123"}) # Admin ID를 모의
async def test_check_and_notify_new_disclosures_no_stock_code_for_notification(mock_send_telegram_message, mock_dart_get_disclosures, disclosure_service, caplog):
    """check_and_notify_new_disclosures: 공시 항목에 stock_code가 없어 알림이 건너뛰어지는 경우"""
    # Given
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        None, # SystemConfig
        None, # Disclosure
        None # StockMaster (stock_info)
    ]

    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101', 'corp_code': '123', 'stock_code': None} # stock_code is None
    ]
    mock_dart_get_disclosures.return_value = dart_data

    mock_db_session.query.return_value.filter.return_value.all.side_effect = [
        [], # subscriptions
        [] # users
    ]

    # When
    with caplog.at_level(logging.DEBUG, logger='src.common.services.disclosure_service'):
        await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    mock_db_session.bulk_save_objects.assert_called_once()
    mock_db_session.commit.assert_called()
    mock_send_telegram_message.assert_called_once() # Admin message should still be sent
    assert "상장되지 않은 기업 공시 알림 건너뛰기" in caplog.text

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
@patch('src.common.services.disclosure_service.send_telegram_message', new_callable=AsyncMock)
@patch.dict(os.environ, {"TELEGRAM_ADMIN_ID": "123"}) # Admin ID를 모의
async def test_check_and_notify_new_disclosures_no_subscriptions(mock_send_telegram_message, mock_dart_get_disclosures, disclosure_service, caplog):
    """check_and_notify_new_disclosures: 공시 알림 구독자가 없는 경우"""
    # Given
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        None, # SystemConfig
        None, # Disclosure
        StockMaster(symbol='005930', name='삼성전자') # StockMaster
    ]

    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101', 'corp_code': '123', 'stock_code': '005930'}
    ]
    mock_dart_get_disclosures.return_value = dart_data

    mock_db_session.query.return_value.filter.return_value.all.side_effect = [
        [], # subscriptions (empty)
        [] # users
    ]

    # When
    with caplog.at_level(logging.DEBUG):
        await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    mock_db_session.bulk_save_objects.assert_called_once()
    mock_db_session.commit.assert_called()
    mock_send_telegram_message.assert_called_once() # Only admin message should be sent
    assert "종목 005930에 대한 활성 공시 알림 구독자가 없습니다." in caplog.text

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
@patch('src.common.services.disclosure_service.send_telegram_message', new_callable=AsyncMock)
@patch.dict(os.environ, {"TELEGRAM_ADMIN_ID": "123"}) # Admin ID를 모의
async def test_check_and_notify_new_disclosures_no_telegram_id(mock_send_telegram_message, mock_dart_get_disclosures, disclosure_service, caplog):
    """check_and_notify_new_disclosures: 사용자에게 텔레그램 ID가 없는 경우"""
    # Given
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        None, # SystemConfig
        None, # Disclosure
        StockMaster(symbol='005930', name='삼성전자') # StockMaster
    ]

    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101', 'corp_code': '123', 'stock_code': '005930'}
    ]
    mock_dart_get_disclosures.return_value = dart_data

    mock_db_session.query.return_value.filter.return_value.all.side_effect = [
        [PriceAlert(user_id=1, symbol='005930', notify_on_disclosure=True, is_active=True)], # subscriptions
        [User(id=1, telegram_id=None)] # users (telegram_id is None)
    ]

    # When
    with caplog.at_level(logging.INFO):
        await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    mock_db_session.bulk_save_objects.assert_called_once()
    mock_db_session.commit.assert_called()
    mock_send_telegram_message.assert_called_once() # Only admin message should be sent
    assert "사용자 1의 Telegram ID가 없어 알림" in caplog.text

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
@patch('src.common.services.disclosure_service.send_telegram_message', new_callable=AsyncMock)
@patch.dict(os.environ, {"TELEGRAM_ADMIN_ID": ""}) # Admin ID를 비워둠
async def test_check_and_notify_new_disclosures_no_admin_id(mock_send_telegram_message, mock_dart_get_disclosures, disclosure_service, caplog):
    """check_and_notify_new_disclosures: 관리자 ID가 설정되지 않아 요약 리포트가 전송되지 않는 경우"""
    # Given
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        None, # SystemConfig
        None, # Disclosure
        StockMaster(symbol='005930', name='삼성전자') # StockMaster
    ]

    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101', 'corp_code': '123', 'stock_code': '005930'}
    ]
    mock_dart_get_disclosures.return_value = dart_data

    mock_db_session.query.return_value.filter.return_value.all.side_effect = [
        [], # subscriptions (empty) - Ensure no user notifications are sent
        [] # users
    ]

    # When
    with caplog.at_level(logging.INFO):
        await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    mock_db_session.bulk_save_objects.assert_called_once()
    mock_db_session.commit.assert_called()
    mock_send_telegram_message.assert_not_called() # Admin message should NOT be sent
    assert "TELEGRAM_ADMIN_ID" not in os.environ or os.environ["TELEGRAM_ADMIN_ID"] == "" # 환경 변수가 비어있는지 확인


@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_check_and_notify_new_disclosures_dart_api_error_020(mock_dart_get_disclosures, disclosure_service, caplog):
    """check_and_notify_new_disclosures: DART API가 020 에러(사용 한도 초과)를 반환하는 경우"""
    # Given
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = None # last_checked_config
    mock_dart_get_disclosures.side_effect = DartApiError("API limit exceeded", "020")

    # When
    with caplog.at_level(logging.CRITICAL):
        await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    assert "DART API 사용 한도를 초과했습니다" in caplog.text

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_check_and_notify_new_disclosures_dart_api_other_error(mock_dart_get_disclosures, disclosure_service, caplog):
    """check_and_notify_new_disclosures: DART API가 기타 에러를 반환하는 경우"""
    # Given
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = None # last_checked_config
    mock_dart_get_disclosures.side_effect = DartApiError("Some other error", "999")

    # When
    with caplog.at_level(logging.ERROR):
        await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    assert "DART 공시 조회 중 API 오류 발생" in caplog.text

@pytest.mark.asyncio
async def test_check_and_notify_new_disclosures_unexpected_error(disclosure_service, caplog):
    """check_and_notify_new_disclosures: 예상치 못한 예외가 발생하는 경우"""
    # Given
    mock_db_session = MagicMock()
    mock_db_session.query.side_effect = Exception("Unexpected DB error")

    # When
    with caplog.at_level(logging.ERROR):
        await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    mock_db_session.rollback.assert_called_once()
    assert "신규 공시 확인 및 알림 작업 중 예상치 못한 오류 발생" in caplog.text
    assert "Unexpected DB error" in caplog.text

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_check_and_notify_new_disclosures_dart_api_other_error_logging(mock_dart_get_disclosures, disclosure_service, caplog):
    """check_and_notify_new_disclosures: DART API가 기타 에러를 반환할 때 로깅이 올바르게 동작하는지 테스트"""
    # Given
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = None # last_checked_config
    mock_dart_get_disclosures.side_effect = DartApiError("Some other error", "999")

    # When
    with caplog.at_level(logging.ERROR):
        await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    assert "DART 공시 조회 중 API 오류 발생" in caplog.text

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_check_and_notify_new_disclosures_existing_config(mock_dart_get_disclosures, disclosure_service):
    """check_and_notify_new_disclosures: last_checked_config가 존재하지만 value가 None일 경우"""
    # Given
    mock_db_session = MagicMock()
    mock_config = MagicMock(spec=SystemConfig, value=None)
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config
    
    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101', 'corp_code': '123', 'stock_code': '005930'}
    ]
    mock_dart_get_disclosures.return_value = dart_data
    mock_db_session.query.return_value.filter.return_value.all.return_value = []

    # When
    await disclosure_service.check_and_notify_new_disclosures(mock_db_session)

    # Then
    assert mock_config.value == '20230101000001'
    mock_db_session.commit.assert_called()

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.send_telegram_message', new_callable=AsyncMock)
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
@patch.dict(os.environ, {"TELEGRAM_ADMIN_ID": "123"})
async def test_check_and_notify_new_disclosures_sends_admin_summary(
    mock_dart_get_disclosures, mock_send_telegram_message, disclosure_service
):
    """
    check_and_notify_new_disclosures: 관리자에게 요약 메시지를 보내는지 테스트 (더 구체적으로)
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
    mock_send_telegram_message.assert_called_once()
    admin_id, summary_msg = mock_send_telegram_message.call_args[0]
    assert admin_id == 123
    assert "공시 알림 요약 리포트" in summary_msg
    assert "발견된 신규 공시: 1건" in summary_msg
    assert "DB에 추가된 공시: 1건" in summary_msg
    assert "총 알림 발송 건수: 0건" in summary_msg

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_update_disclosures_for_all_stocks_no_disclosures(mock_dart_get_disclosures, disclosure_service):
    """update_disclosures_for_all_stocks: DART에서 가져온 공시가 없을 때"""
    # Given
    mock_db_session = MagicMock()
    mock_dart_get_disclosures.return_value = []

    # When
    result = await disclosure_service.update_disclosures_for_all_stocks(mock_db_session)

    # Then
    assert result['success'] is True
    assert result['inserted'] == 0
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_update_disclosures_for_all_stocks_missing_data(mock_dart_get_disclosures, disclosure_service):
    """update_disclosures_for_all_stocks: 공시 데이터에 rcept_no 또는 stock_code가 없을 때"""
    # Given
    mock_db_session = MagicMock()
    dart_data = [
        {'rcept_no': '20230101000001', 'report_nm': '사업보고서', 'rcept_dt': '20230101', 'corp_code': '123', 'stock_code': None},
        {'report_nm': '사업보고서', 'rcept_dt': '20230101', 'corp_code': '123', 'stock_code': '005930'}
    ]
    mock_dart_get_disclosures.return_value = dart_data
    mock_db_session.query.return_value.filter.return_value.all.return_value = []

    # When
    result = await disclosure_service.update_disclosures_for_all_stocks(mock_db_session)

    # Then
    assert result['success'] is True
    assert result['inserted'] == 0

@pytest.mark.asyncio
@patch('src.common.services.disclosure_service.dart_get_disclosures', new_callable=AsyncMock)
async def test_update_disclosures_missing_rcept_no(mock_dart_get_disclosures, disclosure_service):
    """update_disclosures: 공시 데이터에 rcept_no가 없을 때"""
    # Given
    mock_db_session = MagicMock()
    dart_data = [
        {'report_nm': '사업보고서', 'rcept_dt': '20230101'}
    ]
    mock_dart_get_disclosures.return_value = dart_data

    # When
    result = await disclosure_service.update_disclosures(mock_db_session, "00126380", "005930", "삼성전자")

    # Then
    assert result['success'] is True
    assert result['inserted'] == 0
    assert len(result['errors']) == 1
    assert "공시 항목에 rcept_no 없음" in result['errors'][0]