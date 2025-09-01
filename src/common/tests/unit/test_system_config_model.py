
import pytest
from src.common.models.system_config import SystemConfig

def test_system_config_model_creation():
    """
    SystemConfig 모델 객체가 정상적으로 생성되고,
    속성이 올바르게 설정되는지 테스트합니다.
    """
    # Given
    key = "test_key"
    value = "test_value"

    # When
    system_config = SystemConfig(key=key, value=value)

    # Then
    assert system_config.key == key
    assert system_config.value == value
