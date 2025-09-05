import pytest
from unittest.mock import patch, ANY
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
        args=(112, '2023-01-01', '2023-01-31')
    )
