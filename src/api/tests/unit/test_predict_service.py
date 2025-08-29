import pytest
from unittest.mock import MagicMock, patch
from datetime import date, timedelta
from sqlalchemy.orm import Session
from src.api.services.predict_service import PredictService
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice
from src.common.models.prediction_history import PredictionHistory

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

        assert result["prediction"] == "buy"
        assert result["trend"] == "상승"
        assert "상승" in result["reason"]
        assert "confidence" in result
        assert result["confidence"] > 50 # 신뢰도 증가 확인

    def test_calculate_analysis_items_basic_down_trend(self, predict_service):
        """calculate_analysis_items: 기본적인 하락 추세 테스트"""
        # Given: 꾸준히 하락하는 25일치 데이터
        data = []
        for i in range(25):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 200 - i * 2))

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "sell"
        assert result["trend"] == "하락"
        assert "단기 이동평균선이 장기 이동평균선 아래에 있습니다 (데드 크로스 또는 역배열)." in result["reason"]
        assert result["confidence"] > 50 # 하락 추세이므로 신뢰도 높음

    def test_calculate_analysis_items_basic_sideways_trend(self, predict_service):
        """calculate_analysis_items: 기본적인 횡보 추세 테스트"""
        # Given: 횡보하는 25일치 데이터 (SMA 5와 SMA 20이 비슷)
        data = []
        for i in range(25):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 150 + (i % 5) * 0.01)) # 횡보하는 데이터로 변경

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "hold"
        assert result["trend"] == "횡보"
        assert "단기 이동평균선과 장기 이동평균선이 수렴 중입니다 (횡보)." in result["reason"]
        assert result["confidence"] == 50 # 횡보이므로 중립 신뢰도

    def test_calculate_analysis_items_rsi_overbought(self, predict_service):
        """calculate_analysis_items: RSI 과매수 구간 테스트 (매도 신호)"""
        # Given: RSI가 70 이상이 되도록 데이터 구성
        data = []
        base_price = 100
        for i in range(20): # 초기 데이터
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), base_price + (i % 5)))
        for i in range(15): # 급격한 상승으로 RSI 70 이상 유도
            data.append(self.create_mock_daily_price(date(2023, 1, 21) + timedelta(days=i), base_price + 20 + i * 5, volume=1000000 + i * 100000)) # 거래량도 증가시켜 신뢰도 높임

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "sell"
        assert "RSI(70)가 70 이상으로 과매수 구간입니다." in result["reason"]
        assert result["confidence"] > 50 # 매도 신호이므로 신뢰도 높음

    def test_calculate_analysis_items_rsi_oversold(self, predict_service):
        """calculate_analysis_items: RSI 과매도 구간 테스트 (매수 신호)"""
        # Given: RSI가 30 이하가 되도록 데이터 구성
        data = []
        base_price = 200
        for i in range(20): # 초기 데이터
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), base_price - (i % 5)))
        for i in range(15): # 급격한 하락으로 RSI 30 이하 유도
            data.append(self.create_mock_daily_price(date(2023, 1, 21) + timedelta(days=i), base_price - 20 - i * 5, volume=1000000 + i * 100000)) # 거래량도 증가시켜 신뢰도 높임

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "buy"
        assert "RSI(29)가 30 이하로 과매도 구간입니다." in result["reason"]
        assert result["confidence"] > 50 # 매수 신호이므로 신뢰도 높음

    def test_calculate_analysis_items_macd_buy_signal(self, predict_service):
        """calculate_analysis_items: MACD 매수 신호 테스트"""
        # Given: MACD가 시그널 라인 위로 올라가고 히스토그램이 양수가 되도록 데이터 구성
        data = []
        base_price = 100
        for i in range(30): # 초기 데이터
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), base_price + (i % 5)))
        for i in range(10): # MACD 골든 크로스 유도
            data.append(self.create_mock_daily_price(date(2023, 2, 1) + timedelta(days=i), base_price + 10 + i * 3))

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "buy"
        assert "MACD가 시그널 라인 위에 있고 MACD 히스토그램이 양수입니다 (매수 신호)." in result["reason"]
        assert result["confidence"] > 50 # 매수 신호이므로 신뢰도 높음

    def test_calculate_analysis_items_rsi_neutral(self, predict_service):
        """calculate_analysis_items: RSI 중립 구간 테스트 (홀드 신호)"""
        # Given: RSI가 30과 70 사이에 있도록 데이터 구성
        data = []
        base_price = 150
        for i in range(30): # RSI가 중립 구간에 머물도록 완만한 변동
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), base_price + (i % 3) - 1))

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "hold"
        assert "RSI는 중립 구간입니다." in result["reason"]
        assert result["confidence"] == 50 # 중립 신호이므로 기본 신뢰도

    def test_calculate_analysis_items_macd_neutral(self, predict_service):
        """calculate_analysis_items: MACD 중립 신호 테스트"""
        # Given: MACD가 중립적인 상황 (예: MACD와 시그널 라인이 매우 가깝거나 횡보)
        data = []
        base_price = 100
        for i in range(40): # MACD가 중립 구간에 머물도록 완만한 변동
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), base_price + (i % 2) * 0.5))

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "hold"
        assert "MACD는 중립 신호입니다." in result["reason"]
        assert result["confidence"] == 50 # 중립 신호이므로 기본 신뢰도

    def test_calculate_analysis_items_data_length_edge_cases(self, predict_service):
        """calculate_analysis_items: 데이터 길이에 따른 엣지 케이스 테스트"""
        # 데이터 1개: None 반환
        data_1 = [self.create_mock_daily_price(date(2023, 1, 1), 100)]
        result_1 = predict_service.calculate_analysis_items(data_1)
        assert result_1 is None

        # 데이터 2개: daily_change_percent만 계산
        data_2 = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 105)
        ]
        result_2 = predict_service.calculate_analysis_items(data_2)
        assert result_2["movement_type"] == "보합" # 5% 상승이므로 보합
        assert result_2["trend"] == "정보 부족" # SMA 계산 불가
        assert result_2["reason"] == "현재 데이터로는 명확한 예측 신호를 찾기 어렵습니다." # RSI, MACD 계산 불가

        # 데이터 4개: sma_5 계산 불가
        data_4 = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 101),
            self.create_mock_daily_price(date(2023, 1, 3), 102),
            self.create_mock_daily_price(date(2023, 1, 4), 103),
        ]
        result_4 = predict_service.calculate_analysis_items(data_4)
        assert result_4["trend"] == "정보 부족" # SMA 계산 불가

        # 데이터 13개: rsi 계산 불가
        data_13 = []
        for i in range(13):
            data_13.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i))
        result_13 = predict_service.calculate_analysis_items(data_13)
        assert result_13["reason"] == "현재 데이터로는 명확한 예측 신호를 찾기 어렵습니다." # RSI 계산 불가

        # 데이터 19개: sma_20, trend_count 계산 불가
        data_19 = []
        for i in range(19):
            data_19.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i))
        result_19 = predict_service.calculate_analysis_items(data_19)
        assert result_19["trend"] == "정보 부족" # SMA20 계산 불가
        assert result_19["trend_count"] == {"up": 0, "down": 0} # 20일 데이터 부족

        # 데이터 25개: macd 계산 불가
        data_25 = []
        for i in range(25):
            data_25.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i))
        result_25 = predict_service.calculate_analysis_items(data_25)
        assert result_25["reason"] == "현재 데이터로는 명확한 예측 신호를 찾기 어렵습니다." # MACD 계산 불가

    def test_calculate_analysis_items_movement_type_surge(self, predict_service):
        """calculate_analysis_items: 급등 (4% 이상 상승) 테스트"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 104.1) # 4.1% 상승
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result["movement_type"] == "급등"

    def test_calculate_analysis_items_movement_type_plunge(self, predict_service):
        """calculate_analysis_items: 급락 (4% 이상 하락) 테스트"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 95.9) # 4.1% 하락
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result["movement_type"] == "급락"

    def test_calculate_analysis_items_movement_type_sideways(self, predict_service):
        """calculate_analysis_items: 횡보 (1% 미만 변동) 테스트"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 100.5) # 0.5% 상승
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result["movement_type"] == "횡보"

    def test_calculate_analysis_items_movement_type_neutral(self, predict_service):
        """calculate_analysis_items: 보합 (1% 이상 4% 미만 변동) 테스트"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 102.5) # 2.5% 상승
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result["movement_type"] == "보합"

    def test_calculate_analysis_items_sma_close_above_sma5(self, predict_service):
        """calculate_analysis_items: 현재가가 단기 이동평균선 위에 있는 경우 (매수 신호)"""
        data = []
        # 20일치 데이터로 SMA5, SMA20 계산 가능하게 함
        for i in range(20):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i))
        # 현재가가 SMA5 위에 있도록 설정
        data.append(self.create_mock_daily_price(date(2023, 1, 21), data[-1]['close'] + 10))

        result = predict_service.calculate_analysis_items(data)
        assert "현재가가 단기 이동평균선 위에 있습니다." in result["reason"]
        assert result["prediction"] == "buy"

    def test_calculate_analysis_items_sma_both_rising(self, predict_service):
        """calculate_analysis_items: 단기 및 장기 이동평균선이 모두 상승 중인 경우 (매수 신호)"""
        data = []
        # 꾸준히 상승하는 데이터로 SMA5, SMA20 모두 상승 유도
        for i in range(30):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i * 2))

        result = predict_service.calculate_analysis_items(data)
        assert "단기 및 장기 이동평균선이 모두 상승 중입니다." in result["reason"]
        assert result["prediction"] == "buy"

    def test_calculate_analysis_items_sma_close_below_sma5(self, predict_service):
        """calculate_analysis_items: 현재가가 단기 이동평균선 아래에 있는 경우 (매도 신호)"""
        data = []
        # 20일치 데이터로 SMA5, SMA20 계산 가능하게 함
        for i in range(20):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 200 - i))
        # 현재가가 SMA5 아래에 있도록 설정
        data.append(self.create_mock_daily_price(date(2023, 1, 21), data[-1]['close'] - 10))

        result = predict_service.calculate_analysis_items(data)
        assert "현재가가 단기 이동평균선 아래에 있습니다." in result["reason"]
        assert result["prediction"] == "sell"

    def test_calculate_analysis_items_sma_both_falling(self, predict_service):
        """calculate_analysis_items: 단기 및 장기 이동평균선이 모두 하락 중인 경우 (매도 신호)"""
        data = []
        # 꾸준히 하락하는 데이터로 SMA5, SMA20 모두 하락 유도
        for i in range(30):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 200 - i * 2))

        result = predict_service.calculate_analysis_items(data)
        assert "단기 및 장기 이동평균선이 모두 하락 중입니다." in result["reason"]
        assert result["prediction"] == "sell"

    def test_calculate_analysis_items_sideways_low_point_buy_opportunity(self, predict_service):
        """calculate_analysis_items: 횡보 추세에서 저점 매수 기회 테스트"""
        data = []
        # 20일치 횡보 데이터 (약간의 상승 추세)
        for i in range(20):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i * 0.5))
        # 현재가가 20일 최저가에 근접하도록 설정 (매수 기회)
        data.append(self.create_mock_daily_price(date(2023, 1, 21), 100.5))

        result = predict_service.calculate_analysis_items(data)
        assert result["prediction"] == "buy"
        assert "저점 횡보 패턴 감지 (매수 기회)." in result["reason"]
        assert result["confidence"] > 50 # 매수 신호이므로 신뢰도 높음

    def test_calculate_analysis_items_trend_duration_up(self, predict_service):
        """calculate_analysis_items: 상승 추세 지속 기간 테스트"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 101),
            self.create_mock_daily_price(date(2023, 1, 3), 102),
            self.create_mock_daily_price(date(2023, 1, 4), 103),
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result["trend_duration"] == "3일"

    def test_calculate_analysis_items_trend_duration_down(self, predict_service):
        """calculate_analysis_items: 하락 추세 지속 기간 테스트"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 99),
            self.create_mock_daily_price(date(2023, 1, 3), 98),
            self.create_mock_daily_price(date(2023, 1, 4), 97),
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result["trend_duration"] == "3일"

    def test_calculate_analysis_items_volume_trend_duration_up(self, predict_service):
        """calculate_analysis_items: 거래량 상승 추세 지속 기간 테스트"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100, volume=1000),
            self.create_mock_daily_price(date(2023, 1, 2), 101, volume=1100),
            self.create_mock_daily_price(date(2023, 1, 3), 102, volume=1200),
            self.create_mock_daily_price(date(2023, 1, 4), 103, volume=1300),
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result["volume_trend_duration"] == "3일"

    def test_calculate_analysis_items_volume_trend_duration_down(self, predict_service):
        """calculate_analysis_items: 거래량 하락 추세 지속 기간 테스트"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100, volume=1300),
            self.create_mock_daily_price(date(2023, 1, 2), 101, volume=1200),
            self.create_mock_daily_price(date(2023, 1, 3), 102, volume=1100),
            self.create_mock_daily_price(date(2023, 1, 4), 103, volume=1000),
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result["volume_trend_duration"] == "3일"

    def test_calculate_analysis_items_trend_count(self, predict_service):
        """calculate_analysis_items: 20일간 상승/하락 횟수 테스트"""
        data = []
        # 20일 데이터 (10일 상승, 10일 하락)
        for i in range(10):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i))
        for i in range(10):
            data.append(self.create_mock_daily_price(date(2023, 1, 11) + timedelta(days=i), 110 - i))

        result = predict_service.calculate_analysis_items(data)
        assert result["trend_count"] == {"up": 10, "down": 9}

    def test_calculate_analysis_items_pattern_surge_then_sideways(self, predict_service):
        """calculate_analysis_items: 급등 후 횡보 패턴 테스트 (매도 신호)"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100), # Day 1
            self.create_mock_daily_price(date(2023, 1, 2), 110), # Day 2: 10% 상승 (급등)
            self.create_mock_daily_price(date(2023, 1, 3), 105.2), # Day 3: 0.19% 상승 (횡보)
            self.create_mock_daily_price(date(2023, 1, 4), 105.1) # Day 4: 횡보 유지
        ]
        # SMA와 MACD가 매도 신호를 보내도록 추가 데이터 조정
        for i in range(10):
            data.append(self.create_mock_daily_price(date(2023, 1, 5) + timedelta(days=i), 105.1 - i * 0.1)) # 하락 추세 유도 (RSI 중립 유도)
        result = predict_service.calculate_analysis_items(data)
        assert result["prediction"] == "sell"
        assert "급등 후 횡보 패턴 감지 (차익 실현 가능성)." in result["reason"]
        assert result["confidence"] > 50 # 매도 신호이므로 신뢰도 높음

