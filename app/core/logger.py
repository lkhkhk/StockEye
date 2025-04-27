import logging
import sys
from pythonjsonlogger import jsonlogger
from .config import settings

def setup_logging():
    """
    로깅 설정
    """
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    
    # JSON 포맷터 설정
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러
    file_handler = logging.FileHandler('stockeye.log')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 서드파티 라이브러리 로깅 레벨 조정
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    return root_logger 