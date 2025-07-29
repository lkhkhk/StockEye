import pytest
from unittest.mock import patch, MagicMock
import logging
from src.api.services.stock_service import StockService
from src.common.exceptions import DartApiError
from datetime import date, timedelta, datetime
from src.api.models.system_config import SystemConfig
from src.api.models.stock_master import StockMaster
from src.api.models.user import User
from src.api.models.price_alert import PriceAlert
import os

class TestStockService:
    @pytest.fixture
    def stock_service(self):
        return StockService()

    @pytest.mark.asyncio
    @patch('src.api.services.stock_service.dart_get_disclosures')
    @patch('src.common.notify_service.send_telegram_message')
    @patch('src.api.models.system_config.SystemConfig') # SystemConfig 모델을 패치
    async def test_check_and_notify_new_disclosures_no_new_disclosures(self, mock_system_config, mock_send_telegram_message, mock_dart_get_disclosures, stock_service, real_db, caplog):
        """새로운 공시가 없는 경우 (DB에 마지막 확인 번호가 있고, 신규 공시가 없는 경우)"""
        with caplog.at_level(logging.INFO):
            # GIVEN
            # 마지막 확인 공시 번호 설정
            mock_config = MagicMock(spec=SystemConfig)
            mock_config.value = '202301010000001'
            
            # real_db.query().filter().return_value.first.return_value를 모의하여 mock_config를 반환하도록 설정
            with patch.object(real_db, 'query') as mock_real_db_query:
                mock_real_db_query.return_value.filter.return_value.first.return_value = mock_config

                # DART API가 기존 공시만 반환하도록 모의
                mock_dart_get_disclosures.return_value = [
                    {"rcept_no": "202301010000001", "corp_name": "기존회사", "report_nm": "기존보고서", "rcept_dt": "20230101"}
                ]

                # WHEN
                await stock_service.check_and_notify_new_disclosures(real_db)

                # THEN
                mock_dart_get_disclosures.assert_called_once()
                mock_send_telegram_message.assert_not_called()
                assert "신규 공시가 없습니다." in caplog.text

    @pytest.mark.asyncio
    @patch('src.api.services.stock_service.dart_get_disclosures')
    @patch('src.common.notify_service.send_telegram_message')
    @patch('src.api.models.system_config.SystemConfig') # SystemConfig 모델을 패치
    async def test_check_and_notify_new_disclosures_initial_run(self, mock_system_config, mock_send_telegram_message, mock_dart_get_disclosures, stock_service, real_db, caplog):
        """최초 실행 시 기준점 설정 테스트"""
        with caplog.at_level(logging.INFO):
            # GIVEN
            # DB에 last_checked_rcept_no 없음 (real_db.query().first()가 None을 반환하도록 기본 설정)
            with patch.object(real_db, 'query') as mock_real_db_query:
                mock_real_db_query.return_value.filter.return_value.first.return_value = None

                mock_dart_get_disclosures.return_value = [
                    {"rcept_no": "202301020000001", "corp_name": "새회사", "report_nm": "새보고서", "rcept_dt": "20230102"},
                    {"rcept_no": "202301010000001", "corp_name": "기존회사", "report_nm": "기존보고서", "rcept_dt": "20230101"}
                ]

                # WHEN
                await stock_service.check_and_notify_new_disclosures(real_db)

                # THEN
                mock_dart_get_disclosures.assert_called_once()
                mock_send_telegram_message.assert_not_called()
                assert "최초 실행. 기준 접수번호를 202301020000001로 DB에 설정합니다." in caplog.text
                # real_db.add가 호출되었는지 확인
                with patch.object(real_db, 'add') as mock_real_db_add:
                    with patch.object(real_db, 'commit') as mock_real_db_commit:
                        await stock_service.check_and_notify_new_disclosures(real_db)
                        mock_real_db_add.assert_called_once()
                        mock_real_db_commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.api.services.stock_service.dart_get_disclosures')
    @patch('src.common.notify_service.send_telegram_message')
    @patch('src.api.models.system_config.SystemConfig') # SystemConfig 모델을 패치
    @patch('src.api.models.stock_master.StockMaster') # StockMaster 모델을 패치
    @patch('src.api.models.user.User') # User 모델을 패치
    @patch('src.api.models.price_alert.PriceAlert') # PriceAlert 모델을 패치
    async def test_check_and_notify_new_disclosures_success(self, mock_price_alert, mock_user, mock_stock_master, mock_system_config, mock_send_telegram_message, mock_dart_get_disclosures, stock_service, real_db, caplog):
        """신규 공시 알림 성공 테스트"""
        with caplog.at_level(logging.INFO):
            # GIVEN
            # 마지막 확인 공시 번호 설정
            mock_config_initial = MagicMock(spec=SystemConfig)
            mock_config_initial.value = '202301010000001'
            print(f"DEBUG: mock_config_initial.value = {mock_config_initial.value}")

            mock_stock_master_samsung = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자", corp_code="0012345")
            mock_user_1 = MagicMock(spec=User, id=1, telegram_id=123, username="testuser", password_hash="hashed", email="test@example.com")
            mock_price_alert_samsung = MagicMock(spec=PriceAlert, user_id=1, symbol="005930", target_price=100, notify_on_disclosure=True, is_active=True)

            # Create a mock for real_db.query() that can handle different filter calls
            with patch.object(real_db, 'query') as mock_real_db_query:
                # Configure side_effect for filter.return_value.first() calls
                mock_real_db_query.return_value.filter.return_value.first.side_effect = [
                    mock_config_initial, # First call for SystemConfig
                    mock_stock_master_samsung, # First call for StockMaster
                    mock_stock_master_samsung, # Second call for StockMaster
                    mock_config_initial # Final call for SystemConfig assertion
                ]

                # Configure side_effect for filter.return_value.all() calls
                mock_real_db_query.return_value.filter.return_value.all.side_effect = [
                    [mock_price_alert_samsung], # First call for PriceAlert
                    [mock_user_1], # First call for User
                    [mock_price_alert_samsung], # Second call for PriceAlert
                    [mock_user_1] # Second call for User
                ]

                # DART API가 신규 공시를 반환하도록 모의
                mock_dart_get_disclosures.return_value = [
                    {"rcept_no": "202301020000002", "corp_name": "삼성전자", "report_nm": "신규보고서2", "rcept_dt": "20230102", "stock_code": "005930", "corp_code": "0012345"},
                    {"rcept_no": "202301020000001", "corp_name": "삼성전자", "report_nm": "신규보고서1", "rcept_dt": "20230102", "stock_code": "005930", "corp_code": "0012345"},
                    {"rcept_no": "202301010000001", "corp_name": "기존회사", "report_nm": "기존보고서", "rcept_dt": "20230101", "stock_code": "000000", "corp_code": "0000000"}
                ]
                os.environ["TELEGRAM_ADMIN_ID"] = "456"

                # WHEN
                await stock_service.check_and_notify_new_disclosures(real_db)

                # THEN
                mock_dart_get_disclosures.assert_called_once()
                assert mock_send_telegram_message.call_count == 3 # 사용자 2명 + 관리자 1명
                # 사용자 알림 확인
                mock_send_telegram_message.assert_any_call(123, "🔔 [삼성전자] 신규 공시\n\n📑 신규보고서1\n🕒 20230102\n🔗 https://dart.fss.or.kr/dsaf001/main.do?rcpNo=202301020000001")
                mock_send_telegram_message.assert_any_call(123, "🔔 [삼성전자] 신규 공시\n\n📑 신규보고서2\n🕒 20230102\n🔗 https://dart.fss.or.kr/dsaf001/main.do?rcpNo=202301020000002")
                # 관리자 알림 확인
                mock_send_telegram_message.assert_any_call(456, "📈 공시 알림 요약 리포트\n\n- 발견된 신규 공시: 2건\n- 총 알림 발송 건수: 2건")
                # config 객체를 모의하여 value 속성을 가질 수 있도록 함
                mock_config_final = MagicMock(spec=SystemConfig, value='202301020000002')
                mock_real_db_query.return_value.filter.return_value.first.side_effect = [
                    mock_config_initial, # First call for SystemConfig
                    mock_stock_master_samsung, # First call for StockMaster
                    mock_stock_master_samsung, # Second call for StockMaster
                    mock_config_final # Final call for SystemConfig assertion
                ]
                config = real_db.query(SystemConfig).filter(SystemConfig.key == 'last_checked_rcept_no').first()
                assert config.value == '202301020000002'
                assert "2건의 신규 공시를 발견했습니다." in caplog.text
                assert "마지막 확인 접수번호를 202301020000002로 DB에 갱신합니다." in caplog.text

    @pytest.mark.asyncio
    @patch('src.api.services.stock_service.dart_get_disclosures')
    @patch('src.common.notify_service.send_telegram_message')
    @patch('src.api.models.system_config.SystemConfig') # SystemConfig 모델을 패치
    async def test_check_and_notify_new_disclosures_dart_api_limit_exceeded(self, mock_system_config, mock_send_telegram_message, mock_dart_get_disclosures, stock_service, real_db, caplog):
        """DART API 사용 한도 초과 오류 처리 테스트"""
        with caplog.at_level(logging.CRITICAL):
            # GIVEN
            mock_dart_get_disclosures.side_effect = DartApiError("사용 한도 초과", status_code="020")

            # real_db.query().filter().first()를 모의하여 None을 반환하도록 설정
            with patch.object(real_db, 'query') as mock_real_db_query:
                mock_real_db_query.return_value.filter.return_value.first.return_value = None

                # WHEN
                with patch.object(real_db, 'rollback') as mock_real_db_rollback:
                    await stock_service.check_and_notify_new_disclosures(real_db)

                    # THEN
                    mock_dart_get_disclosures.assert_called_once()
                    mock_send_telegram_message.assert_not_called()
                    assert "DART API 사용 한도를 초과했습니다" in caplog.text
                    mock_real_db_rollback.assert_not_called() # 오류 발생 시 롤백되지 않아야 함

    @pytest.mark.asyncio
    @patch('src.api.services.stock_service.dart_get_disclosures')
    @patch('src.common.notify_service.send_telegram_message')
    @patch('src.api.models.system_config.SystemConfig') # SystemConfig 모델을 패치
    async def test_check_and_notify_new_disclosures_other_dart_api_error(self, mock_system_config, mock_send_telegram_message, mock_dart_get_disclosures, stock_service, real_db, caplog):
        """기타 DART API 오류 처리 테스트"""
        with caplog.at_level(logging.ERROR):
            # GIVEN
            mock_dart_get_disclosures.side_effect = DartApiError("기타 API 오류", status_code="999")

            # real_db.query().filter().first()를 모의하여 None을 반환하도록 설정
            with patch.object(real_db, 'query') as mock_real_db_query:
                mock_real_db_query.return_value.filter.return_value.first.return_value = None

                # WHEN
                with patch.object(real_db, 'rollback') as mock_real_db_rollback:
                    await stock_service.check_and_notify_new_disclosures(real_db)

                    # THEN
                    mock_dart_get_disclosures.assert_called_once()
                    mock_send_telegram_message.assert_not_called()
                    assert "DART 공시 조회 중 API 오류 발생" in caplog.text
                    mock_real_db_rollback.assert_not_called() # 오류 발생 시 롤백되지 않아야 함

    @pytest.mark.asyncio
    @patch('src.api.services.stock_service.dart_get_disclosures')
    @patch('src.common.notify_service.send_telegram_message')
    @patch('src.api.models.system_config.SystemConfig') # SystemConfig 모델을 패치
    async def test_check_and_notify_new_disclosures_unexpected_error(self, mock_system_config, mock_send_telegram_message, mock_dart_get_disclosures, stock_service, real_db, caplog):
        """예상치 못한 오류 발생 시 롤백 및 로깅 테스트"""
        with caplog.at_level(logging.ERROR):
            # GIVEN
            mock_dart_get_disclosures.side_effect = Exception("예상치 못한 오류")

            # real_db.query().filter().first()를 모의하여 None을 반환하도록 설정
            with patch.object(real_db, 'query') as mock_real_db_query:
                mock_real_db_query.filter.return_value.first.return_value = None

                # WHEN
                with patch.object(real_db, 'rollback') as mock_real_db_rollback:
                    await stock_service.check_and_notify_new_disclosures(real_db)

                    # THEN
                    mock_dart_get_disclosures.assert_called_once()
                    mock_send_telegram_message.assert_not_called()
                    assert "신규 공시 확인 및 알림 작업 중 예상치 못한 오류 발생" in caplog.text
                    mock_real_db_rollback.assert_called_once() # 롤백이 호출되어야 함 