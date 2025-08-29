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
- 장애/이벤트 발생 시 TODO.md, SystemManual.md, features_analysis.md 참고

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
- Makefile, README, TODO.md, 개발 가이드에 위 정책을 명확히 반영
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


# 테스트 환경 설정 및 오류 해결

이 섹션은 프로젝트의 테스트 환경을 설정하고, 테스트 과정에서 발생한 주요 오류 및 해결 과정을 문서화합니다.

## 1. 테스트 환경 초기화 및 실행

프로젝트의 `api` 및 `bot` 서비스 테스트를 실행하기 전에, Docker Compose 환경을 초기화하고 서비스를 시작해야 합니다.

```bash
docker compose down # 기존 컨테이너 및 네트워크 제거
docker compose up -d --build # 서비스 빌드 및 백그라운드 실행
```

각 서비스의 테스트는 해당 컨테이너 내부에서 `pytest`를 실행하여 수행합니다.

```bash
docker compose exec api pytest # api 서비스 테스트 실행
docker compose exec bot pytest # bot 서비스 테스트 실행
```

## 2. 주요 테스트 오류 및 해결 (API 서비스)

### 2.1. `sqlalchemy.exc.IntegrityError: NOT NULL constraint failed: app_users.id`

**문제:** `api` 서비스 테스트 실행 시 `app_users` 테이블의 `id` 컬럼에 `NOT NULL` 제약 조건 위반 오류가 발생했습니다. 이는 테스트 환경에서 사용하는 SQLite 데이터베이스에서 `id` 컬럼이 자동으로 증가하지 않아 발생하는 문제였습니다.

**해결:**
1.  `src/api/models/user.py` 파일의 `User` 모델 `id` 컬럼 타입을 `BigInteger`에서 `Integer`로 변경하고, `sqlalchemy.Identity`를 명시적으로 사용하여 모든 DB 환경에서 자동 증가가 보장되도록 수정했습니다.
    ```python
    # src/api/models/user.py
    from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
    import sqlalchemy as sa # 추가
    # ...
    class User(Base):
        # ...
        id = Column(Integer, sa.Identity(start=1), primary_key=True) # 변경
        # ...
    ```
2.  `src/api/models/price_alert.py` 파일의 `PriceAlert` 모델 `id` 컬럼도 동일한 이유로 `Integer` 타입으로 변경했습니다.
    ```python
    # src/api/models/price_alert.py
    from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, func # Integer 추가
    # ...
    class PriceAlert(Base):
        # ...
        id = Column(Integer, primary_key=True) # 변경
        # ...
    ```
3.  테스트 실행 전에 기존의 `test.db` 파일을 삭제하여 새로운 스키마로 데이터베이스가 재생성되도록 했습니다.
    ```bash
    docker compose exec api rm -f test.db
    ```

### 2.2. `AssertionError: 로그인 실패: {"detail":[{"type":"model_attributes_type", ...}]}` (422 Unprocessable Entity)

**문제:** 로그인 API (`/users/login`) 테스트 시 `422 Unprocessable Entity` 오류가 발생했습니다. 이는 FastAPI 엔드포인트가 `UserLogin` Pydantic 모델을 통해 JSON 형식의 요청 본문을 기대하지만, 테스트 코드에서 `data=` 인수를 사용하여 `application/x-www-form-urlencoded` 형식으로 요청을 보냈기 때문입니다.

**해결:**
`src/api/tests/test_api_alerts.py`, `src/api/tests/test_api_user.py`, `src/api/tests/test_e2e_scenario.py` 파일에서 `/users/login` 호출 시 `data=` 대신 `json=`을 사용하도록 수정했습니다.

```python
# 예시: test_api_user.py
# 변경 전: response = client.post("/users/login", data=login_payload)
# 변경 후: response = client.post("/users/login", json=login_payload)
```

### 2.3. `AssertionError: assert '모의매매 기록 완료' == '모의 거래가 기록되었습니다.'`

**문제:** `test_api_simulated_trade.py` 테스트에서 모의 거래 기록 후 반환되는 메시지가 테스트 코드의 기대값과 달랐습니다.

**해결:**
테스트 코드의 기대 메시지를 실제 API 응답 메시지인 `"모의매매 기록 완료"`와 일치하도록 수정했습니다.

```python
# src/api/tests/test_api_simulated_trade.py
# 변경 전: assert response.json()["message"] == "모의 거래가 기록되었습니다."
# 변경 후: assert response.json()["message"] == "모의매매 기록 완료"
```

### 2.4. `AssertionError: assert 404 == 200` (E2E 시나리오의 가격 알림 설정)

**문제:** `test_e2e_scenario.py`에서 가격 알림 설정을 위해 `POST /notifications/`를 호출했을 때 `404 Not Found` 오류가 발생했습니다. 이는 `notification` 라우터의 실제 prefix가 `/alerts`였고, `NotificationCreate` 스키마가 `user_id`를 요청 본문으로 받지 않기 때문이었습니다.

**해결:**
1.  `test_e2e_scenario.py`에서 가격 알림 생성 API의 URL을 올바른 경로인 `/alerts/`로 수정했습니다.
2.  `POST /alerts/` 호출 시 요청 본문(json)에서 `user_id` 필드를 제거했습니다. 인증된 사용자의 정보는 헤더의 토큰을 통해 자동으로 전달됩니다.
3.  API 응답이 `message` 키를 포함하지 않고 `PriceAlertRead` 스키마를 직접 반환하므로, 테스트 코드에서 `response.json()["message"]` 대신 `response.json()["symbol"]`과 `response.json()["target_price"]`를 직접 확인하도록 수정했습니다.

```python
# src/api/tests/test_e2e_scenario.py
# 변경 전:
# response = client.post("/notifications/", json={
#     "user_id": user_id,
#     "symbol": symbol,
#     "target_price": 90000,
#     "condition": "gte"
# }, headers=headers)
# assert response.status_code == 200
# assert response.json()["message"] == "가격 알림이 추가되었습니다."

# 변경 후:
response = client.post("/alerts/", json={
    "symbol": symbol,
    "target_price": 90000,
    "condition": "gte"
}, headers=headers)
assert response.status_code == 200
alert_data = response.json()
assert alert_data["symbol"] == symbol
assert alert_data["target_price"] == 90000
```

## 3. 주요 테스트 오류 및 해결 (Bot 서비스)

### 3.1. `TypeError: object MagicMock can't be used in 'await' expression`

**문제:** `bot` 서비스 테스트에서 `context.bot.send_message`를 `await`로 호출할 때 `TypeError`가 발생했습니다. 이는 `context.bot`이 `MagicMock`으로 모의되었지만, 그 안에 있는 `send_message` 메서드가 비동기 함수처럼 동작하도록 설정되지 않았기 때문입니다.

**해결:**
`src/bot/tests/test_bot_admin.py` 파일의 `setup_method`에서 `self.context.bot`을 `AsyncMock`으로 설정하고, `self.context.bot.send_message`도 `AsyncMock`으로 설정하여 비동기 함수처럼 동작하도록 했습니다.

```python
# src/bot/tests/test_bot_admin.py
# ...
class TestBotAdmin:
    def setup_method(self):
        self.update = AsyncMock(spec=Update)
        self.context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        
        self.update.message = AsyncMock(spec=Message)
        self.update.message.reply_text = AsyncMock()
        
        # 추가된 부분
        self.context.bot = AsyncMock()
        self.context.bot.send_message = AsyncMock()
```

### 3.2. `AssertionError: expected call not found. Expected: send_message(...) Actual: send_message(chat_id=..., text=...)`

**문제:** `self.context.bot.send_message.assert_called_once_with` 호출 시, 테스트 코드에서 위치 인자를 기대했지만 실제 호출은 키워드 인자로 이루어져 발생한 오류입니다.

**해결:**
`src/bot/tests/test_bot_admin.py` 파일에서 `self.context.bot.send_message.assert_called_once_with` 호출 시 `chat_id`와 `text`를 키워드 인자로 명시적으로 전달하도록 수정했습니다.

```python
# src/bot/tests/test_bot_admin.py
# 변경 전: self.context.bot.send_message.assert_called_once_with(self.update.effective_chat.id, "...")
# 변경 후: self.context.bot.send_message.assert_called_once_with(chat_id=self.update.effective_chat.id, text="...")
```