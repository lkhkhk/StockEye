import asyncio
import logging
import signal
from typing import Set, Dict
from prometheus_client import start_http_server
from pythonjsonlogger import jsonlogger
from .core.config import settings
from .core.database import db
from .services.telegram import telegram_bot
from .services.disclosure import check_disclosures
from .core.logger import setup_logging
from .core.scheduler import setup_scheduler, start_scheduler, stop_scheduler
from .services.dart_updater import update_corp_codes_from_dart

# JSON 로깅 설정
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s')
logHandler.setFormatter(formatter)
logger = setup_logging()
logger.addHandler(logHandler)
logger.setLevel(settings.LOG_LEVEL)

# 종료 이벤트를 위한 asyncio Event 객체
shutdown_event = asyncio.Event()

async def periodic_disclosure_check_task():
    """주기적으로 공시 확인을 실행하는 태스크 (기존 check_and_notify 역할)"""
    while not shutdown_event.is_set():
        try:
            await check_disclosures() # disclosure.py의 함수 호출
        except asyncio.CancelledError:
            logger.info("periodic_disclosure_check_task 태스크 취소됨.")
            break
        except Exception as e:
            logger.error(f"periodic_disclosure_check_task 태스크 오류: {e}", exc_info=True)

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=settings.UPDATE_INTERVAL * 60)
            if shutdown_event.is_set():
                logger.info("periodic_disclosure_check_task 에서 종료 이벤트 감지, 루프 종료.")
                break
        except asyncio.TimeoutError:
            pass
        except asyncio.CancelledError:
            logger.info("periodic_disclosure_check_task 대기 중 취소됨.")
            break

async def main():
    """애플리케이션 메인 실행 함수"""
    # 데이터베이스 연결
    await db.connect()
    logger.info("데이터베이스 연결 성공")

    try:
        logger.info("시작 시 DART 고유번호 정보 갱신 시도...")
        inserted_count, updated_count = await update_corp_codes_from_dart()
        logger.info(f"시작 시 DART 고유번호 정보 갱신 완료. 삽입: {inserted_count}, 갱신: {updated_count}")
    except Exception as e:
        logger.error(f"시작 시 DART 고유번호 정보 갱신 중 오류: {e}", exc_info=True)

    # 스케줄러 설정 및 시작
    setup_scheduler()
    start_scheduler()
    logger.info("스케줄러 시작됨.")

    # 텔레그램 봇 시작
    await telegram_bot.start()

    # 주기적 공시 확인 태스크 시작
    disclosure_task = asyncio.create_task(periodic_disclosure_check_task())

    # Prometheus 메트릭 서버 시작 (포트 8000)
    start_http_server(8000)
    logger.info("Prometheus 메트릭 서버 시작 (포트 8000)")

    # 종료 시그널 처리 설정
    loop = asyncio.get_running_loop()
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, loop, [disclosure_task]))
        )

    logger.info("애플리케이션 실행 준비 완료. 종료하려면 Ctrl+C를 누르세요.")

    # 애플리케이션이 종료될 때까지 대기 (예: shutdown_event 사용 또는 다른 대기 메커니즘)
    await shutdown_event.wait() # shutdown_event를 사용하여 종료 대기

async def shutdown(signal, loop, tasks):
    """Graceful shutdown 처리"""
    logger.info(f"종료 시그널 수신: {signal}. 애플리케이션 종료 시작...")
    shutdown_event.set() # 종료 이벤트 설정

    # 진행 중인 태스크 취소
    for task in tasks:
        task.cancel()

    # 스케줄러 종료
    await stop_scheduler()

    # 텔레그램 봇 종료
    await telegram_bot.stop()

    # 데이터베이스 연결 종료
    await db.disconnect()

    # 이벤트 루프 중지
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]

    logger.info(f"태스크 {len(tasks)}개 취소. 종료 대기 중...")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
    logger.info("애플리케이션 종료 완료.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("애플리케이션 강제 종료됨.") 