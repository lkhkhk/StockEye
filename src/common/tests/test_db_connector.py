import pytest
from unittest.mock import patch, MagicMock

from sqlalchemy.orm import Session

from src.common.db_connector import get_db, SessionLocal


def test_get_db():
    """Test the get_db dependency to ensure it yields a session and closes it."""
    # Mock SessionLocal to control the session object
    mock_session = MagicMock(spec=Session)
    
    with patch('src.common.db_connector.SessionLocal', return_value=mock_session) as mock_session_local:
        
        db_generator = get_db()
        
        # 1. Get the session from the generator
        db_session = next(db_generator)
        
        # 2. Assert the session is the one from our mock
        assert db_session is mock_session
        mock_session_local.assert_called_once()
        
        # 3. Assert the session is closed after the generator is exhausted
        with pytest.raises(StopIteration):
            next(db_generator)
        
        mock_session.close.assert_called_once()
