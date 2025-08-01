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
from src.api.models.daily_price import DailyPrice
import os
import yfinance as yf
import pandas as pd
from unittest.mock import ANY

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
                    assert real_db.rollback.called # 롤백이 호출되어야 함 

    @pytest.mark.asyncio
    @patch('yfinance.download')
    async def test_update_daily_prices_success(self, mock_yfinance_download, stock_service, real_db):
        """일별시세 갱신 성공 테스트"""
        # GIVEN
        # StockMaster에 테스트용 종목 추가
        stock1 = StockMaster(symbol="005930", name="삼성전자", market="KOSPI", corp_code="0012345")
        stock2 = StockMaster(symbol="000660", name="SK하이닉스", market="KOSPI", corp_code="0012346")
        real_db.add_all([stock1, stock2])
        real_db.commit()

        # pandas_datareader.data.get_data_yahoo 모의
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
        result = await stock_service.update_daily_prices(real_db)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 4 # 각 종목당 2일치 데이터
        assert len(result["errors"]) == 0

        # DB에 데이터가 올바르게 저장되었는지 확인
        daily_prices = real_db.query(DailyPrice).all()
        assert len(daily_prices) == 4

        samsung_prices = [p for p in daily_prices if p.symbol == "005930"]
        assert len(samsung_prices) == 2
        assert samsung_prices[0].close == 71500 # 최신 날짜 데이터
        assert samsung_prices[1].close == 72500

        skhynix_prices = [p for p in daily_prices if p.symbol == "000660"]
        assert len(skhynix_prices) == 2
        assert skhynix_prices[0].close == 101500
        assert skhynix_prices[1].close == 102500

        mock_yfinance_download.assert_any_call("005930.KS", start=ANY, end=ANY)
        mock_yfinance_download.assert_any_call("000660.KS", start=ANY, end=ANY)

    @pytest.mark.asyncio
    @patch('yfinance.download')
    async def test_update_daily_prices_no_data(self, mock_yfinance_download, stock_service, real_db):
        """일별시세 갱신 시 데이터가 없는 경우 테스트"""
        # GIVEN
        stock1 = StockMaster(symbol="005930", name="삼성전자", market="KOSPI", corp_code="0012345")
        real_db.add(stock1)
        real_db.commit()

        mock_yfinance_download.return_value = pd.DataFrame() # 빈 DataFrame 반환

        # WHEN
        result = await stock_service.update_daily_prices(real_db)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 0
        assert "005930" in result["errors"] # 에러 종목에 포함되는지 확인

        daily_prices = real_db.query(DailyPrice).all()
        assert len(daily_prices) == 0 # 데이터가 추가되지 않아야 함

    @pytest.mark.asyncio
    @patch('yfinance.download')
    async def test_update_daily_prices_api_error(self, mock_yfinance_download, stock_service, real_db):
        """일별시세 갱신 시 API 오류 발생 테스트"""
        # GIVEN
        stock1 = StockMaster(symbol="005930", name="삼성전자", market="KOSPI", corp_code="0012345")
        real_db.add(stock1)
        real_db.commit()

        mock_yfinance_download.side_effect = Exception("API Error")

        # WHEN
        result = await stock_service.update_daily_prices(real_db)

        # THEN
        assert result["success"] == True # 개별 종목 오류는 전체 성공으로 처리
        assert result["updated_count"] == 0
        assert "005930" in result["errors"] # 에러 종목에 포함되는지 확인

        daily_prices = real_db.query(DailyPrice).all()
        assert len(daily_prices) == 0 # 데이터가 추가되지 않아야 함

    @pytest.mark.asyncio
    async def test_get_current_price_and_change(self, stock_service, real_db):
        """현재가 및 등락률 조회 테스트"""
        # GIVEN
        # 테스트용 DailyPrice 데이터 추가
        stock_symbol = "005930"
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        price_today = DailyPrice(symbol=stock_symbol, date=today, open=70000, high=71000, low=69000, close=71500, volume=1000000)
        price_yesterday = DailyPrice(symbol=stock_symbol, date=yesterday, open=69000, high=70000, low=68000, close=70500, volume=900000)
        real_db.add_all([price_today, price_yesterday])
        real_db.commit()

        # WHEN
        result = stock_service.get_current_price_and_change(stock_symbol, real_db)

        # THEN
        assert result["current_price"] == 71500
        assert result["change"] == 1000
        assert abs(result["change_rate"] - (1000 / 70500) * 100) < 0.001 # 부동소수점 비교

    @pytest.mark.asyncio
    async def test_get_current_price_and_change_no_data(self, stock_service, real_db):
        """현재가 및 등락률 조회 시 데이터가 없는 경우 테스트"""
        # GIVEN: 데이터 없음

        # WHEN
        result = stock_service.get_current_price_and_change("NONEXIST", real_db)

        # THEN
        assert result["current_price"] is None
        assert result["change"] is None
        assert result["change_rate"] is None

    @pytest.mark.asyncio
    async def test_get_current_price_and_change_only_one_day_data(self, stock_service, real_db):
        """현재가 및 등락률 조회 시 하루치 데이터만 있는 경우 테스트"""
        # GIVEN
        stock_symbol = "005930"
        today = datetime.now().date()

        price_today = DailyPrice(symbol=stock_symbol, date=today, open=70000, high=71000, low=69000, close=71500, volume=1000000)
        real_db.add(price_today)
        real_db.commit()

        # WHEN
        result = stock_service.get_current_price_and_change(stock_symbol, real_db)

        # THEN
        assert result["current_price"] == 71500
        assert result["change"] is None
        assert result["change_rate"] is None 