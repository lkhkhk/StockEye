import pytest
from unittest.mock import patch, ANY, MagicMock
from src.worker import main
from src.worker import tasks
from datetime import datetime

@pytest.mark.asyncio
@patch('src.worker.main.multiprocessing.Process')
async def test_update_stock_master_job_triggers_process(mock_process):
    await main.update_stock_master_job(chat_id=123)
    mock_process.assert_called_once_with(target=tasks.update_stock_master_task, args=(123,))

@pytest.mark.asyncio
@patch('src.worker.main.multiprocessing.Process')
async def test_update_daily_price_job_triggers_process(mock_process):
    await main.update_daily_price_job(chat_id=456)
    mock_process.assert_called_once_with(target=tasks.update_daily_price_task, args=(456,))

@pytest.mark.asyncio
@patch('src.worker.main.multiprocessing.Process')
async def test_check_disclosures_job_triggers_process(mock_process):
    await main.check_disclosures_job(chat_id=789)
    mock_process.assert_called_once_with(target=tasks.check_disclosures_task, args=(789,))

@pytest.mark.asyncio
@patch('src.worker.main.multiprocessing.Process')
async def test_check_price_alerts_job_triggers_process(mock_process):
    await main.check_price_alerts_job(chat_id=101)
    mock_process.assert_called_once_with(target=tasks.check_price_alerts_task, args=(101,))

@pytest.mark.asyncio
@patch('src.worker.main.multiprocessing.Process')
async def test_run_historical_price_update_task_triggers_process(mock_process):
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 1, 31)
    await main.run_historical_price_update_task(chat_id=112, start_date=start_date, end_date=end_date)
    mock_process.assert_called_once_with(
        target=tasks.run_historical_price_update_task, 
        args=(112, '2023-01-01', '2023-01-31', None)
    )


# --- Phase 3: Remaining Job Trigger Tests ---

@pytest.mark.asyncio
@patch('src.worker.main.multiprocessing.Process')
@patch('src.worker.main.tasks.update_stock_master_task')
async def test_update_stock_master_job_triggers_process(mock_task, mock_process):
    """update_stock_master_job이 별도 프로세스를 트리거하는지 테스트"""
    # GIVEN
    mock_process_instance = MagicMock()
    mock_process.return_value = mock_process_instance
    chat_id = 12345
    
    # WHEN
    await main.update_stock_master_job(chat_id)
    
    # THEN
    mock_process.assert_called_once_with(target=mock_task, args=(chat_id,))
    mock_process_instance.start.assert_called_once()


@pytest.mark.asyncio
@patch('src.worker.main.multiprocessing.Process')
@patch('src.worker.main.tasks.update_daily_price_task')
async def test_update_daily_price_job_triggers_process(mock_task, mock_process):
    """update_daily_price_job이 별도 프로세스를 트리거하는지 테스트"""
    # GIVEN
    mock_process_instance = MagicMock()
    mock_process.return_value = mock_process_instance
    chat_id = 67890
    
    # WHEN
    await main.update_daily_price_job(chat_id)
    
    # THEN
    mock_process.assert_called_once_with(target=mock_task, args=(chat_id,))
    mock_process_instance.start.assert_called_once()


@pytest.mark.asyncio
@patch('src.worker.main.multiprocessing.Process')
@patch('src.worker.main.tasks.check_disclosures_task')
async def test_check_disclosures_job_triggers_process(mock_task, mock_process):
    """check_disclosures_job이 별도 프로세스를 트리거하는지 테스트"""
    # GIVEN
    mock_process_instance = MagicMock()
    mock_process.return_value = mock_process_instance
    
    # WHEN - chat_id 없이 호출 (scheduled job)
    await main.check_disclosures_job()
    
    # THEN
    mock_process.assert_called_once_with(target=mock_task, args=(None,))
    mock_process_instance.start.assert_called_once()
