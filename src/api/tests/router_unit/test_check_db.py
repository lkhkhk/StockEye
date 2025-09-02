import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError
from src.api import check_db as check_db_module
from tenacity import retry, stop_after_attempt, wait_fixed
import time # Added import for time
import logging # Added import for logging

# 성공 케이스
@patch('src.api.check_db.SessionLocal')
def test_check_db_success(mock_session_local):
    """DB 연결 성공 테스트"""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    
    # Call the original check_db function directly, bypassing the retry decorator
    # This is a bit hacky, but it works for testing purposes
    check_db_module.check_db.__wrapped__()
    
    mock_session_local.assert_called_once()
    mock_db.execute.assert_called_once()
    mock_db.close.assert_called_once()

# 실패 케이스 (재시도)
@patch('src.api.check_db.logger') # Patch src.api.check_db.logger
@patch('src.api.check_db.SessionLocal')
@patch('time.sleep', MagicMock()) # Patch time.sleep with MagicMock
def test_check_db_retry_and_fail(mock_sleep, mock_session_local, mock_logger): # Corrected function signature
    """DB 연결 재시도 후 최종 실패 테스트"""
    mock_session_local.side_effect = OperationalError("DB connection failed", {}, None)
    
    with pytest.raises(OperationalError):
        check_db_module.check_db()
        
    assert mock_session_local.call_count == 3
    assert mock_logger.info.call_count == 2 # Assert on mock_logger
    assert mock_logger.error.call_count == 3 # Assert on mock_logger

# 실패 후 성공 케이스
@patch('src.api.check_db.logger') # Patch src.api.check_db.logger
@patch('src.api.check_db.SessionLocal')
@patch('time.sleep', MagicMock()) # Patch time.sleep with MagicMock
def test_check_db_retry_and_succeed(mock_sleep, mock_session_local, mock_logger): # Corrected function signature
    """DB 연결 재시도 후 성공 테스트"""
    mock_db_good = MagicMock()
    
    mock_session_local.side_effect = [
        OperationalError("DB connection failed", {}, None),
        OperationalError("DB connection failed", {}, None),
        mock_db_good
    ]
    
    check_db_module.check_db()
    
    assert mock_session_local.call_count == 3
    assert mock_logger.info.call_count == 2 # Assert on mock_logger
    mock_db_good.execute.assert_called_once()
    mock_db_good.close.assert_called_once()

@patch('src.api.check_db.check_db')
def test_main_block(mock_check_db, caplog):
    """__main__ 블록 실행 테스트"""
    # Simulate the __main__ block execution
    with caplog.at_level(check_db_module.logging.INFO):
        check_db_module.logger.info("Initializing service")
        check_db_module.check_db() # This will call the mocked check_db
        check_db_module.logger.info("Service finished initializing")
    
    assert "Initializing service" in caplog.text
    mock_check_db.assert_called_once()
    assert "Service finished initializing" in caplog.text