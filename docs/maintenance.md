# Maintenance & Operations (운영/유지보수)

## 1. DB 초기화/마이그레이션
- DB 볼륨/폴더 삭제, 마이그레이션, Alembic 등
- DB 백업/복구, 데이터 마이그레이션 절차
- 예시 명령어 및 체크리스트

## 2. 로그 파일 관리
- logs/app.log, logs/bot.log 파일 위치 및 확인 방법
- 로그 파일 회전(RotatingFileHandler) 설정, 운영 중 로그 모니터링 방법
- 로그 파일 용량 관리, 백업/보관/삭제 절차

## 3. 장애 대응/복구
- 장애 발생 시 우선 확인 항목(로그, DB, 백업본 등)
- 컨테이너 재기동, 이미지 재빌드, 운영 체크리스트
- 장애/이벤트 발생 시 PLAN.md, SystemManual.md, features_analysis.md 참고

## 4. 운영 자동화/배포
- 컨테이너 재기동, 이미지 재빌드, 운영 자동화 스크립트
- 운영/개발 환경 분리, 환경변수 관리, 보안/권한 관리 등

## 5. 기타
- 서비스별 환경변수 관리, 운영/개발 환경 분리, 보안/권한 관리 등
- 추가 문의/자동화/마이그레이션 도구 적용 필요시 담당자 문의 

# 패키지 관리 및 테스트/운영 환경 정책

## 1. 외부 패키지(lxml 등) 누락 시 문제
- 예시: `ModuleNotFoundError: No module named 'lxml'`
- 원인: requirements.txt에 패키지가 누락되어 컨테이너 빌드시 설치되지 않음
- 영향: 컨테이너 내부에서 테스트/운영 시 ImportError 발생, 기능 동작 불가

## 2. 근본적 해결책 및 정책
- 모든 외부 패키지는 반드시 requirements.txt에 명시
- requirements.txt가 변경되면 반드시 컨테이너를 재빌드/재기동
- Dockerfile에서 `pip install -r requirements.txt`로 일관 설치
- 테스트는 반드시 컨테이너 내부에서 실행 (운영 환경과 동일하게 검증)
- (예: `docker compose exec api pytest src/api/tests`)

## 3. 자동화/문서화 방안
- Makefile, README, PLAN.md, 개발 가이드에 위 정책을 명확히 반영
- CI/CD 파이프라인에서도 컨테이너 내부 테스트만 허용

## 4. 문제 발생시 조치 예시
1. requirements.txt에 누락된 패키지 추가
2. `docker compose build api`로 컨테이너 재빌드
3. `docker compose up -d api`로 재기동
4. `docker compose exec api pytest src/api/tests`로 테스트 

### 주요 트러블슈팅 사례

#### 1. API/스케줄러에서 보내는 텔레그램 알림이 도착하지 않는 문제

**증상:**
- `api_service`의 스케줄러나 특정 API 엔드포인트에서 `send_telegram_message` 함수를 호출하여 메시지를 보내는 로직이 있음.
- API 로그에는 메시지 전송이 성공했다고 기록되거나, `AttributeError: 'coroutine' object has no attribute 'message_id'` 오류가 발생함.
- 하지만 실제 사용자에게는 텔레그램 메시지가 도착하지 않음.

**원인 분석:**
- 이 문제의 근본 원인은 **동기(Sync) 코드에서 비동기(Async) 함수를 올바르게 호출하지 않았기 때문**임.
- `python-telegram-bot` v20+ 라이브러리는 `asyncio` 기반의 비동기 라이브러리임. 따라서 `bot.send_message()`와 같은 함수들은 호출 시 즉시 실행되지 않고, '코루틴(coroutine)'이라는 작업 대기표 객체를 반환함.
- FastAPI의 일반적인 동기 함수(예: `def my_sync_func(): ...`)나 APScheduler의 잡(Job)과 같은 동기적인 환경에서 비동기 함수를 `await` 없이 그냥 호출하면, 실제 작업은 실행되지 않고 코루틴 객체만 생성된 채로 남게 됨.
- 코드에서 이 코루틴 객체(작업 대기표)에 대해 `.message_id` 속성을 읽으려고 시도했기 때문에 `AttributeError`가 발생한 것임.

**해결 방안:**
- 동기 코드 블록 내에서 비동기 함수를 호출하고 그 결과가 끝날 때까지 기다려야 할 경우, 파이썬의 `asyncio` 라이브러리를 사용함.
- `asyncio.run(비동기_함수())` 형태로 코드를 감싸주면, 동기 컨텍스트에서 새로운 이벤트 루프를 생성하여 해당 비동기 작업이 완료될 때까지 실행하고 결과를 반환해 줌.

**수정 코드 예시 (`src/common/notify_service.py`):**
```python
import asyncio
# ... (기존 코드)

def send_telegram_message(chat_id: int, text: str):
    logger.info(f"Attempting to send message to chat_id: {chat_id}")
    try:
        # 비동기 함수를 동기 코드에서 실행하기 위해 asyncio.run() 사용
        message = asyncio.run(bot.send_message(chat_id=chat_id, text=text))
        if message:
            logger.info(f"Successfully sent message to chat_id: {chat_id}. Message ID: {message.message_id}")
        # ... (이후 코드)
```

**재발 방지 및 추가 확인 사항:**
- `python-telegram-bot` 라이브러리의 함수를 동기적인 환경(APScheduler, 일반 함수 등)에서 직접 호출할 때는 항상 `asyncio.run()`을 사용하여 실행해야 함.
- FastAPI 엔드포인트 자체를 `async def`로 선언하면, 내부에서 다른 비동기 함수를 호출할 때 `await` 키워드를 사용할 수 있어 코드가 더 간결해짐. 스케줄러 잡과 같이 `async def`로 만들기 어려운 환경에서는 `asyncio.run()`이 유용한 해결책임. 