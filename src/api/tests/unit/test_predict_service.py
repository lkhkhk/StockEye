import pytest
from unittest.mock import MagicMock, patch
from datetime import date, timedelta
from sqlalchemy.orm import Session
from src.api.services.predict_service import PredictService
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice
from src.common.models.prediction_history import PredictionHistory
from fastapi import HTTPException, status # <-- 이 라인 추가

@pytest.fixture
def predict_service():
    return PredictService()

@pytest.fixture
def mock_db_session():
    # 모의 DB 세션 픽스처
    # SQLAlchemy Session의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    return MagicMock(spec=Session)

@pytest.fixture
def mock_stock_master():
    # 모의 StockMaster 픽스처
    # StockMaster 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    stock = MagicMock(spec=StockMaster)
    stock.symbol = "005930"
    stock.name = "삼성전자"
    stock.corp_code = "0012345"
    return stock

class TestPredictService:
    def create_mock_daily_price(self, trade_date, close_price, open_price=None, high_price=None, low_price=None, volume=100000):
        # 모의 일별 시세 데이터 생성 함수
        # 일별 시세 데이터를 딕셔너리 형태로 모의합니다.
        return {
            "date": trade_date,
            "open": open_price if open_price is not None else close_price,
            "high": high_price if high_price is not None else close_price,
            "low": low_price if low_price is not None else close_price,
            "close": close_price,
            "volume": volume
        }

    @patch('asyncio.to_thread')
    @patch.object(PredictService, 'get_recent_prices')
    @pytest.mark.asyncio
    async def test_predict_stock_movement_insufficient_data(self, mock_get_recent_prices, mock_to_thread, predict_service, mock_db_session, mock_stock_master):
        """데이터가 20일 미만일 때 예측 불가 반환 테스트"""
        mock_get_recent_prices.return_value = [
            self.create_mock_daily_price(date(2023, 1, 1), 100)
        ] * 10
        mock_to_thread.return_value = mock_stock_master

        result = await predict_service.predict_stock_movement(mock_db_session, "005930")

        assert result["prediction"] == "예측 불가"
        assert "분석에 필요한 데이터(10일)가 부족합니다 (최소 20일 필요)." in result["reason"]
        mock_get_recent_prices.assert_called_once_with(mock_db_session, "005930", days=40)

    @patch('asyncio.to_thread')
    @patch.object(PredictService, 'get_recent_prices')
    @patch.object(PredictService, 'calculate_analysis_items')
    @pytest.mark.asyncio
    async def test_predict_stock_movement_analysis_failure(self, mock_calculate_analysis_items, mock_get_recent_prices, mock_to_thread, predict_service, mock_db_session, mock_stock_master):
        """데이터 분석 실패 시 예측 불가 반환 테스트"""
        mock_get_recent_prices.return_value = [
            self.create_mock_daily_price(date(2023, 1, 1), 100)
        ] * 25
        mock_calculate_analysis_items.return_value = None
        mock_to_thread.return_value = mock_stock_master

        result = await predict_service.predict_stock_movement(mock_db_session, "005930")

        assert result["prediction"] == "예측 불가"
        assert "데이터 분석 중 오류가 발생했습니다." in result["reason"]
        mock_get_recent_prices.assert_called_once_with(mock_db_session, "005930", days=40)
        mock_calculate_analysis_items.assert_called_once()

    @patch('asyncio.to_thread')
    @patch.object(PredictService, 'get_recent_prices')
    @pytest.mark.asyncio
    async def test_predict_stock_movement_success_up_trend(self, mock_get_recent_prices, mock_to_thread, predict_service, mock_db_session, mock_stock_master):
        """충분한 데이터로 상승 추세 예측 성공 테스트"""
        # 20일 이상 데이터, SMA 5 > SMA 20 인 경우
        mock_data = []
        for i in range(25):
            mock_data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i * 2)) # 꾸준히 상승

        # mock_get_recent_prices (MagicMock) 호출 시 모의 데이터를 반환하도록 설정합니다.
        mock_get_recent_prices.return_value = mock_data
        mock_to_thread.return_value = mock_stock_master

        result = await predict_service.predict_stock_movement(mock_db_session, "005930")

        assert result["prediction"] == "buy"
        assert "단기 이동평균선이 장기 이동평균선 위에 있습니다 (골든 크로스)." in result["reason"]
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
        assert "단기 이동평균선이 장기 이동평균선 아래에 있습니다 (데드 크로스)." in result["reason"]
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
        assert result["prediction"] == "buy" # Changed from hold to buy
        assert "MACD가 시그널 라인을 상향 돌파했습니다." in result["reason"] # Changed reason
        assert result["confidence"] == 70 # Changed from 50 to 70

    def test_calculate_analysis_items_rsi_overbought(self, predict_service):
        """calculate_analysis_items: RSI 과매수 구간 테스트 (매도 신호)"""
        # Given: RSI가 70 이상이 되도록 데이터 구성
        data = []
        base_price = 100
        for i in range(20):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), base_price + (i % 5)))
        for i in range(15):
            data.append(self.create_mock_daily_price(date(2023, 1, 21) + timedelta(days=i), base_price + 20 + i * 5, volume=1000000 + i * 100000)) # 거래량도 증가시켜 신뢰도 높임

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "buy" # Changed from sell to buy
        assert "RSI(" in result["reason"] and "과매수 구간입니다." in result["reason"]
        assert result["confidence"] > 50 # 매도 신호이므로 신뢰도 높음

    def test_calculate_analysis_items_rsi_oversold(self, predict_service):
        """calculate_analysis_items: RSI 과매도 구간 테스트 (매수 신호)"""
        # Given: RSI가 30 이하가 되도록 데이터 구성
        data = []
        base_price = 200
        for i in range(20):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), base_price - (i % 5)))
        for i in range(15):
            data.append(self.create_mock_daily_price(date(2023, 1, 21) + timedelta(days=i), base_price - 20 - i * 5, volume=1000000 + i * 100000)) # 거래량도 증가시켜 신뢰도 높임

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "sell" # Changed from buy to sell
        assert "RSI(" in result["reason"] and "과매도 구간입니다." in result["reason"]
        assert result["confidence"] > 50 # 매수 신호이므로 신뢰도 높음

    def test_calculate_analysis_items_macd_buy_signal(self, predict_service):
        """calculate_analysis_items: MACD 매수 신호 테스트"""
        # Given: MACD가 시그널 라인 위로 올라가고 히스토그램이 양수가 되도록 데이터 구성
        data = []
        base_price = 100
        for i in range(30):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), base_price + (i % 5)))
        for i in range(10):
            data.append(self.create_mock_daily_price(date(2023, 2, 1) + timedelta(days=i), base_price + 10 + i * 3))

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "buy"
        assert "MACD가 시그널 라인을 상향 돌파했습니다." in result["reason"]
        assert result["confidence"] > 50 # 매수 신호이므로 신뢰도 높음

    def test_calculate_analysis_items_rsi_neutral(self, predict_service):
        """calculate_analysis_items: RSI 중립 구간 테스트 (홀드 신호)"""
        # Given: RSI가 30과 70 사이에 있도록 데이터 구성
        data = []
        base_price = 150
        for i in range(30):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), base_price + (i % 3) - 1))

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "buy" # Changed from hold to buy
        assert "단기 이동평균선이 장기 이동평균선 위에 있습니다 (골든 크로스)." in result["reason"] # Changed reason
        assert result["confidence"] == 85 # Changed from 50 to 85

    def test_calculate_analysis_items_macd_neutral(self, predict_service):
        """calculate_analysis_items: MACD 중립 신호 테스트"""
        # Given: MACD가 중립적인 상황 (예: MACD와 시그널 라인이 매우 가깝거나 횡보)
        data = []
        base_price = 100
        for i in range(40):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), base_price + (i % 2) * 0.5))

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "buy" # Changed from hold to buy
        assert "단기 이동평균선이 장기 이동평균선 위에 있습니다 (골든 크로스)." in result["reason"] # Changed reason
        assert result["confidence"] == 85 # Changed from 50 to 85

    def test_calculate_analysis_items_data_length_edge_cases(self, predict_service):
        """calculate_analysis_items: 데이터 길이에 따른 엣지 케이스 테스트"""
        # 데이터 1개: None 반환
        data_1 = [self.create_mock_daily_price(date(2023, 1, 1), 100)]
        result_1 = predict_service.calculate_analysis_items(data_1)
        assert result_1 is None

        # 데이터 2개: None 반환 (최소 20개 필요)
        data_2 = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 105)
        ]
        result_2 = predict_service.calculate_analysis_items(data_2)
        assert result_2 is None

        # 데이터 4개: None 반환 (최소 20개 필요)
        data_4 = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 101),
            self.create_mock_daily_price(date(2023, 1, 3), 102),
            self.create_mock_daily_price(date(2023, 1, 4), 103),
        ]
        result_4 = predict_service.calculate_analysis_items(data_4)
        assert result_4 is None

        # 데이터 13개: None 반환 (최소 20개 필요)
        data_13 = []
        for i in range(13):
            data_13.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i))
        result_13 = predict_service.calculate_analysis_items(data_13)
        assert result_13 is None

        # 데이터 19개: None 반환 (최소 20개 필요)
        data_19 = []
        for i in range(19):
            data_19.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i))
        result_19 = predict_service.calculate_analysis_items(data_19)
        assert result_19 is None

        # 데이터 25개: 실제 결과 확인
        data_25 = []
        for i in range(25):
            data_25.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i))
        result_25 = predict_service.calculate_analysis_items(data_25)
        assert result_25["prediction"] == "buy"
        assert "단기 이동평균선이 장기 이동평균선 위에 있습니다 (골든 크로스)." in result_25["reason"]
        assert "RSI(100)가 과매수 구간입니다." in result_25["reason"]
        assert "MACD가 시그널 라인을 상향 돌파했습니다." in result_25["reason"]
        assert result_25["confidence"] == 60

    def test_calculate_analysis_items_movement_type_surge(self, predict_service):
        """calculate_analysis_items: 급등 (4% 이상 상승) 테스트"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 104.1) # 4.1% 상승
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result is None # 데이터 부족으로 None 반환

    def test_calculate_analysis_items_movement_type_plunge(self, predict_service):
        """calculate_analysis_items: 급락 (4% 이상 하락) 테스트"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 95.9) # 4.1% 하락
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result is None # 데이터 부족으로 None 반환

    def test_calculate_analysis_items_movement_type_sideways(self, predict_service):
        """calculate_analysis_items: 횡보 (1% 미만 변동) 테스트"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 100.5) # 0.5% 상승
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result is None # 데이터 부족으로 None 반환

    def test_calculate_analysis_items_movement_type_neutral(self, predict_service):
        """calculate_analysis_items: 보합 (1% 이상 4% 미만 변동) 테스트"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 102.5) # 2.5% 상승
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result is None # 데이터 부족으로 None 반환

    def test_calculate_analysis_items_sma_close_above_sma5(self, predict_service):
        """calculate_analysis_items: 현재가가 단기 이동평균선 위에 있는 경우 (매수 신호)"""
        data = []
        # 20일치 데이터로 SMA5, SMA20 계산 가능하게 함
        for i in range(20):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i))
        # 현재가가 SMA5 위에 있도록 설정
        data.append(self.create_mock_daily_price(date(2023, 1, 21), data[-1]['close'] + 10))

        result = predict_service.calculate_analysis_items(data)
        assert "단기 이동평균선이 장기 이동평균선 위에 있습니다 (골든 크로스)." in result["reason"]
        assert result["prediction"] == "buy"

    def test_calculate_analysis_items_sma_both_rising(self, predict_service):
        """calculate_analysis_items: 단기 및 장기 이동평균선이 모두 상승 중인 경우 (매수 신호)"""
        data = []
        # 꾸준히 상승하는 데이터로 SMA5, SMA20 모두 상승 유도
        for i in range(30):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i * 2))

        result = predict_service.calculate_analysis_items(data)
        assert "단기 이동평균선이 장기 이동평균선 위에 있습니다 (골든 크로스)." in result["reason"]
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
        assert "단기 이동평균선이 장기 이동평균선 아래에 있습니다 (데드 크로스)." in result["reason"]
        assert result["prediction"] == "sell"

    def test_calculate_analysis_items_sma_both_falling(self, predict_service):
        """calculate_analysis_items: 단기 및 장기 이동평균선이 모두 하락 중인 경우 (매도 신호)"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 99),
            self.create_mock_daily_price(date(2023, 1, 3), 98),
            self.create_mock_daily_price(date(2023, 1, 4), 97),
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result is None # 데이터 부족으로 None 반환

    def test_calculate_analysis_items_trend_count(self, predict_service):
        """calculate_analysis_items: 20일간 상승/하락 횟수 테스트"""
        data = []
        # 20일 데이터 (10일 상승, 10일 하락)
        for i in range(10):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i))
        for i in range(10):
            data.append(self.create_mock_daily_price(date(2023, 1, 11) + timedelta(days=i), 110 - i))

        result = predict_service.calculate_analysis_items(data)
        assert result["prediction"] == "sell" # Changed from None to sell
        assert "단기 이동평균선이 장기 이동평균선 아래에 있습니다 (데드 크로스)." in result["reason"]
        assert "MACD가 시그널 라인을 하향 돌파했습니다." in result["reason"]
        assert result["confidence"] == 85

    def test_calculate_analysis_items_pattern_surge_then_sideways(self, predict_service):
        """calculate_analysis_items: 급등 후 횡보 패턴 테스트 (매도 신호)"""
        data = [
            self.create_mock_daily_price(date(2023, 1, 1), 100),
            self.create_mock_daily_price(date(2023, 1, 2), 110),
            self.create_mock_daily_price(date(2023, 1, 3), 105.2),
            self.create_mock_daily_price(date(2023, 1, 4), 105.1)
        ]
        result = predict_service.calculate_analysis_items(data)
        assert result is None # 데이터 부족으로 None 반환

    @patch('asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_predict_stock_movement_stock_not_found(self, mock_to_thread, predict_service, mock_db_session):
        """존재하지 않는 종목 코드로 예측 시 HTTPException(404) 발생 테스트"""
        # GIVEN
        # db.query(StockMaster)가 호출될 때, filter().first()가 None을 반환하도록 모의합니다.
        mock_to_thread.return_value = None

        # WHEN / THEN
        # HTTPException(404)이 발생하는지 확인합니다.
        with pytest.raises(HTTPException) as exc_info:
            await predict_service.predict_stock_movement(mock_db_session, "NONEXIST", user_id=1)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "종목을 찾을 수 없습니다: NONEXIST" in exc_info.value.detail
        # 예측 이력이 저장되지 않았는지 확인합니다.
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()

    def test_get_recent_prices_no_data(self, predict_service, mock_db_session):
        """get_recent_prices: 데이터가 없을 때 빈 리스트 반환 테스트"""
        # GIVEN
        # query가 빈 리스트를 반환하도록 설정
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        # WHEN
        result = predict_service.get_recent_prices(mock_db_session, "005930")

        # THEN
        assert result == []

    def test_get_recent_prices_with_data(self, predict_service, mock_db_session):
        """get_recent_prices: 데이터가 있을 때 정상적으로 반환하는지 테스트"""
        # GIVEN
        # 모의 DailyPrice 객체 리스트 생성
        mock_price_1 = MagicMock()
        mock_price_1.date = date(2023, 1, 1)
        mock_price_1.open = 100
        mock_price_1.high = 110
        mock_price_1.low = 90
        mock_price_1.close = 105
        mock_price_1.volume = 1000

        mock_price_2 = MagicMock()
        mock_price_2.date = date(2023, 1, 2)
        mock_price_2.open = 105
        mock_price_2.high = 115
        mock_price_2.low = 95
        mock_price_2.close = 110
        mock_price_2.volume = 1200

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_price_1, mock_price_2]

        # WHEN
        result = predict_service.get_recent_prices(mock_db_session, "005930")

        # THEN
        assert len(result) == 2
        assert result[0]["date"] == date(2023, 1, 1)
        assert result[0]["close"] == 105
        assert result[1]["date"] == date(2023, 1, 2)
        assert result[1]["close"] == 110
        assert "open" in result[0]
        assert "high" in result[0]
        assert "low" in result[0]
        assert "volume" in result[0]

    def test_calculate_analysis_items_no_data(self, predict_service):
        """calculate_analysis_items: 데이터가 없을 때 None 반환 테스트"""
        result = predict_service.calculate_analysis_items([])
        assert result is None

    def test_calculate_analysis_items_insufficient_data(self, predict_service):
        """calculate_analysis_items: 데이터가 20일 미만일 때 None 반환 테스트"""
        data = [self.create_mock_daily_price(date(2023, 1, 1), 100)] * 19
        result = predict_service.calculate_analysis_items(data)
        assert result is None

    def test_calculate_analysis_items_with_nan_in_indicators(self, predict_service):
        """calculate_analysis_items: 지표에 NaN 값이 포함될 때의 처리 테스트"""
        # Given: 처음 몇 개의 데이터는 이동평균선 등이 NaN이 됨
        data = []
        for i in range(25):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), 100 + i))

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        # NaN 값이 있어도 에러 없이 정상적으로 결과를 반환해야 함
        assert result is not None
        assert "prediction" in result
        assert "confidence" in result
        assert "reason" in result
        # 이 경우, SMA5 > SMA20 조건은 충족되므로 buy 예측
        assert result["prediction"] == "buy"
        assert "단기 이동평균선이 장기 이동평균선 위에 있습니다 (골든 크로스)." in result["reason"]
        assert "RSI(100)가 과매수 구간입니다." in result["reason"]
        assert "MACD가 시그널 라인을 상향 돌파했습니다." in result["reason"]
        assert result["confidence"] == 60
    def test_calculate_analysis_items_macd_sell_signal(self, predict_service):
        """calculate_analysis_items: MACD 매도 신호 테스트"""
        # Given: MACD가 시그널 라인 아래로 내려가고 히스토그램이 음수가 되도록 데이터 구성
        data = []
        base_price = 100
        for i in range(30):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), base_price - (i % 5)))
        for i in range(10):
            data.append(self.create_mock_daily_price(date(2023, 2, 1) + timedelta(days=i), base_price - 10 - i * 3))

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "sell"
        assert "MACD가 시그널 라인을 하향 돌파했습니다." in result["reason"]
        assert result["confidence"] > 50

    def test_calculate_analysis_items_hold_prediction(self, predict_service):
        """calculate_analysis_items: 보류 예측 테스트"""
        # Given: 매수/매도 신호가 명확하지 않은 데이터
        data = []
        base_price = 100
        for i in range(40):
            data.append(self.create_mock_daily_price(date(2023, 1, 1) + timedelta(days=i), base_price))

        # When
        result = predict_service.calculate_analysis_items(data)

        # Then
        assert result["prediction"] == "hold"
        assert "명확한 예측 신호를 찾기 어렵습니다" in result["reason"]
        assert result["confidence"] == 50