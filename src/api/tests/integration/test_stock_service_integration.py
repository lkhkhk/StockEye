import pytest
from unittest.mock import patch, MagicMock
import logging
from src.common.services.stock_service import StockService
from src.common.utils.exceptions import DartApiError
from datetime import date, timedelta, datetime
from src.common.models.system_config import SystemConfig
from src.common.models.stock_master import StockMaster
from src.common.models.user import User
from src.common.models.price_alert import PriceAlert
from src.common.models.daily_price import DailyPrice
from src.common.models.disclosure import Disclosure
import os
import yfinance as yf
import pandas as pd
from unittest.mock import ANY

class TestStockServiceIntegration:
    @pytest.fixture
    def stock_service(self):
        return StockService()

    @pytest.mark.asyncio
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    @patch('src.common.services.notify_service.send_telegram_message')
    @patch('src.common.models.system_config.SystemConfig') # SystemConfig 모델을 패치
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
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    @patch('src.common.services.notify_service.send_telegram_message')
    @patch('src.common.models.system_config.SystemConfig') # SystemConfig 모델을 패치
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
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    @patch('src.common.services.notify_service.send_telegram_message')
    @patch('src.common.models.system_config.SystemConfig') # SystemConfig 모델을 패치
    @patch('src.common.models.stock_master.StockMaster') # StockMaster 모델을 패치
    @patch('src.common.models.user.User') # User 모델을 패치
    @patch('src.common.models.price_alert.PriceAlert') # PriceAlert 모델을 패치
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
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    @patch('src.common.services.notify_service.send_telegram_message')
    @patch('src.common.models.system_config.SystemConfig') # SystemConfig 모델을 패치
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
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    @patch('src.common.services.notify_service.send_telegram_message')
    @patch('src.common.models.system_config.SystemConfig') # SystemConfig 모델을 패치
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
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    @patch('src.common.services.notify_service.send_telegram_message')
    @patch('src.common.models.system_config.SystemConfig') # SystemConfig 모델을 패치
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
                    assert real_db.rollback.called # 롤백이 호출되어야 함

    @pytest.mark.asyncio
    @patch('yfinance.download')
    async def test_update_daily_prices_success(self, mock_yfinance_download, stock_service):
        """일별시세 갱신 성공 테스트"""
        # GIVEN
        mock_db = MagicMock()
        
        stock1 = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자", corp_code="0012345")
        stock2 = MagicMock(spec=StockMaster, symbol="000660", name="SK하이닉스", corp_code="0012346")
        mock_db.query.return_value.all.return_value = [stock1, stock2]

        mock_df_samsung = pd.DataFrame({
            'Open': [70000, 71000],
            'High': [72000, 73000],
            'Low': [69000, 70000],
            'Close': [71500, 72500],
            'Volume': [1000000, 1200000]
        }, index=pd.to_datetime(['2025-07-29', '2025-07-28']))
        mock_df_skhynix = pd.DataFrame({
            'Open': [100000, 101000],
            'High': [102000, 103000],
            'Low': [99000, 100000],
            'Close': [101500, 102500],
            'Volume': [500000, 600000]
        }, index=pd.to_datetime(['2025-07-29', '2025-07-28']))

        mock_yfinance_download.side_effect = [mock_df_samsung, mock_df_skhynix]

        # WHEN
        result = await stock_service.update_daily_prices(mock_db)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 4 # 각 종목당 2일치 데이터
        assert len(result["errors"]) == 0

        assert mock_db.add.call_count == 4
        mock_db.commit.assert_called_once()

        mock_yfinance_download.assert_any_call("005930.KS", start=ANY, end=ANY)
        mock_yfinance_download.assert_any_call("000660.KS", start=ANY, end=ANY)

        # DailyPrice 객체가 올바른 인자로 생성되었는지 확인
        # 첫 번째 종목 (삼성전자)의 첫 번째 날짜 데이터
        assert isinstance(mock_db.add.call_args_list[0].args[0], DailyPrice)
        assert mock_db.add.call_args_list[0].args[0].symbol == "005930"
        assert mock_db.add.call_args_list[0].args[0].close == 71500

        # 첫 번째 종목 (삼성전자)의 두 번째 날짜 데이터
        assert isinstance(mock_db.add.call_args_list[1].args[0], DailyPrice)
        assert mock_db.add.call_args_list[1].args[0].symbol == "005930"
        assert mock_db.add.call_args_list[1].args[0].close == 72500

        # 두 번째 종목 (SK하이닉스)의 첫 번째 날짜 데이터
        assert isinstance(mock_db.add.call_args_list[2].args[0], DailyPrice)
        assert mock_db.add.call_args_list[2].args[0].symbol == "000660"
        assert mock_db.add.call_args_list[2].args[0].close == 101500

        # 두 번째 종목 (SK하이닉스)의 두 번째 날짜 데이터
        assert isinstance(mock_db.add.call_args_list[3].args[0], DailyPrice)
        assert mock_db.add.call_args_list[3].args[0].symbol == "000660"
        assert mock_db.add.call_args_list[3].args[0].close == 102500

    @pytest.mark.asyncio
    @patch('yfinance.download')
    async def test_update_daily_prices_no_data(self, mock_yfinance_download, stock_service):
        """일별시세 갱신 시 데이터가 없는 경우 테스트"""
        # GIVEN
        mock_db = MagicMock()
        stock1 = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자", market="KOSPI", corp_code="0012345")
        mock_db.query.return_value.all.return_value = [stock1]

        mock_yfinance_download.return_value = pd.DataFrame() # 빈 DataFrame 반환

        # WHEN
        result = await stock_service.update_daily_prices(mock_db)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 0
        assert "005930" in result["errors"] # 에러 종목에 포함되는지 확인

        mock_db.add.assert_not_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('yfinance.download')
    async def test_update_daily_prices_api_error(self, mock_yfinance_download, stock_service):
        """일별시세 갱신 시 API 오류 발생 테스트"""
        # GIVEN
        mock_db = MagicMock()
        stock1 = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자", market="KOSPI", corp_code="0012345")
        mock_db.query.return_value.all.return_value = [stock1]

        mock_yfinance_download.side_effect = Exception("API Error")

        # WHEN
        result = await stock_service.update_daily_prices(mock_db)

        # THEN
        assert result["success"] == True # 개별 종목 오류는 전체 성공으로 처리
        assert result["updated_count"] == 0
        assert "005930" in result["errors"] # 에러 종목에 포함되는지 확인

        mock_db.add.assert_not_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_price_and_change(self, stock_service):
        """현재가 및 등락률 조회 테스트"""
        # GIVEN
        mock_db = MagicMock()
        stock_symbol = "005930"
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        price_today = MagicMock(spec=DailyPrice, symbol=stock_symbol, date=today, open=70000, high=71000, low=69000, close=71500, volume=1000000)
        price_yesterday = MagicMock(spec=DailyPrice, symbol=stock_symbol, date=yesterday, open=69000, high=70000, low=68000, close=70500, volume=900000)
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            price_today, price_yesterday
        ]

        # WHEN
        result = stock_service.get_current_price_and_change(stock_symbol, mock_db)

        # THEN
        assert result["current_price"] == 71500
        assert result["change"] == 1000
        assert abs(result["change_rate"] - (1000 / 70500) * 100) < 0.001 # 부동소수점 비교

    @pytest.mark.asyncio
    async def test_get_current_price_and_change_no_data(self, stock_service):
        """현재가 및 등락률 조회 시 데이터가 없는 경우 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        # WHEN
        result = stock_service.get_current_price_and_change("NONEXIST", mock_db)

        # THEN
        assert result["current_price"] is None
        assert result["change"] is None
        assert result["change_rate"] is None

    @pytest.mark.asyncio
    async def test_get_current_price_and_change_only_one_day_data(self, stock_service):
        """현재가 및 등락률 조회 시 하루치 데이터만 있는 경우 테스트"""
        # GIVEN
        mock_db = MagicMock()
        stock_symbol = "005930"
        today = datetime.now().date()

        price_today = MagicMock(spec=DailyPrice, symbol=stock_symbol, date=today, open=70000, high=71000, low=69000, close=71500, volume=1000000)
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            price_today
        ]

        # WHEN
        result = stock_service.get_current_price_and_change(stock_symbol, mock_db)

        # THEN
        assert result["current_price"] == 71500
        assert result["change"] is None
        assert result["change_rate"] is None

    def test_get_stock_by_symbol_found(self, stock_service):
        """심볼로 종목 조회 시 종목이 존재하는 경우 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_stock = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        # WHEN
        result = stock_service.get_stock_by_symbol("005930", mock_db)

        # THEN
        assert result == mock_stock
        mock_db.query.assert_called_once_with(StockMaster)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_stock_by_symbol_not_found(self, stock_service):
        """심볼로 종목 조회 시 종목이 존재하지 않는 경우 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # WHEN
        result = stock_service.get_stock_by_symbol("NONEXIST", mock_db)

        # THEN
        assert result is None
        mock_db.query.assert_called_once_with(StockMaster)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_stock_by_name_found(self, stock_service):
        """이름으로 종목 조회 시 종목이 존재하는 경우 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_stock = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        # WHEN
        result = stock_service.get_stock_by_name("삼성전자", mock_db)

        # THEN
        assert result == mock_stock
        mock_db.query.assert_called_once_with(StockMaster)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_stock_by_name_not_found(self, stock_service):
        """이름으로 종목 조회 시 종목이 존재하지 않는 경우 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # WHEN
        result = stock_service.get_stock_by_name("없는종목", mock_db)

        # THEN
        assert result is None
        mock_db.query.assert_called_once_with(StockMaster)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_search_stocks_found(self, stock_service):
        """키워드로 종목 검색 시 종목이 존재하는 경우 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_stock1 = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자")
        mock_stock2 = MagicMock(spec=StockMaster, symbol="000660", name="SK하이닉스")
        mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_stock1, mock_stock2]

        # WHEN
        result = stock_service.search_stocks("삼성", mock_db)

        # THEN
        assert len(result) == 2
        assert result[0] == mock_stock1
        assert result[1] == mock_stock2
        mock_db.query.assert_called_once_with(StockMaster)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.limit.assert_called_once()
        mock_db.query.return_value.filter.return_value.limit.return_value.all.assert_called_once()

    def test_search_stocks_not_found(self, stock_service):
        """키워드로 종목 검색 시 종목이 존재하지 않는 경우 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = []

        # WHEN
        result = stock_service.search_stocks("없는키워드", mock_db)

        # THEN
        assert len(result) == 0
        mock_db.query.assert_called_once_with(StockMaster)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.limit.assert_called_once()
        mock_db.query.return_value.filter.return_value.limit.return_value.all.assert_called_once()

    def test_get_daily_prices_found(self, stock_service):
        """일별 시세 조회 시 데이터가 존재하는 경우 테스트"""
        # GIVEN
        mock_db = MagicMock()
        stock_symbol = "005930"
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        price_today = MagicMock(spec=DailyPrice, symbol=stock_symbol, date=today, close=71500)
        price_yesterday = MagicMock(spec=DailyPrice, symbol=stock_symbol, date=yesterday, close=70500)
        
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [
            price_today, price_yesterday
        ]

        # WHEN
        result = stock_service.get_daily_prices(stock_symbol, mock_db, days=2)

        # THEN
        assert len(result) == 2
        assert result[0] == price_today
        assert result[1] == price_yesterday
        mock_db.query.assert_called_once_with(DailyPrice)
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.api.services.stock_service.dart_get_all_stocks')
    async def test_update_stock_master_from_dart_success(self, mock_dart_get_all_stocks, stock_service):
        """DART API를 통해 종목 마스터 갱신 성공 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_dart_get_all_stocks.return_value = [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI", "corp_code": "0012345"},
            {"symbol": "000660", "name": "SK하이닉스", "market": "KOSPI", "corp_code": "0012346"}
        ]
        mock_db.query.return_value.filter.return_value.first.side_effect = [None, None] # 두 종목 모두 DB에 없다고 가정

        # WHEN
        result = await stock_service.update_stock_master(mock_db, use_dart=True)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 2
        mock_dart_get_all_stocks.assert_called_once()
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.api.services.stock_service.dart_get_all_stocks')
    async def test_update_stock_master_from_dart_update_existing(self, mock_dart_get_all_stocks, stock_service):
        """DART API를 통해 기존 종목 마스터 업데이트 테스트"""
        # GIVEN
        mock_db = MagicMock()
        existing_stock = MagicMock(spec=StockMaster, symbol="005930", name="오래된삼성전자", market="KOSPI", corp_code="0012345")
        mock_dart_get_all_stocks.return_value = [
            {"symbol": "005930", "name": "새로운삼성전자", "market": "KOSPI", "corp_code": "0012345"}
        ]
        mock_db.query.return_value.filter.return_value.first.return_value = existing_stock

        # WHEN
        result = await stock_service.update_stock_master(mock_db, use_dart=True)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 1
        mock_dart_get_all_stocks.assert_called_once()
        mock_db.add.assert_not_called() # 업데이트이므로 add 호출 안됨
        mock_db.commit.assert_called_once()
        assert existing_stock.name == "새로운삼성전자"

    @pytest.mark.asyncio
    @patch('src.api.services.stock_service.dart_get_all_stocks')
    async def test_update_stock_master_from_dart_api_error(self, mock_dart_get_all_stocks, stock_service):
        """DART API 오류 발생 시 종목 마스터 갱신 실패 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_dart_get_all_stocks.side_effect = DartApiError("DART API Error")

        # WHEN
        result = await stock_service.update_stock_master(mock_db, use_dart=True)

        # THEN
        assert result["success"] == False
        assert "DART API Error" in result["error"]
        mock_dart_get_all_stocks.assert_called_once()
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_stock_master_from_sample_data(self, stock_service):
        """샘플 데이터를 통해 종목 마스터 갱신 성공 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [None] * 10 # 10개 종목 모두 DB에 없다고 가정

        # WHEN
        result = await stock_service.update_stock_master(mock_db, use_dart=False)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 10
        assert mock_db.add.call_count == 10
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    async def test_update_disclosures_for_all_stocks_success(self, mock_dart_get_disclosures, stock_service):
        """모든 종목에 대한 공시 갱신 성공 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "1", "corp_name": "회사1", "report_nm": "보고서1", "rcept_dt": "20230101", "stock_code": "000001"},
            {"rcept_no": "2", "corp_name": "회사2", "report_nm": "보고서2", "rcept_dt": "20230102", "stock_code": "000002"}
        ]
        mock_db.query.return_value.all.return_value = [] # 기존 공시 없음

        # WHEN
        result = await stock_service.update_disclosures_for_all_stocks(mock_db)

        # THEN
        assert result["success"] == True
        assert result["inserted"] == 2
        assert result["skipped"] == 0
        assert len(result["errors"]) == 0
        mock_dart_get_disclosures.assert_called_once()
        mock_db.bulk_save_objects.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    async def test_update_disclosures_for_all_stocks_skip_existing(self, mock_dart_get_disclosures, stock_service):
        """모든 종목에 대한 공시 갱신 시 기존 공시 건너뛰기 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "1", "corp_name": "회사1", "report_nm": "보고서1", "rcept_dt": "20230101", "stock_code": "000001"},
            {"rcept_no": "2", "corp_name": "회사2", "report_nm": "보고서2", "rcept_dt": "20230102", "stock_code": "000002"}
        ]
        mock_db.query.return_value.all.return_value = [("1",)] # 기존 공시 1개 존재

        # WHEN
        result = await stock_service.update_disclosures_for_all_stocks(mock_db)

        # THEN
        assert result["success"] == True
        assert result["inserted"] == 1
        assert result["skipped"] == 1
        assert len(result["errors"]) == 0
        mock_dart_get_disclosures.assert_called_once()
        mock_db.bulk_save_objects.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    async def test_update_disclosures_for_all_stocks_api_error(self, mock_dart_get_disclosures, stock_service):
        """모든 종목에 대한 공시 갱신 시 API 오류 발생 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_dart_get_disclosures.side_effect = Exception("DART API Error")

        # WHEN
        result = await stock_service.update_disclosures_for_all_stocks(mock_db)

        # THEN
        assert result["success"] == False
        assert result["inserted"] == 0
        assert result["skipped"] == 0
        assert "DART API Error" in result["errors"][0]
        mock_dart_get_disclosures.assert_called_once()
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    async def test_update_disclosures_success(self, mock_dart_get_disclosures, stock_service):
        """특정 기업 공시 갱신 성공 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "3", "corp_name": "회사3", "report_nm": "보고서3", "rcept_dt": "20230103"}
        ]
        mock_db.query.return_value.filter.return_value.first.return_value = None # 기존 공시 없음

        # WHEN
        result = await stock_service.update_disclosures(mock_db, corp_code="000003", stock_code="000003", stock_name="회사3")

        # THEN
        assert result["success"] == True
        assert result["inserted"] == 1
        assert result["skipped"] == 0
        assert len(result["errors"]) == 0
        mock_dart_get_disclosures.assert_called_once_with("000003", max_count=10)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    async def test_update_disclosures_skip_existing(self, mock_dart_get_disclosures, stock_service):
        """특정 기업 공시 갱신 시 기존 공시 건너뛰기 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "3", "corp_name": "회사3", "report_nm": "보고서3", "rcept_dt": "20230103"}
        ]
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(spec=Disclosure) # 기존 공시 존재

        # WHEN
        result = await stock_service.update_disclosures(mock_db, corp_code="000003", stock_code="000003", stock_name="회사3")

        # THEN
        assert result["success"] == True
        assert result["inserted"] == 0
        assert result["skipped"] == 1
        assert len(result["errors"]) == 0
        mock_dart_get_disclosures.assert_called_once_with("000003", max_count=10)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    async def test_update_disclosures_api_error(self, mock_dart_get_disclosures, stock_service):
        """특정 기업 공시 갱신 시 API 오류 발생 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_dart_get_disclosures.side_effect = Exception("DART API Error")

        # WHEN
        result = await stock_service.update_disclosures(mock_db, corp_code="000003", stock_code="000003", stock_name="회사3")

        # THEN
        assert result["success"] == False
        assert result["inserted"] == 0
        assert result["skipped"] == 0
        assert "DART API Error" in result["errors"][0]
        mock_dart_get_disclosures.assert_called_once_with("000003", max_count=10)
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    async def test_update_disclosures_parses_disclosure_type(self, mock_dart_get_disclosures, stock_service):
        """공시 갱신 시 disclosure_type이 올바르게 파싱되는지 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "4", "corp_name": "회사4", "report_nm": "[기재정정]사업보고서", "rcept_dt": "20230104"}
        ]
        mock_db.query.return_value.filter.return_value.first.return_value = None # 기존 공시 없음

        # WHEN
        await stock_service.update_disclosures(mock_db, corp_code="000004", stock_code="000004", stock_name="회사4")

        # THEN
        mock_db.add.assert_called_once()
        added_disclosure = mock_db.add.call_args[0][0]
        assert added_disclosure.title == "[기재정정]사업보고서"
        assert added_disclosure.disclosure_type == "사업보고서"

    @pytest.mark.asyncio
    @patch('src.common.utils.dart_utils.dart_get_disclosures')
    async def test_update_disclosures_for_all_stocks_parses_disclosure_type(self, mock_dart_get_disclosures, stock_service):
        """전체 공시 갱신 시 disclosure_type이 올바르게 파싱되는지 테스트"""
        # GIVEN
        mock_db = MagicMock()
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "5", "corp_name": "회사5", "report_nm": "[첨부정정]반기보고서", "rcept_dt": "20230105", "stock_code": "000005"}
        ]
        mock_db.query.return_value.all.return_value = [] # 기존 공시 없음

        # WHEN
        await stock_service.update_disclosures_for_all_stocks(mock_db)

        # THEN
        mock_db.bulk_save_objects.assert_called_once()
        saved_disclosures = mock_db.bulk_save_objects.call_args[0][0]
        assert len(saved_disclosures) == 1
        assert saved_disclosures[0].title == "[첨부정정]반기보고서"
        assert saved_disclosures[0].disclosure_type == "반기보고서"