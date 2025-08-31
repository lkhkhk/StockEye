# 이 파일은 src.common.database.db_connector 모듈의 단위 테스트를 포함합니다.
#
# get_db 함수의 핵심 기능은 데이터베이스 세션을 생성하고, 사용 후
# 안전하게 닫는 것입니다. 이 테스트는 실제 데이터베이스에 연결하는 대신
# SessionLocal 객체를 모의(mock)하여 이 세션 관리 로직이 정확히
# 동작하는지만을 검증합니다.

import pytest
from unittest.mock import patch, MagicMock

from sqlalchemy.orm import Session

from src.common.database.db_connector import get_db, SessionLocal


def test_get_db():
    """get_db 의존성 주입 함수의 세션 생성 및 종료 로직을 테스트합니다."""
    # MOCK: SessionLocal
    # SessionLocal을 모의 객체로 대체하여 실제 DB 세션을 생성하지 않도록 합니다.
    # MagicMock: SessionLocal은 동기적으로 동작하는 클래스이므로 MagicMock을 사용합니다.
    mock_session = MagicMock(spec=Session)
    
    with patch('src.common.database.db_connector.SessionLocal', return_value=mock_session) as mock_session_local:
        
        db_generator = get_db()
        
        # 1. 제너레이터에서 세션을 정상적으로 가져오는지 확인합니다.
        db_session = next(db_generator)
        assert db_session is mock_session
        # mock_session_local (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_session_local.assert_called_once()
        
        # 2. `yield` 이후, 제너레이터가 종료될 때 세션의 close() 메서드가
        #    정확히 한 번 호출되는지 확인합니다.
        with pytest.raises(StopIteration):
            next(db_generator)
        
        # mock_session.close (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_session.close.assert_called_once()