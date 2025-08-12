# StockEye 개발 계획 및 현황

## 🚨 최우선 과제: 아키텍처 재설계 및 안정화

> **현황:** E2E 테스트 과정에서 `api`와 `bot` 서비스 간의 순환 의존성으로 인한 심각한 네트워크 오류 및 기능 미작동 문제가 발견되었습니다. 이를 해결하기 위해 Message Queue(Redis)를 도입하고, 비동기 작업을 처리하는 별도의 `worker` 서비스를 추가하는 것으로 아키텍처를 재설계하기로 결정했습니다.

> **목표:** 새로운 아키텍처를 성공적으로 도입하여 서비스 간 결합도를 낮추고, 시스템 전체의 안정성과 확장성을 확보합니다. 이 과정에서 기존의 핵심 기능 미작동 버그들을 모두 해결하고, 안정적인 E2E 테스트를 구축합니다.

---

### Phase 1: 아키텍처 재설계 및 인프라 구축

-   [x] **[인프라] `docker-compose.yml` 수정:**
    -   [x] `redis` 서비스를 신규 추가했습니다.
    -   [x] `worker` 서비스를 신규 추가하고 `Dockerfile`을 작성했습니다.
    -   [x] 모든 서비스(`api`, `bot`, `db`, `redis`, `worker`)의 이름과 `container_name`에 `stockeye-` 접두사를 붙여 명명 규칙을 통일했습니다.
    -   [x] 서비스 간 통신에 사용되는 호스트 이름을 새로운 서비스명으로 업데이트했습니다.
-   [x] **[리팩토링] 서비스명 변경에 따른 프로젝트 전체 수정:**
    -   [x] `docker-compose.yml`의 서비스명 변경사항을 `bot` 핸들러, 테스트 코드, 쉘 스크립트 등 프로젝트 내의 모든 관련 파일에 일괄 적용했습니다.
-   [x] **[신규] `worker` 서비스 기본 구현:**
    -   [x] `src/worker/main.py`를 생성하고, Redis Pub/Sub 구독 및 기본 로깅 로직을 구현했습니다.
    -   [x] `docker compose up --build`를 통해 모든 서비스가 정상적으로 기동됨을 확인했습니다。

### Phase 2: Worker 서비스 기능 이전 및 테스트

-   [x] **[완료] 스케줄러 기능 이전 및 테스트:**
    -   **목표:** `api` 서비스의 APScheduler 관련 코드를 `worker` 서비스로 이전하고, 단위 테스트를 작성하여 안정성을 검증합니다.
    -   **작업 단계:**
        1.  `api/main.py`의 스케줄러 관련 코드를 `worker/main.py`로 이전합니다.
        2.  `worker`가 DB 및 서비스(StockService, PriceAlertService)에 접근할 수 있도록 의존성을 설정합니다.
        3.  `api/main.py`에서 스케줄러 관련 코드를 완전히 제거합니다.
        4.  `src/worker/tests/unit/test_scheduler.py`를 작성하여 각 스케줄링 잡(`update_stock_master_job` 등)에 대한 단위 테스트를 구현합니다. (서비스 로직 Mocking)
        5.  모든 서비스 재기동 후, `worker` 로그를 통해 스케줄러가 정상적으로 잡을 등록하고 실행하는지 확인합니다.

-   [x] **[완료] 알림 기능 리팩토링 및 테스트:**
    -   **목표:** 기존의 동기적 알림 로직을 Redis Pub/Sub 기반의 비동기 방식으로 변경하고, 이에 대한 테스트를 작성합니다.
    -   **작업 단계:**
        1.  **`api` 서비스:** `price_alert_service.py` 등에서 `bot`을 직접 호출하던 로직을 제거하고, `chat_id`와 메시지 내용을 Redis의 `notifications` 채널에 발행(Publish)하도록 수정합니다. (확인 결과, 이 로직은 `worker` 서비스에 이미 구현되어 있었음)
        2.  **`worker` 서비스:** `notification_listener`가 수신한 메시지를 바탕으로 `telegram-bot` 라이브러리를 사용하여 실제 텔레그램 메시지를 발송하도록 구현합니다.
        3.  [x] **`src/worker/tests/unit/test_listener.py`를 작성하여 `notification_listener`에 대한 단위 테스트를 구현합니다.** (Redis 메시지 수신 및 `send_telegram_message` 호출 검증)
        4.  **`src/api/tests/integration/test_notification_publish.py`를 작성하여 `api`가 Redis에 메시지를 올바르게 발행하는지 통합 테스트를 구현합니다.**
            -   **현황:** 수많은 테스트 환경 문제(DB 손상, Fixture 설계 오류, 라우터 설정 오류 등)를 해결하고, 최종적으로 `async/await` 누락 버그를 수정하여 **알림 생성 기능에 대한 통합 테스트(`test_create_price_alert_successfully`)가 통과됨을 확인**했습니다.
            -   **다음 단계:** 알림 '생성'이 아닌, `worker`의 스케줄러에 의해 알림 조건이 맞는다고 판단되었을 때 Redis에 메시지를 **'발행'**하는 로직(`price_alert_service.check_price_alerts`)에 대한 별도의 통합 테스트를 작성해야 합니다.
        5.  [x] **`price_alert_service.check_price_alerts`에 대한 통합 테스트를 작성합니다.**
            -   **테스트 케이스 설계:**
                -   **Given (준비):**
                    -   테스트용 사용자, 주식(예: 삼성전자), 가격 정보(예: 75,000원)를 DB에 생성합니다.
                    -   해당 사용자와 주식에 대한 알림(예: 80,000원 이상일 때 알림)을 생성합니다.
                    -   Redis 클라이언트를 준비하고 `notifications` 채널을 구독합니다.
                -   **When (실행):**
                    -   알림 조건을 충족시키는 새로운 가격 정보(예: 81,000원)를 DB에 추가합니다.
                    -   `PriceAlertService`의 `check_price_alerts` 메서드를 직접 호출합니다.
                -   **Then (검증):**
                    -   Redis `notifications` 채널에 메시지가 발행되었는지 확인합니다.
                    -   발행된 메시지의 `chat_id`와 내용이 예상과 일치하는지 검증합니다.
                    -   알림이 정상적으로 처리된 후, DB에서 해당 알림의 상태(`is_active` 등)가 올바르게 변경되었는지 확인합니다.
            -   **구현 위치:** `src/api/tests/unit/test_price_alert_service.py`

### Phase 3: 핵심 기능 정상화 및 E2E 테스트 구축

> **목표:** 새로운 아키텍처 위에서 기존의 모든 버그를 해결하고, 각 기능에 대한 E2E 테스트를 작성하여 안정성을 검증합니다.

-   [x] **[완료] 사용자 데이터 연동 기능 정상화:**
    -   **대상:** `alert`, `history`, `trade`, `watchlist` 등
    -   **해결 방안:** `telegram_id` 기반의 사용자 식별 로직을 `api` 서비스에 중앙화하여 구현했던 내용을 새로운 아키텍처에 맞게 재검증하고 안정화합니다。
    -   **검증:** 각 기능에 대한 **Bot-API-Worker 연동 E2E 테스트 코드를 반드시 작성**하여 버그 재발을 방지합니다。

-   [x] **[완료] `natural` 핸들러 API 응답 형식 불일치 문제 해결:**
    -   **해결:** `natural.py`에서 API 응답(`{"items": [...]}`)을 올바르게 파싱하도록 수정합니다。
    -   **검증:** E2E 테스트를 통해 자연어 처리 기능의 정상 동작을 확인합니다。

-   [x] **[완료] 예측 이력 저장을 위한 `user_id` 전달:**
    -   **현황:** `predict`, `natural` 핸들러에서 `/predict` API 호출 시 `telegram_id`를 포함하고, `api`는 이를 `user_id`로 변환하여 이력을 저장하도록 하는 기능 구현 중.
    -   **발생 문제:**
        *   **API 라우터 경로 불일치:** `bot`에서 `/predict`로 호출했으나 `api` 라우터가 `/predict/`로 설정되어 `307 Temporary Redirect` 발생 및 POST 본문 유실. (`/predict`로 수정 완료)
        *   **테스트 데이터 시딩 불일치:** `api` 서비스 시작 시 `StockMaster` 테이블에 테스트 데이터가 이미 존재한다고 판단하여 시딩을 건너뛰었으나, 실제 검색 시 데이터가 조회되지 않는 문제 발생. (시딩 로직 보강 완료)
        *   **`predict_service` 로직 오류:** `predict_stock_movement` 함수가 `calculate_analysis_items`의 결과를 `None`으로 잘못 판단하여 "예측 불가"를 반환하는 문제 발생. (`predict_service` 로직 수정 완료)
        *   **E2E 테스트 실패 지속:** 위 모든 수정에도 불구하고 E2E 테스트가 동일한 오류로 계속 실패하고 있음. 이는 DB 환경, Docker 네트워크, 또는 `pytest`와 `asyncio`의 상호작용 등 더 근본적인 환경적 문제일 가능성이 높음.
    -   **해결:** `httpx.Response.ok` 속성 Deprecated 문제로 확인되어, `response.is_success` 또는 `response.status_code < 400`으로 변경하여 해결했습니다.
    -   **검증:** `src/bot/tests/e2e/test_prediction_history_e2e.py` 테스트 통과 확인.

-   [ ] **[진행중] 봇 관리자 명령어(`show_schedules`) 오류 해결:**
    -   **문제:** `show_schedules` 명령어 실행 시 `404 Not Found` 오류 발생.
    -   **원인:** 아키텍처 변경 (`api` -> `worker`로 스케줄러 이전) 후, `bot`이 `worker`와 통신하는 방법이 구현되지 않음.
    -   **해결 계획:**
        1.  `worker` 서비스에 FastAPI를 도입하여 스케줄러 제어용 API를 구현합니다.
        2.  `api` 서비스에 `worker` API를 호출하는 프록시 엔드포인트를 추가합니다.
        3.  `bot` 핸들러가 `api` 서비스의 프록시 엔드포인트를 호출하도록 수정합니다.

## 🌟 Phase 4: 테스트 고도화 및 지침 개선 (유지)

-   [ ] **(기존) 단위 테스트 커버리지 100% 달성**
    -   [x] **Bot 핸들러:** `start.py` 단위 테스트 신규 작성 완료.
    -   [x] **Bot 핸들러:** `history.py` 등 누락된 단위 테스트를 작성합니다.
    -   [ ] **API 라우터:** `admin.py` 등 단위 테스트가 없는 모든 라우터에 대해 신규 작성합니다.
    -   [ ] **API 서비스:** `stock_service.py` 등 기존 테스트를 보강하고 순수 단위 테스트로 리팩토링합니다.
    -   [ ] **`common` 모듈:** 모든 공통 모듈에 대한 단위 테스트를 작성합니다.
-   [ ] **(기존) 통합 테스트 보강**
    -   [ ] `predict.py` 등 통합 테스트가 없는 API 라우터에 대해 신규 작성합니다.

## ⚙️ Phase 5: 환경 변수 및 DB 설정 안정화

-   [x] **`TELEGRAM_BOT_TOKEN` 환경 변수 문제 해결:**
    -   `worker` 서비스 로그에 `The "TELEGRAM_BOT_TOKEN" variable is not set.` 경고가 발생하는 문제 해결.
    -   `docker-compose.yml` 및 관련 파일 검토하여 `TELEGRAM_BOT_TOKEN`이 모든 서비스에 올바르게 전달되는지 확인.
-   [x] **`.env` 파일 및 환경 변수 설정 전반 검토:**
    -   `docker-compose.yml`, `Dockerfile`들, `settings.env.example` 등을 검토하여 환경 변수 설정의 일관성 확보.
    -   `db` 서비스 때문에 필요하다고 알려진 `.env` 파일의 필요성을 재검토하고, 가능하다면 의존성 제거 방안 모색.

## ⚙️ Phase 6: 전역 HTTP 클라이언트(session) 제거 리팩토링

> **목표:** 프로젝트 전반에 걸쳐 사용되는 `src/common/http_client.py`의 전역 `session` 객체를 제거하여, 모듈 로딩 시점의 의존성을 없애고 테스트 용이성을 향상시킵니다. 모든 HTTP 요청은 `get_retry_client()` 팩토리 함수를 통해 생성된 클라이언트 인스턴스를 사용하도록 변경합니다.

-   [x] **`src/bot/handlers/predict.py`**
-   [x] **`src/bot/handlers/register.py`**
-   [x] `src/common/dart_utils.py`
-   [x] `src/bot/handlers/history.py`
-   [x] `src/bot/handlers/alert.py`
-   [x] `src/bot/handlers/symbols.py`
-   [x] `src/bot/handlers/trade.py`
-   [x] `src/bot/handlers/watchlist.py`
-   [x] `src/bot/handlers/admin.py`
-   [x] 관련 테스트 파일 모두 수정 (`test_dart_utils.py`, `test_bot_admin.py` 등)

## ✨ Phase 7: 향후 개선 과제

-   [ ] **[신규] 알림 시스템 고도화:**
    -   **목표:** 현재 텔레그램에 종속된 알림 시스템을 다중 채널(이메일, SMS, 디스코드 등)을 지원하는 유연한 구조로 리팩토링합니다.
    -   **구현 방향:**
        1.  API가 Redis에 발행하는 메시지를 `{"user_id": ..., "message": ...}`와 같이 일반화합니다.
        2.  Worker는 이 메시지를 받아, DB에서 사용자의 알림 설정을 조회한 후, 설정된 모든 채널로 알림을 발송하는 "알림 라우터" 역할을 수행하도록 변경합니다.
        3.  사용자가 자신의 알림 채널을 설정할 수 있는 API를 구현합니다.
    -   **관련 문서:** `docs/archive/notification_system_architecture.md`

---

## 🐞 이전에 해결된 주요 문제점

-   [x] **[API] 통합 테스트 404 오류 해결:** `src/api/main.py`의 라우터 `prefix` 설정과 `TestClient` 호출 경로의 일관성 확인 및 수정.
-   [x] **[Bot/API] 단위 테스트 Mocking/Import 오류 해결:**
    -   [x] `src/bot/tests/unit/test_alert_handler.py`, `test_bot_natural.py`, `test_bot_predict.py`, `test_bot_register.py` 등에서 Mocking 관련 오류 (`TypeError: object AsyncMock can't be used in 'await' expression` 등)가 발생합니다.
    -   [x] `src/bot/tests/unit/test_bot_natural.py`에서 `ModuleNotFoundError: No module named 'src.bot.handlers.natural.session'` 오류가 발생합니다.
    -   [x] `src/api/tests/unit/test_auth_service.py`에서 `ModuleNotFoundError: No module named 'src.api.services.auth_service.pwd_context'` 오류가 발생합니다.
-   [x] **[API] 서비스 로직 오류 해결:** `src/api/tests/unit/test_predict_service.py`, `test_price_alert_service.py`, `test_stock_service.py` 등에서 `KeyError` 또는 `TypeError`와 같은 로직 오류가 발생합니다.
-   [x] **[Worker] 단위 테스트 오류 해결:**
    -   [x] `src/worker/tests/unit/test_listener.py`에서 `TypeError: object AsyncMock can't be used in 'await' expression` 오류가 발생합니다.
    -   [x] `src/worker/tests/unit/test_main_jobs.py`에서 `ModuleNotFoundError: No module named 'src.api.main'` 오류가 발생합니다.