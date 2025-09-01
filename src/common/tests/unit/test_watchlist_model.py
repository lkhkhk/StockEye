
import pytest
from src.common.models.watchlist import Watchlist

def test_watchlist_model_creation():
    """
    Watchlist 모델 객체가 정상적으로 생성되고,
    속성이 올바르게 설정되는지 테스트합니다.
    """
    # Given
    user_id = 12345
    symbol = "005930"  # Samsung Electronics

    # When
    watchlist_item = Watchlist(user_id=user_id, symbol=symbol)

    # Then
    assert watchlist_item.user_id == user_id
    assert watchlist_item.symbol == symbol
