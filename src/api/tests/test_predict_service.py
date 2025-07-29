import pytest
from unittest.mock import MagicMock, patch
from datetime import date, timedelta
from sqlalchemy.orm import Session
from src.api.services.predict_service import PredictService
from src.api.models.stock_master import StockMaster
from src.api.models.daily_price import DailyPrice
from src.api.models.prediction_history import PredictionHistory

@pytest.fixture
def predict_service():
    return PredictService()

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_stock_master():
    stock = MagicMock(spec=StockMaster)
    stock.symbol = "005930"
    stock.name = "삼성전자"
    stock.corp_code = "0012345"
    return stock

def create_mock_daily_price(trade_date, close_price, open_price=None, high_price=None, low_price=None, volume=100000):
    return {
        "date": trade_date,
        "open": open_price if open_price is not None else close_price,
        "high": high_price if high_price is not None else close_price,
        "low": low_price if low_price is not None else close_price,
        "close": close_price,
        "volume": volume
    }

class TestPredictService:
    def create_mock_daily_price(self, trade_date, close_price, open_price=None, high_price=None, low_price=None, volume=100000):
        return {
            "date": trade_date,
            "open": open_price if open_price is not None else close_price,
            "high": high_price if high_price is not None else close_price,
            "low": low_price if low_price is not None else close_price,
            "close": close_price,
            "volume": volume
        }

    @patch.object(PredictService, 'get_recent_prices')
    def test_predict_stock_movement_insufficient_data(self, mock_get_recent_prices, predict_service, mock_db_session):
        """데이터가 20일 미만일 때 예측 불가 반환 테스트"""
        mock_get_recent_prices.return_value = [
            self.create_mock_daily_price(date(2023, 1, 1), 100)
        ] * 10  # 10일치 데이터

        result = predict_service.predict_stock_movement(mock_db_session, "005930")

        assert result["prediction"] == "예측 불가"
        assert "최소 20일 필요" in result["reason"]
        mock_get_recent_prices.assert_called_once_with(mock_db_session, "005930", days=40)

    @patch.object(PredictService, 'get_recent_prices')
    @patch.object(PredictService, 'calculate_analysis_items')
    def test_predict_stock_movement_analysis_failure(self, mock_calculate_analysis_items, mock_get_recent_prices, predict_service, mock_db_session):
        """데이터 분석 실패 시 예측 불가 반환 테스트"""
        mock_get_recent_prices.return_value = [
            self.create_mock_daily_price(date(2023, 1, 1), 100)
        ] * 25  # 25일치 데이터 (충분)
        mock_calculate_analysis_items.return_value = None  # 분석 실패 가정

        result = predict_service.predict_stock_movement(mock_db_session, "005930")

        assert result["prediction"] == "예측 불가"
        assert "데이터 분석 중 오류가 발생했습니다." in result["reason"]
        mock_get_recent_prices.assert_called_once_with(mock_db_session, "005930", days=40)
        mock_calculate_analysis_items.assert_called_once()

    @patch.object(PredictService, 'get_recent_prices')
    def test_predict_stock_movement_success_up_trend(self, mock_get_recent_prices, predict_service, mock_db_session):
        """충분한 데이터로 상승 추세 예측 성공 테스트"""
        # 20일 이상 데이터, SMA 5 > SMA 20 인 경우
        mock_data = []
        for i in range(25):
            mock_data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i * 2)) # 꾸준히 상승

        mock_get_recent_prices.return_value = mock_data

        result = predict_service.predict_stock_movement(mock_db_session, "005930")

        assert result["prediction"] == "hold" # 기본 예측은 hold
        assert result["trend"] == "상승"
        assert "상승" in result["reason"]

    @patch.object(PredictService, 'get_recent_prices')
    def test_predict_stock_movement_success_down_trend(self, mock_get_recent_prices, predict_service, mock_db_session):
        """충분한 데이터로 하락 추세 예측 성공 테스트"""
        # 20일 이상 데이터, SMA 5 < SMA 20 인 경우
        mock_data = []
        for i in range(25):
            mock_data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 200 - i * 2)) # 꾸준히 하락

        mock_get_recent_prices.return_value = mock_data

        result = predict_service.predict_stock_movement(mock_db_session, "005930")

        assert result["prediction"] == "hold"
        assert result["trend"] == "하락"
        assert "하락" in result["reason"]

    @patch.object(PredictService, 'get_recent_prices')
    def test_predict_stock_movement_success_sideways_trend(self, mock_get_recent_prices, predict_service, mock_db_session):
        """충분한 데이터로 횡보 추세 예측 성공 테스트"""
        # 20일 이상 데이터, SMA 5 == SMA 20 인 경우
        mock_data = []
        for i in range(25):
            mock_data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 150 + (i % 3) - 1)) # 횡보

        mock_get_recent_prices.return_value = mock_data

        result = predict_service.predict_stock_movement(mock_db_session, "005930")

        assert result["prediction"] == "hold"
        assert result["trend"] == "횡보"
        assert "횡보" in result["reason"]

    @patch.object(PredictService, 'get_recent_prices')
    def test_predict_stock_movement_buy_signal(self, mock_get_recent_prices, predict_service, mock_db_session):
        """매수 신호 (저점 횡보) 예측 테스트"""
        mock_data = []
        # 급락 후 횡보하는 데이터
        for i in range(20): # 20일간 하락
            mock_data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 200 - i * 5))
        for i in range(5): # 5일간 횡보 (저점)
            mock_data.append(self.create_mock_daily_price(date(2023, 1, 20) + timedelta(days=i), 100 + (i % 2)))

        mock_get_recent_prices.return_value = mock_data

        result = predict_service.predict_stock_movement(mock_db_session, "005930")
        assert result["prediction"] == "buy"
        assert "저점 횡보 패턴 감지" in result["reason"]

    @patch.object(PredictService, 'get_recent_prices')
    def test_predict_stock_movement_sell_signal(self, mock_get_recent_prices, predict_service, mock_db_session):
        """매도 신호 (급등 후 횡보) 예측 테스트"""
        mock_data = []
        # 급등 후 횡보하는 데이터
        for i in range(20): # 20일간 상승
            mock_data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i * 5))
        # 직전일 급등 (4% 이상)
        mock_data.append(self.create_mock_daily_price(date(2023, 1, 21), mock_data[-1]['close'] * 1.05, volume=100000))
        # 금일 횡보 (1% 미만 변동)
        mock_data.append(self.create_mock_daily_price(date(2023, 1, 22), mock_data[-1]['close'] * 1.005, volume=100000))

        mock_get_recent_prices.return_value = mock_data

        result = predict_service.predict_stock_movement(mock_db_session, "005930")
        assert result["prediction"] == "sell"
        assert "급등 후 횡보 패턴 감지" in result["reason"]

