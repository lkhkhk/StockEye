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

class TestStockService:
    @pytest.fixture
    def stock_service(self):
        return StockService()

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    @patch('src.common.services.stock_service.send_telegram_message') # MOCK: send_telegram_message 함수
    async def test_check_and_notify_new_disclosures_no_new_disclosures(self, mock_send_telegram_message, mock_dart_get_disclosures, stock_service, caplog):
        """새로운 공시가 없는 경우 (DB에 마지막 확인 번호가 있고, 신규 공시가 없는 경우) - 단위 테스트"""
        with caplog.at_level(logging.INFO):
            # GIVEN
            # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
            mock_db = MagicMock()
            # MagicMock: SystemConfig 모델 객체를 모의합니다. 동기적으로 동작합니다.
            mock_config = MagicMock(spec=SystemConfig)
            mock_config.value = '202301010000001'
            # mock_db.query().filter().first() 호출 시 mock_config를 반환하도록 설정합니다.
            mock_db.query.return_value.filter.return_value.first.return_value = mock_config

            # mock_dart_get_disclosures (AsyncMock) 호출 시 모의 공시 목록을 반환하도록 설정합니다.
            mock_dart_get_disclosures.return_value = [
                {"rcept_no": "202301010000001", "corp_name": "기존회사", "report_nm": "기존보고서", "rcept_dt": "20230101"}
            ]

            # WHEN
            await stock_service.check_and_notify_new_disclosures(mock_db)

            # THEN
            # mock_dart_get_disclosures (AsyncMock)가 한 번 호출되었는지 확인합니다.
            mock_dart_get_disclosures.assert_called_once()
            # mock_send_telegram_message (AsyncMock)가 호출되지 않았는지 확인합니다.
            mock_send_telegram_message.assert_not_called()
            assert "신규 공시가 없습니다." in caplog.text

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    @patch('src.common.services.stock_service.send_telegram_message') # MOCK: send_telegram_message 함수
    async def test_check_and_notify_new_disclosures_initial_run(self, mock_send_telegram_message, mock_dart_get_disclosures, stock_service, caplog):
        """최초 실행 시 기준점 설정 테스트 - 단위 테스트"""
        with caplog.at_level(logging.INFO):
            # GIVEN
            # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
            mock_db = MagicMock()
            
            # DB 쿼리를 정교하게 모의: SystemConfig와 Disclosure 조회 시에는 None을, 그 외에는 빈 리스트를 반환
            def query_side_effect(model):
                query_mock = MagicMock()
                if model == SystemConfig:
                    query_mock.filter.return_value.first.return_value = None
                elif model == Disclosure:
                    query_mock.filter.return_value.first.return_value = None
                else: # PriceAlert, User 등
                    query_mock.filter.return_value.all.return_value = []
                return query_mock

            mock_db.query.side_effect = query_side_effect

            # mock_dart_get_disclosures (AsyncMock) 호출 시 모의 공시 목록을 반환하도록 설정합니다.
            mock_dart_get_disclosures.return_value = [
                {"rcept_no": "202301020000001", "corp_name": "새회사", "report_nm": "새보고서", "rcept_dt": "20230102", "stock_code": "123456"},
                {"rcept_no": "202301010000001", "corp_name": "기존회사", "report_nm": "기존보고서", "rcept_dt": "20230101", "stock_code": "654321"}
            ]
            # MOCK: os.environ
            # TELEGRAM_ADMIN_ID 환경 변수를 모의하여, 실제 관리자 ID 없이 테스트를 실행합니다.
            os.environ["TELEGRAM_ADMIN_ID"] = "12345"

            # WHEN
            await stock_service.check_and_notify_new_disclosures(mock_db)

            # THEN
            # mock_dart_get_disclosures (AsyncMock)가 한 번 호출되었는지 확인합니다.
            mock_dart_get_disclosures.assert_called_once()
            
            # 관리자 리포트는 발송되지만, 사용자 알림은 없음 (총 1번 호출)
            # mock_send_telegram_message (AsyncMock)가 한 번 호출되었는지 확인합니다.
            mock_send_telegram_message.assert_called_once()
            
            assert "최초 실행. 기준 접수번호를 202301020000001로 DB에 설정합니다." in caplog.text
            assert "2건의 신규 공시를 발견했습니다." in caplog.text
            
            # 신규 공시와 시스템 설정이 DB에 추가/커밋되는지 확인
            # mock_db.bulk_save_objects (MagicMock)가 한 번 호출되었는지 확인합니다.
            assert mock_db.bulk_save_objects.call_count == 1
            # mock_db.add (MagicMock)가 한 번 호출되었는지 확인합니다.
            assert mock_db.add.call_count == 1
            # mock_db.commit (MagicMock)가 세 번 호출되었는지 확인합니다.
            assert mock_db.commit.call_count == 3

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    @patch('src.common.services.stock_service.send_telegram_message') # MOCK: send_telegram_message 함수
    async def test_check_and_notify_new_disclosures_success(self, mock_send_telegram_message, mock_dart_get_disclosures, stock_service, caplog):
        """신규 공시 알림 성공 테스트 - 단위 테스트"""
        with caplog.at_level(logging.INFO):
            # GIVEN
            # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
            mock_db = MagicMock()
            # MagicMock: SystemConfig 모델 객체를 모의합니다. 동기적으로 동작합니다.
            mock_config = MagicMock(spec=SystemConfig)
            mock_config.value = '202301010000001'
            
            # MagicMock: StockMaster 모델 객체를 모의합니다. 동기적으로 동작합니다.
            mock_stock_master_samsung = MagicMock(spec=StockMaster, symbol="005930", corp_code="0012345")
            mock_stock_master_samsung.name = "삼성전자"
            # MagicMock: User 모델 객체를 모의합니다. 동기적으로 동작합니다.
            mock_user_1 = MagicMock(spec=User, id=1, telegram_id=123, username="testuser")
            # MagicMock: PriceAlert 모델 객체를 모의합니다. 동기적으로 동작합니다.
            mock_price_alert_samsung = MagicMock(spec=PriceAlert, user_id=1, symbol="005930", notify_on_disclosure=True, is_active=True)

            # Mocking the database queries
            def query_side_effect(model):
                query_mock = MagicMock()
                if model == SystemConfig:
                    query_mock.filter.return_value.first.return_value = mock_config
                elif model == StockMaster:
                    query_mock.filter.return_value.first.return_value = mock_stock_master_samsung
                elif model == PriceAlert:
                    query_mock.filter.return_value.all.return_value = [mock_price_alert_samsung]
                elif model == User:
                    query_mock.filter.return_value.all.return_value = [mock_user_1]
                elif model == Disclosure: # Add this block for Disclosure model
                    query_mock.filter.return_value.first.return_value = None # Simulate no existing disclosure
                return query_mock

            mock_db.query.side_effect = query_side_effect

            # mock_dart_get_disclosures (AsyncMock) 호출 시 모의 공시 목록을 반환하도록 설정합니다.
            mock_dart_get_disclosures.return_value = [
                {"rcept_no": "202301020000002", "corp_name": "삼성전자", "report_nm": "신규보고서2", "rcept_dt": "20230102", "stock_code": "005930", "corp_code": "0012345"},
                {"rcept_no": "202301020000001", "corp_name": "삼성전자", "report_nm": "신규보고서1", "rcept_dt": "20230102", "stock_code": "005930", "corp_code": "0012345"},
                {"rcept_no": "202301010000001", "corp_name": "기존회사", "report_nm": "기존보고서", "rcept_dt": "20230101", "stock_code": "000000", "corp_code": "0000000"}
            ]
            # MOCK: os.environ
            # TELEGRAM_ADMIN_ID 환경 변수를 모의하여, 실제 관리자 ID 없이 테스트를 실행합니다.
            os.environ["TELEGRAM_ADMIN_ID"] = "456"

            # WHEN
            await stock_service.check_and_notify_new_disclosures(mock_db)

            # THEN
            # mock_dart_get_disclosures (AsyncMock)가 한 번 호출되었는지 확인합니다.
            mock_dart_get_disclosures.assert_called_once()
            # mock_send_telegram_message (AsyncMock)가 세 번 호출되었는지 확인합니다. (2 사용자 알림 + 1 관리자 리포트)
            assert mock_send_telegram_message.call_count == 3 
            # mock_send_telegram_message (AsyncMock)가 올바른 인자로 호출되었는지 확인합니다.
            mock_send_telegram_message.assert_any_call(123, "🔔 [삼성전자] 신규 공시\n\n📑 신규보고서1\n🕒 20230102\n🔗 https://dart.fss.or.kr/dsaf001/main.do?rcpNo=202301020000001")
            # mock_send_telegram_message (AsyncMock)가 올바른 인자로 호출되었는지 확인합니다.
            mock_send_telegram_message.assert_any_call(123, "🔔 [삼성전자] 신규 공시\n\n📑 신규보고서2\n🕒 20230102\n🔗 https://dart.fss.or.kr/dsaf001/main.do?rcpNo=202301020000002")
            
            admin_call_args = mock_send_telegram_message.call_args_list[2].args # Assuming it's the third call
            assert admin_call_args[0] == 456
            assert "📈 공시 알림 요약 리포트" in admin_call_args[1]
            assert "- 발견된 신규 공시: 2건" in admin_call_args[1]
            assert "- DB에 추가된 공시: 2건" in admin_call_args[1]
            assert "- 총 알림 발송 건수: 2건" in admin_call_args[1]

            assert "2건의 신규 공시를 발견했습니다." in caplog.text
            assert "마지막 확인 접수번호를 202301020000002로 DB에 갱신합니다." in caplog.text
            assert mock_config.value == '202301020000002'
            # mock_db.commit (MagicMock)가 두 번 호출되었는지 확인합니다.
            assert mock_db.commit.call_count == 2

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    @patch('src.common.services.stock_service.send_telegram_message') # MOCK: send_telegram_message 함수
    async def test_check_and_notify_new_disclosures_dart_api_limit_exceeded(self, mock_send_telegram_message, mock_dart_get_disclosures, stock_service, caplog):
        """DART API 사용 한도 초과 오류 처리 테스트 - 단위 테스트"""
        with caplog.at_level(logging.CRITICAL):
            # GIVEN
            # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
            mock_db = MagicMock()
            # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
            mock_db.query.return_value.filter.return_value.first.return_value = None
            # mock_dart_get_disclosures (AsyncMock) 호출 시 DartApiError를 발생시키도록 설정합니다.
            mock_dart_get_disclosures.side_effect = DartApiError("사용 한도 초과", status_code="020")

            # WHEN
            await stock_service.check_and_notify_new_disclosures(mock_db)

            # THEN
            # mock_dart_get_disclosures (AsyncMock)가 한 번 호출되었는지 확인합니다.
            mock_dart_get_disclosures.assert_called_once()
            # mock_send_telegram_message (AsyncMock)가 호출되지 않았는지 확인합니다.
            mock_send_telegram_message.assert_not_called()
            assert "DART API 사용 한도를 초과했습니다" in caplog.text
            # mock_db.rollback (MagicMock)이 호출되지 않았는지 확인합니다.
            mock_db.rollback.assert_not_called()

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    @patch('src.common.services.stock_service.send_telegram_message') # MOCK: send_telegram_message 함수
    async def test_check_and_notify_new_disclosures_other_dart_api_error(self, mock_send_telegram_message, mock_dart_get_disclosures, stock_service, caplog):
        """기타 DART API 오류 처리 테스트 - 단위 테스트"""
        with caplog.at_level(logging.ERROR):
            # GIVEN
            # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
            mock_db = MagicMock()
            # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
            mock_db.query.return_value.filter.return_value.first.return_value = None
            # mock_dart_get_disclosures (AsyncMock) 호출 시 DartApiError를 발생시키도록 설정합니다.
            mock_dart_get_disclosures.side_effect = DartApiError("기타 API 오류", status_code="999")

            # WHEN
            await stock_service.check_and_notify_new_disclosures(mock_db)

            # THEN
            # mock_dart_get_disclosures (AsyncMock)가 한 번 호출되었는지 확인합니다.
            mock_dart_get_disclosures.assert_called_once()
            # mock_send_telegram_message (AsyncMock)가 호출되지 않았는지 확인합니다.
            mock_send_telegram_message.assert_not_called()
            assert "DART 공시 조회 중 API 오류 발생" in caplog.text
            # mock_db.rollback (MagicMock)이 호출되지 않았는지 확인합니다.
            mock_db.rollback.assert_not_called()

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    @patch('src.common.services.stock_service.send_telegram_message') # MOCK: send_telegram_message 함수
    async def test_check_and_notify_new_disclosures_unexpected_error(self, mock_send_telegram_message, mock_dart_get_disclosures, stock_service, caplog):
        """예상치 못한 오류 발생 시 롤백 및 로깅 테스트 - 단위 테스트"""
        with caplog.at_level(logging.ERROR):
            # GIVEN
            # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
            mock_db = MagicMock()
            # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
            mock_db.query.return_value.filter.return_value.first.return_value = None
            # mock_dart_get_disclosures (AsyncMock) 호출 시 Exception을 발생시키도록 설정합니다.
            mock_dart_get_disclosures.side_effect = Exception("예상치 못한 오류")

            # WHEN
            await stock_service.check_and_notify_new_disclosures(mock_db)

            # THEN
            # mock_dart_get_disclosures (AsyncMock)가 한 번 호출되었는지 확인합니다.
            mock_dart_get_disclosures.assert_called_once()
            # mock_send_telegram_message (AsyncMock)가 호출되지 않았는지 확인합니다.
            mock_send_telegram_message.assert_not_called()
            assert "신규 공시 확인 및 알림 작업 중 예상치 못한 오류 발생" in caplog.text
            # mock_db.rollback (MagicMock)이 한 번 호출되었는지 확인합니다.
            mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    @patch('yfinance.download') # MOCK: yfinance.download 함수
    async def test_update_daily_prices_success(self, mock_yfinance_download, stock_service):
        """일별시세 갱신 성공 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        
        # MagicMock: StockMaster 모델 객체를 모의합니다. 동기적으로 동작합니다.
        stock1 = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자", corp_code="0012345")
        # MagicMock: StockMaster 모델 객체를 모의합니다. 동기적으로 동작합니다.
        stock2 = MagicMock(spec=StockMaster, symbol="000660", name="SK하이닉스", corp_code="0012346")
        # mock_db.query().all() 호출 시 모의 종목 목록을 반환하도록 설정합니다.
        mock_db.query.return_value.all.return_value = [stock1, stock2]

        # pandas.DataFrame: yfinance.download가 반환할 모의 데이터프레임을 생성합니다.
        mock_df_samsung = pd.DataFrame({
            'Open': [70000, 71000],
            'High': [72000, 73000],
            'Low': [69000, 70000],
            'Close': [71500, 72500],
            'Volume': [1000000, 1200000]
        }, index=pd.to_datetime(['2025-07-29', '2025-07-28']))
        # pandas.DataFrame: yfinance.download가 반환할 모의 데이터프레임을 생성합니다.
        mock_df_skhynix = pd.DataFrame({
            'Open': [100000, 101000],
            'High': [102000, 103000],
            'Low': [99000, 100000],
            'Close': [101500, 102500],
            'Volume': [500000, 600000]
        }, index=pd.to_datetime(['2025-07-29', '2025-07-28']))

        # mock_yfinance_download (MagicMock) 호출 시 다른 데이터프레임을 반환하도록 설정합니다.
        mock_yfinance_download.side_effect = [mock_df_samsung, mock_df_skhynix]

        # WHEN
        result = await stock_service.update_daily_prices(mock_db)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 4 # 각 종목당 2일치 데이터
        assert len(result["errors"]) == 0

        # mock_db.add (MagicMock)가 네 번 호출되었는지 확인합니다.
        assert mock_db.add.call_count == 4
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()

        # mock_yfinance_download (MagicMock)가 올바른 인자로 호출되었는지 확인합니다.
        mock_yfinance_download.assert_any_call("005930.KS", start=ANY, end=ANY)
        # mock_yfinance_download (MagicMock)가 올바른 인자로 호출되었는지 확인합니다.
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
    @patch('yfinance.download') # MOCK: yfinance.download 함수
    async def test_update_daily_prices_no_data(self, mock_yfinance_download, stock_service):
        """일별시세 갱신 시 데이터가 없는 경우 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # MagicMock: StockMaster 모델 객체를 모의합니다. 동기적으로 동작합니다.
        stock1 = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자", market="KOSPI", corp_code="0012345")
        # mock_db.query().all() 호출 시 모의 종목 목록을 반환하도록 설정합니다.
        mock_db.query.return_value.all.return_value = [stock1]

        # mock_yfinance_download (MagicMock) 호출 시 빈 DataFrame을 반환하도록 설정합니다.
        mock_yfinance_download.return_value = pd.DataFrame() # 빈 DataFrame 반환

        # WHEN
        result = stock_service.update_daily_prices(mock_db)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 0
        assert "005930" in result["errors"] # 에러 종목에 포함되는지 확인

        # mock_db.add (MagicMock)가 호출되지 않았는지 확인합니다.
        mock_db.add.assert_not_called()
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('yfinance.download') # MOCK: yfinance.download 함수
    async def test_update_daily_prices_api_error(self, mock_yfinance_download, stock_service):
        """일별시세 갱신 시 API 오류 발생 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # MagicMock: StockMaster 모델 객체를 모의합니다. 동기적으로 동작합니다.
        stock1 = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자", market="KOSPI", corp_code="0012345")
        # mock_db.query().all() 호출 시 모의 종목 목록을 반환하도록 설정합니다.
        mock_db.query.return_value.all.return_value = [stock1]

        # mock_yfinance_download (MagicMock) 호출 시 Exception을 발생시키도록 설정합니다.
        mock_yfinance_download.side_effect = Exception("API Error")

        # WHEN
        result = await stock_service.update_daily_prices(mock_db)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 0
        assert "005930" in result["errors"] # 에러 종목에 포함되는지 확인

        # mock_db.add (MagicMock)가 호출되지 않았는지 확인합니다.
        mock_db.add.assert_not_called()
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_price_and_change(self, stock_service):
        """현재가 및 등락률 조회 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        stock_symbol = "005930"
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # MagicMock: DailyPrice 모델 객체를 모의합니다. 동기적으로 동작합니다.
        price_today = MagicMock(spec=DailyPrice, symbol=stock_symbol, date=today, open=70000, high=71000, low=69000, close=71500, volume=1000000)
        # MagicMock: DailyPrice 모델 객체를 모의합니다. 동기적으로 동작합니다.
        price_yesterday = MagicMock(spec=DailyPrice, symbol=stock_symbol, date=yesterday, open=69000, high=70000, low=68000, close=70500, volume=900000)
        
        # mock_db.query().filter().order_by().limit().all() 호출 시 모의 일별 시세 목록을 반환하도록 설정합니다.
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
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_db.query().filter().order_by().limit().all() 호출 시 빈 목록을 반환하도록 설정합니다.
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
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        stock_symbol = "005930"
        today = datetime.now().date()

        # MagicMock: DailyPrice 모델 객체를 모의합니다. 동기적으로 동작합니다.
        price_today = MagicMock(spec=DailyPrice, symbol=stock_symbol, date=today, open=70000, high=71000, low=69000, close=71500, volume=1000000)
        # mock_db.query().filter().order_by().limit().all() 호출 시 하루치 데이터만 반환하도록 설정합니다.
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
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # MagicMock: StockMaster 모델 객체를 모의합니다. 동기적으로 동작합니다.
        mock_stock = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자")
        # mock_db.query().filter().first() 호출 시 mock_stock을 반환하도록 설정합니다.
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        # WHEN
        result = stock_service.get_stock_by_symbol("005930", mock_db)

        # THEN
        assert result == mock_stock
        # mock_db.query (MagicMock)가 StockMaster 모델로 한 번 호출되었는지 확인합니다.
        mock_db.query.assert_called_once_with(StockMaster)
        # mock_db.query().filter (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.assert_called_once()
        # mock_db.query().filter().first (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_stock_by_symbol_not_found(self, stock_service):
        """심볼로 종목 조회 시 종목이 존재하지 않는 경우 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # WHEN
        result = stock_service.get_stock_by_symbol("NONEXIST", mock_db)

        # THEN
        assert result is None
        # mock_db.query (MagicMock)가 StockMaster 모델로 한 번 호출되었는지 확인합니다.
        mock_db.query.assert_called_once_with(StockMaster)
        # mock_db.query().filter (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.assert_called_once()
        # mock_db.query().filter().first (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_stock_by_name_found(self, stock_service):
        """이름으로 종목 조회 시 종목이 존재하는 경우 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # MagicMock: StockMaster 모델 객체를 모의합니다. 동기적으로 동작합니다.
        mock_stock = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자")
        # mock_db.query().filter().first() 호출 시 mock_stock을 반환하도록 설정합니다.
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        # WHEN
        result = stock_service.get_stock_by_name("삼성전자", mock_db)

        # THEN
        assert result == mock_stock
        # mock_db.query (MagicMock)가 StockMaster 모델로 한 번 호출되었는지 확인합니다.
        mock_db.query.assert_called_once_with(StockMaster)
        # mock_db.query().filter (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.assert_called_once()
        # mock_db.query().filter().first (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_stock_by_name_not_found(self, stock_service):
        """이름으로 종목 조회 시 종목이 존재하지 않는 경우 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # WHEN
        result = stock_service.get_stock_by_name("없는종목", mock_db)

        # THEN
        assert result is None
        # mock_db.query (MagicMock)가 StockMaster 모델로 한 번 호출되었는지 확인합니다.
        mock_db.query.assert_called_once_with(StockMaster)
        # mock_db.query().filter (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.assert_called_once()
        # mock_db.query().filter().first (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_search_stocks_found(self, stock_service):
        """키워드로 종목 검색 시 종목이 존재하는 경우 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # MagicMock: StockMaster 모델 객체를 모의합니다. 동기적으로 동작합니다.
        mock_stock1 = MagicMock(spec=StockMaster, symbol="005930", name="삼성전자")
        # MagicMock: StockMaster 모델 객체를 모의합니다. 동기적으로 동작합니다.
        mock_stock2 = MagicMock(spec=StockMaster, symbol="000660", name="SK하이닉스")
        # mock_db.query().filter().limit().all() 호출 시 모의 종목 목록을 반환하도록 설정합니다.
        mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_stock1, mock_stock2]

        # WHEN
        result = stock_service.search_stocks("삼성", mock_db)

        # THEN
        assert len(result) == 2
        assert result[0] == mock_stock1
        assert result[1] == mock_stock2
        # mock_db.query (MagicMock)가 StockMaster 모델로 한 번 호출되었는지 확인합니다.
        mock_db.query.assert_called_once_with(StockMaster)
        # mock_db.query().filter (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.assert_called_once()
        # mock_db.query().filter().limit (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.return_value.limit.assert_called_once()
        # mock_db.query().filter().limit().all (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.return_value.limit.return_value.all.assert_called_once()

    def test_search_stocks_not_found(self, stock_service):
        """키워드로 종목 검색 시 종목이 존재하지 않는 경우 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_db.query().filter().limit().all() 호출 시 빈 목록을 반환하도록 설정합니다.
        mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = []

        # WHEN
        result = stock_service.search_stocks("없는키워드", mock_db)

        # THEN
        assert len(result) == 0
        # mock_db.query (MagicMock)가 StockMaster 모델로 한 번 호출되었는지 확인합니다.
        mock_db.query.assert_called_once_with(StockMaster)
        # mock_db.query().filter (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.assert_called_once()
        # mock_db.query().filter().limit (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.return_value.limit.assert_called_once()
        # mock_db.query().filter().limit().all (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.return_value.limit.return_value.all.assert_called_once()

    def test_get_daily_prices_found(self, stock_service):
        """일별 시세 조회 시 데이터가 존재하는 경우 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        stock_symbol = "005930"
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # MagicMock: DailyPrice 모델 객체를 모의합니다. 동기적으로 동작합니다.
        price_today = MagicMock(spec=DailyPrice, symbol=stock_symbol, date=today, open=70000, high=71000, low=69000, close=71500, volume=1000000)
        # MagicMock: DailyPrice 모델 객체를 모의합니다. 동기적으로 동작합니다.
        price_yesterday = MagicMock(spec=DailyPrice, symbol=stock_symbol, date=yesterday, open=69000, high=70000, low=68000, close=70500, volume=900000)
        
        # mock_db.query().filter().filter().order_by().all() 호출 시 모의 일별 시세 목록을 반환하도록 설정합니다.
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [
            price_today, price_yesterday
        ]

        # WHEN
        result = stock_service.get_daily_prices(stock_symbol, mock_db, days=2)

        # THEN
        assert len(result) == 2
        assert result[0] == price_today
        assert result[1] == price_yesterday
        # mock_db.query (MagicMock)가 DailyPrice 모델로 한 번 호출되었는지 확인합니다.
        mock_db.query.assert_called_once_with(DailyPrice)
        # mock_db.query().filter().filter().order_by().all (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_all_stocks') # MOCK: dart_get_all_stocks 함수
    async def test_update_stock_master_from_dart_success(self, mock_dart_get_all_stocks, stock_service):
        """DART API를 통해 종목 마스터 갱신 성공 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_dart_get_all_stocks (AsyncMock) 호출 시 모의 종목 목록을 반환하도록 설정합니다.
        mock_dart_get_all_stocks.return_value = [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI", "corp_code": "0012345"},
            {"symbol": "000660", "name": "SK하이닉스", "market": "KOSPI", "corp_code": "0012346"}
        ]
        # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정하여 두 종목 모두 DB에 없음을 모의합니다.
        mock_db.query.return_value.filter.return_value.first.side_effect = [None, None] # 두 종목 모두 DB에 없다고 가정

        # WHEN
        result = await stock_service.update_stock_master(mock_db, use_dart=True)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 2
        # mock_dart_get_all_stocks (AsyncMock)가 한 번 호출되었는지 확인합니다.
        mock_dart_get_all_stocks.assert_called_once()
        # mock_db.add (MagicMock)가 두 번 호출되었는지 확인합니다.
        assert mock_db.add.call_count == 2
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_all_stocks') # MOCK: dart_get_all_stocks 함수
    async def test_update_stock_master_from_dart_update_existing(self, mock_dart_get_all_stocks, stock_service):
        """DART API를 통해 기존 종목 마스터 업데이트 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # MagicMock: StockMaster 모델 객체를 모의합니다. 동기적으로 동작합니다.
        existing_stock = MagicMock(spec=StockMaster, symbol="005930", name="오래된삼성전자", market="KOSPI", corp_code="0012345")
        # mock_dart_get_all_stocks (AsyncMock) 호출 시 모의 종목 목록을 반환하도록 설정합니다.
        mock_dart_get_all_stocks.return_value = [
            {"symbol": "005930", "name": "새로운삼성전자", "market": "KOSPI", "corp_code": "0012345"}
        ]
        # mock_db.query().filter().first() 호출 시 existing_stock을 반환하도록 설정합니다.
        mock_db.query.return_value.filter.return_value.first.return_value = existing_stock

        # WHEN
        result = await stock_service.update_stock_master(mock_db, use_dart=True)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 1
        # mock_dart_get_all_stocks (AsyncMock)가 한 번 호출되었는지 확인합니다.
        mock_dart_get_all_stocks.assert_called_once()
        # mock_db.add (MagicMock)가 호출되지 않았는지 확인합니다. (업데이트이므로 add 호출 안됨)
        mock_db.add.assert_not_called()
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()
        assert existing_stock.name == "새로운삼성전자"

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_all_stocks') # MOCK: dart_get_all_stocks 함수
    async def test_update_stock_master_from_dart_api_error(self, mock_dart_get_all_stocks, stock_service):
        """DART API 오류 발생 시 종목 마스터 갱신 실패 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_dart_get_all_stocks (AsyncMock) 호출 시 DartApiError를 발생시키도록 설정합니다.
        mock_dart_get_all_stocks.side_effect = DartApiError("DART API Error")

        # WHEN
        result = await stock_service.update_stock_master(mock_db, use_dart=True)

        # THEN
        assert result["success"] == False
        assert "DART API Error" in result["error"]
        # mock_dart_get_all_stocks (AsyncMock)가 한 번 호출되었는지 확인합니다.
        mock_dart_get_all_stocks.assert_called_once()
        # mock_db.rollback (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_stock_master_from_sample_data(self, stock_service):
        """샘플 데이터를 통해 종목 마스터 갱신 성공 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정하여 모든 종목이 DB에 없음을 모의합니다.
        mock_db.query.return_value.filter.return_value.first.side_effect = [None] * 10 # 10개 종목 모두 DB에 없다고 가정

        # WHEN
        result = await stock_service.update_stock_master(mock_db, use_dart=False)

        # THEN
        assert result["success"] == True
        assert result["updated_count"] == 10
        # mock_db.add (MagicMock)가 10번 호출되었는지 확인합니다.
        assert mock_db.add.call_count == 10
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    async def test_update_disclosures_for_all_stocks_success(self, mock_dart_get_disclosures, stock_service):
        """모든 종목에 대한 공시 갱신 성공 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_dart_get_disclosures (AsyncMock) 호출 시 모의 공시 목록을 반환하도록 설정합니다.
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "1", "corp_name": "회사1", "report_nm": "보고서1", "rcept_dt": "20230101", "stock_code": "000001"},
            {"rcept_no": "2", "corp_name": "회사2", "report_nm": "보고서2", "rcept_dt": "20230102", "stock_code": "000002"}
        ]
        # mock_db.query().all() 호출 시 빈 목록을 반환하도록 설정하여 기존 공시가 없음을 모의합니다.
        mock_db.query.return_value.all.return_value = [] # 기존 공시 없음

        # WHEN
        result = await stock_service.update_disclosures_for_all_stocks(mock_db)

        # THEN
        assert result["success"] == True
        assert result["inserted"] == 2
        assert result["skipped"] == 0
        assert len(result["errors"]) == 0
        # mock_dart_get_disclosures (AsyncMock)가 한 번 호출되었는지 확인합니다.
        mock_dart_get_disclosures.assert_called_once()
        # mock_db.bulk_save_objects (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.bulk_save_objects.assert_called_once()
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    async def test_update_disclosures_for_all_stocks_skip_existing(self, mock_dart_get_disclosures, stock_service):
        """모든 종목에 대한 공시 갱신 시 기존 공시 건너뛰기 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_dart_get_disclosures (AsyncMock) 호출 시 모의 공시 목록을 반환하도록 설정합니다.
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "1", "corp_name": "회사1", "report_nm": "보고서1", "rcept_dt": "20230101", "stock_code": "000001"},
            {"rcept_no": "2", "corp_name": "회사2", "report_nm": "보고서2", "rcept_dt": "20230102", "stock_code": "000002"}
        ]
        # mock_db.query().all() 호출 시 기존 공시가 하나 존재함을 모의합니다.
        mock_db.query.return_value.all.return_value = [("1",)] # 기존 공시 1개 존재

        # WHEN
        result = await stock_service.update_disclosures_for_all_stocks(mock_db)

        # THEN
        assert result["success"] == True
        assert result["inserted"] == 1
        assert result["skipped"] == 1
        assert len(result["errors"]) == 0
        # mock_dart_get_disclosures (AsyncMock)가 한 번 호출되었는지 확인합니다.
        mock_dart_get_disclosures.assert_called_once()
        # mock_db.bulk_save_objects (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.bulk_save_objects.assert_called_once()
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    async def test_update_disclosures_for_all_stocks_api_error(self, mock_dart_get_disclosures, stock_service):
        """모든 종목에 대한 공시 갱신 시 API 오류 발생 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_dart_get_disclosures (AsyncMock) 호출 시 Exception을 발생시키도록 설정합니다.
        mock_dart_get_disclosures.side_effect = Exception("DART API Error")

        # WHEN
        result = await stock_service.update_disclosures_for_all_stocks(mock_db)

        # THEN
        assert result["success"] == False
        assert result["inserted"] == 0
        assert result["skipped"] == 0
        assert "DART API Error" in result["errors"][0]
        # mock_dart_get_disclosures (AsyncMock)가 한 번 호출되었는지 확인합니다.
        mock_dart_get_disclosures.assert_called_once()
        # mock_db.rollback (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    async def test_update_disclosures_success(self, mock_dart_get_disclosures, stock_service):
        """특정 기업 공시 갱신 성공 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_dart_get_disclosures (AsyncMock) 호출 시 모의 공시 목록을 반환하도록 설정합니다.
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "3", "corp_name": "회사3", "report_nm": "보고서3", "rcept_dt": "20230103"}
        ]
        # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정하여 기존 공시가 없음을 모의합니다.
        mock_db.query.return_value.filter.return_value.first.return_value = None # 기존 공시 없음

        # WHEN
        result = await stock_service.update_disclosures(mock_db, corp_code="000003", stock_code="000003", stock_name="회사3")

        # THEN
        assert result["success"] == True
        assert result["inserted"] == 1
        assert result["skipped"] == 0
        assert len(result["errors"]) == 0
        # mock_dart_get_disclosures (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        mock_dart_get_disclosures.assert_called_once_with("000003", max_count=10)
        # mock_db.add (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.add.assert_called_once()
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    async def test_update_disclosures_skip_existing(self, mock_dart_get_disclosures, stock_service):
        """특정 기업 공시 갱신 시 기존 공시 건너뛰기 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_dart_get_disclosures (AsyncMock) 호출 시 모의 공시 목록을 반환하도록 설정합니다.
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "3", "corp_name": "회사3", "report_nm": "보고서3", "rcept_dt": "20230103"}
        ]
        # mock_db.query().filter().first() 호출 시 기존 공시가 존재함을 모의합니다.
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(spec=Disclosure) # 기존 공시 존재

        # WHEN
        result = await stock_service.update_disclosures(mock_db, corp_code="000003", stock_code="000003", stock_name="회사3")

        # THEN
        assert result["success"] == True
        assert result["inserted"] == 0
        assert result["skipped"] == 1
        assert len(result["errors"]) == 0
        # mock_dart_get_disclosures (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        mock_dart_get_disclosures.assert_called_once_with("000003", max_count=10)
        # mock_db.add (MagicMock)가 호출되지 않았는지 확인합니다.
        mock_db.add.assert_not_called()
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    async def test_update_disclosures_api_error(self, mock_dart_get_disclosures, stock_service):
        """특정 기업 공시 갱신 시 API 오류 발생 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_dart_get_disclosures (AsyncMock) 호출 시 Exception을 발생시키도록 설정합니다.
        mock_dart_get_disclosures.side_effect = Exception("DART API Error")

        # WHEN
        result = await stock_service.update_disclosures(mock_db, corp_code="000003", stock_code="000003", stock_name="회사3")

        # THEN
        assert result["success"] == False
        assert result["inserted"] == 0
        assert result["skipped"] == 0
        assert "DART API Error" in result["errors"][0]
        # mock_dart_get_disclosures (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        mock_dart_get_disclosures.assert_called_once_with("000003", max_count=10)
        # mock_db.rollback (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    async def test_update_disclosures_parses_disclosure_type(self, mock_dart_get_disclosures, stock_service):
        """공시 갱신 시 disclosure_type이 올바르게 파싱되는지 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_dart_get_disclosures (AsyncMock) 호출 시 모의 공시 목록을 반환하도록 설정합니다.
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "4", "corp_name": "회사4", "report_nm": "[기재정정]사업보고서", "rcept_dt": "20230104"}
        ]
        # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정하여 기존 공시가 없음을 모의합니다.
        mock_db.query.return_value.filter.return_value.first.return_value = None # 기존 공시 없음

        # WHEN
        await stock_service.update_disclosures(mock_db, corp_code="000004", stock_code="000004", stock_name="회사4")

        # THEN
        # mock_db.add (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.add.assert_called_once()
        added_disclosure = mock_db.add.call_args[0][0]
        assert added_disclosure.title == "[기재정정]사업보고서"
        assert added_disclosure.disclosure_type == "사업보고서"

    @pytest.mark.asyncio
    @patch('src.common.services.stock_service.dart_get_disclosures') # MOCK: dart_get_disclosures 함수
    async def test_update_disclosures_for_all_stocks_parses_disclosure_type(self, mock_dart_get_disclosures, stock_service):
        """전체 공시 갱신 시 disclosure_type이 올바르게 파싱되는지 테스트"""
        # GIVEN
        # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
        mock_db = MagicMock()
        # mock_dart_get_disclosures (AsyncMock) 호출 시 모의 공시 목록을 반환하도록 설정합니다.
        mock_dart_get_disclosures.return_value = [
            {"rcept_no": "5", "corp_name": "회사5", "report_nm": "[첨부정정]반기보고서", "rcept_dt": "20230105", "stock_code": "000005"}
        ]
        # mock_db.query().all() 호출 시 빈 목록을 반환하도록 설정하여 기존 공시가 없음을 모의합니다.
        mock_db.query.return_value.all.return_value = [] # 기존 공시 없음

        # WHEN
        await stock_service.update_disclosures_for_all_stocks(mock_db)

        # THEN
        # mock_db.bulk_save_objects (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_db.bulk_save_objects.assert_called_once()
        saved_disclosures = mock_db.bulk_save_objects.call_args[0][0]
        assert len(saved_disclosures) == 1
        assert saved_disclosures[0].title == "[첨부정정]반기보고서"
        assert saved_disclosures[0].disclosure_type == "반기보고서"
