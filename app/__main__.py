import asyncio
import logging
import signal
from typing import Set, Dict
from prometheus_client import start_http_server
from pythonjsonlogger import jsonlogger
from .core.config import settings
from .core.database import db
from .services.telegram import telegram_bot
from .services.disclosure import disclosure_service
from .core.logger import setup_logging

# JSON 로깅 설정
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s')
logHandler.setFormatter(formatter)
logger = setup_logging()
logger.addHandler(logHandler)
logger.setLevel(settings.LOG_LEVEL)

# 종료 이벤트를 위한 asyncio Event 객체
shutdown_event = asyncio.Event()

async def check_and_notify():
    """주기적으로 공시를 확인하고 알림을 발송하는 태스크"""
    while not shutdown_event.is_set(): # 종료 이벤트 체크 추가
        try:
            logger.info("공시 확인 및 알림 발송 시작...")
            async with db.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT DISTINCT s.code, s.name, us.user_id
                    FROM stocks s
                    JOIN user_stocks us ON s.code = us.stock_code
                """)

                stocks_to_check: Dict[str, Dict] = {}
                for row in rows:
                    code = row['code']
                    if code not in stocks_to_check:
                        stocks_to_check[code] = {'name': row['name'], 'users': set()}
                    stocks_to_check[code]['users'].add(row['user_id'])

                fetch_tasks = []
                for code, info in stocks_to_check.items():
                    fetch_tasks.append(disclosure_service.fetch_disclosures(code))
                
                all_disclosures = await asyncio.gather(*fetch_tasks)
                
                process_tasks = []
                i = 0
                for code, info in stocks_to_check.items():
                    process_tasks.append(
                        disclosure_service.process_new_disclosures(
                            code, info['name'], all_disclosures[i], info['users']
                        )
                    )
                    i += 1
                await asyncio.gather(*process_tasks)

            # Redis에서 알림 읽어와서 발송
            # 수정: keys() -> scan_iter() 사용 및 async list comprehension 적용
            keys = [key async for key in db.redis.scan_iter("notification:*:*")]
            if keys:
                logger.info(f"{len(keys)}개의 알림 발송 예정...")
                send_tasks = []
                keys_to_delete = []
                for key in keys:
                    # key는 이미 문자열 (decode_responses=True)
                    _, user_id, stock_code = key.split(':')
                    message = await db.redis.get(key)
                    if message:
                        send_tasks.append(
                            telegram_bot.app.bot.send_message(
                                chat_id=user_id,
                                text=message, # message는 이미 문자열
                                parse_mode='HTML',
                                disable_web_page_preview=True
                            )
                        )
                        keys_to_delete.append(key)
                    else:
                        # 메시지가 없는 키도 삭제 리스트에 추가
                        keys_to_delete.append(key)
                
                # 알림 병렬 발송
                results = await asyncio.gather(*send_tasks, return_exceptions=True)
                
                # 성공/실패 로깅 및 키 삭제
                delete_tasks = []
                for i, result in enumerate(results):
                    key = keys_to_delete[i]
                    _, user_id, stock_code = key.split(':')
                    if isinstance(result, Exception):
                        logger.error(f"알림 발송 중 오류 (사용자 {user_id}, 키 {key}): {result}")
                    else:
                        logger.info(f"사용자 {user_id}에게 {stock_code} 알림 발송 완료")
                    delete_tasks.append(db.redis.delete(key))
                
                # 메시지 없는 키 삭제 추가
                for key in keys:
                    if key not in keys_to_delete:
                         delete_tasks.append(db.redis.delete(key))
                
                if delete_tasks:
                    await asyncio.gather(*delete_tasks)

            logger.info("공시 확인 및 알림 발송 완료.")

        except asyncio.CancelledError: # 태스크 취소 시 루프 종료
            logger.info("check_and_notify 태스크 취소됨.")
            break
        except Exception as e:
            logger.error(f"check_and_notify 태스크 오류: {e}", exc_info=True)

        try:
            # 다음 확인까지 대기 (종료 이벤트 감지)
            await asyncio.wait_for(shutdown_event.wait(), timeout=settings.UPDATE_INTERVAL * 60)
            # 종료 이벤트가 설정되면 루프 탈출
            if shutdown_event.is_set():
                logger.info("check_and_notify 에서 종료 이벤트 감지, 루프 종료.")
                break
        except asyncio.TimeoutError:
            # 타임아웃 발생 시 다음 루프 진행
            pass
        except asyncio.CancelledError:
             logger.info("check_and_notify 대기 중 취소됨.")
             break

async def shutdown(sig: signal.Signals = None):
    """
    서비스 종료 처리
    """
    if sig:
        logger.info(f"Received exit signal {sig.name}...")
    else:
        logger.info("Shutdown initiated...")
        
    # 종료 이벤트 설정 (다른 태스크들이 인지하도록)
    if not shutdown_event.is_set():
        shutdown_event.set()

    # 현재 실행 중인 모든 태스크 가져오기 (자신 제외)
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    # 각 태스크 취소 요청
    for task in tasks:
        task.cancel()

    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    # 취소 완료 기다리기
    await asyncio.gather(*tasks, return_exceptions=True)

    # 텔레그램 봇 종료
    logger.info("텔레그램 봇 종료 중...")
    await telegram_bot.stop()

    # 데이터베이스 연결 종료
    logger.info("데이터베이스 및 Redis 연결 종료 중...")
    await db.disconnect()

    logger.info("서비스가 정상적으로 종료되었습니다.")

def signal_handler(sig, frame):
    """
    간단한 시그널 핸들러 - 종료 이벤트 설정
    """
    logger.info(f"Signal {sig} received, initiating shutdown...")
    # 메인 스레드에서 직접 shutdown_event 설정
    # 비동기 함수를 직접 호출하는 대신 이벤트를 사용
    shutdown_event.set()

async def main():
    """
    메인 함수
    """
    # Windows에서는 SIGTERM이 일반적이지 않으므로 SIGINT만 처리
    signal.signal(signal.SIGINT, signal_handler)
    # signal.signal(signal.SIGTERM, signal_handler) # 필요시 주석 해제 (Windows에서는 제한적)

    monitoring_task = None
    try:
        # Prometheus 메트릭스 서버 시작
        start_http_server(8000)
        logger.info("Prometheus metrics server started on port 8000")

        # 데이터베이스 연결
        await db.connect()

        # 텔레그램 봇 시작
        await telegram_bot.start()

        # 공시 확인 및 알림 태스크 시작
        monitoring_task = asyncio.create_task(check_and_notify())
        logger.info("공시 모니터링 태스크 시작됨")

        # 종료 이벤트 대기
        await shutdown_event.wait()
        logger.info("Shutdown event received in main, proceeding to cleanup.")

    except asyncio.CancelledError:
        logger.info("Main task cancelled.")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        logger.info("Entering main finally block for cleanup...")
        # monitoring_task가 생성되었고 아직 실행 중이면 취소 시도
        if monitoring_task and not monitoring_task.done():
             logger.info("Cancelling monitoring task from finally block...")
             monitoring_task.cancel()
             try:
                 await monitoring_task # 취소 완료 대기
             except asyncio.CancelledError:
                 logger.info("Monitoring task cancellation confirmed in finally.")
        
        # 추가 정리 (이미 shutdown 함수에서 호출됨)
        # await telegram_bot.stop()
        # await db.disconnect()
        logger.info("Main finally block finished.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # KeyboardInterrupt는 signal_handler가 처리하므로 여기서는 pass
        logger.info("KeyboardInterrupt caught in __main__, shutdown initiated.")
    except Exception as e:
        logger.error(f"Fatal error during startup or shutdown: {e}", exc_info=True)
    finally:
        logger.info("Application finished.") 