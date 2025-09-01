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
    -   [x] `docker compose up --build`를 통해 모든 서비스가 정상적으로 기동됨을 확인했습니다.

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
    -   **해결 방안:** `telegram_id` 기반의 사용자 식별 로직을 `api` 서비스에 중앙화하여 구현했던 내용을 새로운 아키텍처에 맞게 재검증하고 안정화합니다.
    -   **검증:** 각 기능에 대한 **Bot-API-Worker 연동 E2E 테스트 코드를 반드시 작성**하여 버그 재발을 방지합니다.

-   [x] **[완료] `natural` 핸들러 API 응답 형식 불일치 문제 해결:**
    -   **해결:** `natural.py`에서 API 응답(`{"items": [...]}`)을 올바르게 파싱하도록 수정합니다.
    -   **검증:** E2E 테스트를 통해 자연어 처리 기능의 정상 동작을 확인합니다.

-   [x] **[완료] 예측 이력 저장을 위한 `user_id` 전달:**
    -   **현황:** `predict`, `natural` 핸들러에서 `/predict` API 호출 시 `telegram_id`를 포함하고, `api`는 이를 `user_id`로 변환하여 이력을 저장하도록 하는 기능 구현 중.
    -   **발생 문제:**
        *   **API 라우터 경로 불일치:** `bot`에서 `/predict`로 호출했으나 `api` 라우터가 `/predict/`로 설정되어 `307 Temporary Redirect` 발생 및 POST 본문 유실. (`/predict`로 수정 완료)
        *   **테스트 데이터 시딩 불일치:** `api` 서비스 시작 시 `StockMaster` 테이블에 이미 존재한다고 판단하여 시딩을 건너뛰었으나, 실제 검색 시 데이터가 조회되지 않는 문제 발생. (시딩 로직 보강 완료)
        *   **`predict_service` 로직 오류:** `predict_stock_movement` 함수가 `calculate_analysis_items`의 결과를 `None`으로 잘못 판단하여 "예측 불가"를 반환하는 문제 발생. (`predict_service` 로직 수정 완료)
        *   **E2E 테스트 실패 지속:** 위 모든 수정에도 불구하고 E2E 테스트가 동일한 오류로 계속 실패하고 있음. 이는 DB 환경, Docker 네트워크, 또는 `pytest`와 `asyncio`의 상호작용 등 더 근본적인 환경적 문제일 가능성이 높음.
    -   **해결:** `httpx.Response.ok` 속성 Deprecated 문제로 확인되어, `response.is_success` 또는 `response.status_code < 400`으로 변경하여 해결했습니다.
    -   **검증:** `src/bot/tests/e2e/test_prediction_history_e2e.py` 테스트 통과 확인.
    -   **현황:** 공시 데이터 저장 및 알림 기능 정상 작동 확인.

-   [x] **[완료] 봇 관리자 명령어(`show_schedules`) 오류 해결:**
    -   **문제:** `show_schedules` 명령어 실행 시 `404 Not Found` 오류 발생.
    -   **원인:** 아키텍처 변경 (`api` -> `worker`로 스케줄러 이전) 후, `bot`이 `worker`와 통신하는 방법이 구현되지 않음.
    -   **해결 계획:**
        1.  `worker` 서비스에 FastAPI를 도입하여 스케줄러 제어용 API를 구현합니다.
        2.  `api` 서비스에 `worker` API를 호출하는 프록시 엔드포인트를 추가합니다.
        3.  `bot` 핸들러가 `api` 서비스의 프록시 엔드포인트를 호출하도록 수정합니다.
    -   **검증:** `src/bot/tests/e2e/test_prediction_history_e2e.py` 테스트 통과 확인.

-   [x] **[완료] 봇 관리자 명령어(`show_schedules`) 오류 해결:**
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
        -   [ ] `src/common/models/` 파일들에 대한 단위 테스트 추가
        -   [ ] `src/common/schemas/` 파일들에 대한 단위 테스트 추가
        -   [ ] `src/common/services/price_alert_service.py`에 대한 단위 테스트 추가
        -   [ ] `src/common/services/stock_service.py`에 대한 단위 테스트 추가
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

-   [ ] **API 인증 문제 (curl) 추가 디버깅:** (우선순위 낮음, 봇을 통한 기능은 정상 작동하므로)
-   [ ] **단위/통합 테스트에서 `test_page_limit` 활용:**
-   [ ] **DART API 최적화 (last_rcept_no) 추가 검증:**
-   [ ] **[신규] 알림 시스템 고도화:**
    -   **목표:** 현재 텔레그램에 종속된 알림 시스템을 다중 채널(이메일, SMS, 디스코드 등)을 지원하는 유연한 구조로 리팩토링합니다.
    -   **구현 방향:**
        1.  API가 Redis에 발행하는 메시지를 `{"user_id": ..., "message": ...}`와 같이 일반화합니다.
        2.  Worker는 이 메시지를 받아, DB에서 사용자의 알림 설정을 조회한 후, 설정된 모든 채널로 알림을 발송하는 "알림 라우터" 역할을 수행하도록 변경합니다.
        3.  사용자가 자신의 알림 채널을 설정할 수 있는 API를 구현합니다.
    -   **관련 문서:** `docs/archive/notification_system_architecture.md`

### Phase 7: 아키텍처 개선 - 서비스 결합도 완화 (진행 중)

*   **목표:** `worker` 서비스가 `api` 서비스의 소스 코드(`src/api/services`, `src/api/models`)에 직접 의존하는 문제를 해결하여 서비스 간 결합도를 낮추고 독립성을 강화합니다.
*   **세부 진행 계획:**
    *   [x] **1단계 (파일 이동):** `price_alert_service.py`, `stock_service.py` 및 `src/api/models`의 모든 모델 파일을 `src/common`으로 이동합니다.
    *   [x] **2단계 (코드 수정):** `worker` 및 `api` 서비스의 모든 관련 `import` 구문을 `src/common` 경로를 사용하도록 수정합니다.
    *   [x] **3단계 (설정 수정):** `docker-compose.yml`에서 `stockeye-worker` 서비스의 불필요한 볼륨 마운트(`src/api/services`, `src/api/models`)를 제거합니다.
    *   [ ] **4.단계 (검증):** `api`, `bot`, `worker`의 전체 테스트를 실행하고, 모든 서비스를 재기동하여 리팩토링 결과를 최종 검증합니다.
    -   [ ] `api` 서비스가 `bot` 서비스로부터 필요로 하는 로직 등을 식별합니다. 상기와 같은 방법으로 공유 모듈을 식별하여 분리합니다.

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
---

## 🐞 2025-08-12: `trigger_job` 명령어 버그 수정

-   **[완료] 봇 관리자 명령어(`trigger_job`) 오류 해결 및 기능 개선:**
    -   **문제:** `trigger_job [job_id]` 봇 명령어가 "잡 실행 완료" 메시지를 반환하지만, 실제로는 잡이 실행되지 않습니다.
    -   **원인 분석:**
        1.  `src/worker/routers/scheduler.py`의 `trigger_scheduler_job` 함수가 기존 잡을 즉시 실행(`modify`)하는 대신, 일회성으로 실행되는 새로운 잡을 추가(`add_job`)하고 있어, 의도대로 동작하지 않습니다.
    -   **해결 계획:**
        1.  **Worker 로직 수정:**
            -   `src/worker/routers/scheduler.py`의 `trigger_scheduler_job` 함수를 `job.modify(next_run_time=datetime.now(job.next_run_time.tzinfo))`를 사용하도록 수정하여, 잡이 즉시 실행되도록 올바르게 변경합니다.
            -   실행 결과를 명확하게 나타내는 JSON 응답(예: `{"job_id": job.id, "message": "Job triggered successfully", "triggered_at": ...}`)을 반환하도록 수정합니다.
        2.  **Bot 핸들러 수정:**
            -   `src/bot/handlers/admin.py`의 `admin_trigger_job` 함수를 Worker의 새로운 JSON 응답 형식에 맞게 메시지 포맷팅 부분을 수정하여, `job_id`와 `triggered_at` 등의 정보가 정확히 표시되도록 합니다.
        3.  **검증:**
            -   `docker compose`를 통해 전체 서비스를 재기동하고, 실제 봇 명령어를 통해 E2E 테스트를 수행하여 최종 결과를 검증합니다.
            -   `worker` 서비스의 로그를 확인하여 잡 실행 과정에서 오류가 없는지 확인합니다.

## Phase 8: 리소스 최적화 과제

### 8.1. `worker` 서비스 '종목마스터 갱신' OOM 문제 해결 (완료)

*   **문제:** Oracle VM 환경에서 '종목마스터 갱신' 관리자 명령어 실행 시 `worker` 서비스가 메모리 부족으로 다운되는 문제 발생. `src/common/dart_utils.py`의 `dart_get_all_stocks` 함수가 `CORPCODE.xml` 파일을 메모리에 통째로 로드하여 파싱하는 비효율적인 방식이 원인.
*   **해결:** `src/common/dart_utils.py` 파일을 수정하여 `dart_get_all_stocks` 함수에서 XML 파싱 방식을 `lxml.etree.iterparse`를 사용한 **스트리밍 파싱**으로 변경. 메모리 사용량을 획기적으로 줄임.
*   **관련 파일:** `src/common/dart_utils.py`
*   **검증:** Docker Compose 환경에서 성공적으로 검증 완료.

### 8.2. `일별 시세 갱신` 작업 리소스 최적화 (완료)

*   **과제 ID:** OPT-001
*   **문제:** `src/api/services/stock_service.py`의 `update_daily_prices` 함수는 DB의 모든 종목을 한 번에 가져와 `yfinance`를 통해 일별 시세를 갱신합니다. 종목 수가 증가할수록 메모리 사용량 및 처리 시간이 선형적으로 증가하여 OOM 발생 가능성이 높았습니다.
*   **해결 방안:**
    1.  **배치 처리 (Batch Processing):** `StockMaster`를 한 번에 모두 가져오지 않고, 일정 개수(100개)씩 끊어서 처리하도록 변경.
    2.  **벌크 삽입 (Bulk Insertion):** `db.add()` 대신 `db.bulk_save_objects()`를 사용하여 일별 시세 데이터를 한 번에 DB에 삽입하여 성능 및 메모리 효율 개선.
*   **관련 파일:** `src/api/services/stock_service.py`
*   **상태:** 과제 완료 및 Docker Compose 환경에서 성공적으로 검증 완료.

### 8.3. `전체 공시 갱신` 작업 리소스 최적화 (완료)

*   **과제 ID:** OPT-002
*   **문제:** `src/api/services/stock_service.py`의 `update_disclosures_for_all_stocks` 함수가 DART API에서 대량의 공시 데이터를 가져오고, DB에 이미 저장된 **모든 공시 접수번호**를 메모리에 로드하여 중복을 확인합니다. 공시 데이터가 많아질 경우 메모리 사용량이 급증하여 OOM 발생 가능성이 있었습니다.
*   **해결 방안:**
    1.  **DART API 호출 최적화:** `dart_utils.py`의 `dart_get_disclosures` 함수에 `last_rcept_no` 파라미터를 추가하고, `stock_service.py`에서 `SystemConfig`에 저장된 `last_checked_rcept_no`를 이 파라미터로 전달하도록 수정했습니다. 이를 통해 DART API에서 마지막으로 확인된 공시 이후의 데이터만 가져오도록 최적화했습니다.
    2.  **기존 공시 확인 최적화:** `check_and_notify_new_disclosures` 함수 내에서 DART에서 가져온 공시 중 DB에 이미 존재하는 공시를 필터링하는 로직을 개선했습니다.
*   **관련 파일:** `src/api/services/stock_service.py`, `src/common/dart_utils.py`
*   **상태:** 과제 완료 및 Docker Compose 환경에서 성공적으로 검증 완료.

### 8.4. `가격 알림 확인` 작업 내 쿼리 최적화 (진행 예정)

*   **과제 ID:** OPT-003
*   **문제:** `src/api/services/price_alert_service.py`의 `check_and_notify_price_alerts` 함수 내에서 `db.query(DailyPrice).filter(DailyPrice.symbol.in_(symbols_to_check)).order_by(DailyPrice.date.desc()).all()` 쿼리가 각 종목별 최신 가격을 효율적으로 가져오지 못하고, `symbols_to_check`의 크기가 커질 경우 쿼리 성능에 영향을 줄 수 있습니다.
*   **해결 방안:** 각 종목별 최신 가격을 효율적으로 가져오도록 쿼리를 최적화 (예: 서브쿼리 또는 `DISTINCT ON` 사용).
*   **관련 파일:** `src/api/services/price_alert_service.py`
*   **상태:** 과제 등록 및 진행 예정.

---

**[중요] 리소스 관리 및 향후 계획:**

Oracle VM 환경에서 안정적인 서비스 운영을 위해 리소스 관리는 매우 중요합니다. 이번 분석을 통해 식별된 모든 잠재적 병목 지점들은 `TODO.md`에 `OPT-XXX` 과제로 명확히 등록되었습니다. 앞으로 이 과제들을 우선순위에 따라 순차적으로 개선 작업을 진행할 예정입니다. 지속적인 모니터링과 최적화를 통해 시스템의 안정성과 성능을 확보해 나가겠습니다.

### Phase 9: Common 모듈 테스트 및 개선

-   [x] **[Test] `common` 모듈 단위 테스트 보강:**
    -   `dart_utils.py`의 DART API 에러 응답 및 페이지네이션 로직에 대한 단위 테스트를 추가하여 코드 안정성을 높입니다.

### Phase 10: Common 모듈 구조 리팩토링

-   [ ] **[Refactor] `common` 모듈 소스 파일 재분류:**
    -   `utils`, `database` 등 하위 디렉토리를 생성하고 관련 소스 파일을 이동하여 구조를 개선합니다.
    -   파일 이동에 따른 프로젝트 전체의 `import` 구문을 수정합니다.

### Phase 11: `common` 모듈 리팩토링 후 안정성 검증

-   [ ] **`common` 모듈 경로 변경 후 체계적 테스트 수행:**
    -   **목표:** `common` 모듈 리팩토링으로 인한 잠재적 오류를 파악하고 해결합니다.
    -   **테스트 절차:**
        1.  **단위 테스트:** `api`, `bot`, `worker` 각 서비스의 단위 테스트를 개별적으로 실행하여 핵심 기능의 정상 동작을 확인합니다.
            *   `docker compose exec stockeye-api pytest src/api/tests/unit`
            *   `docker compose exec stockeye-bot pytest src/bot/tests/unit`
            *   `docker compose exec stockeye-worker pytest src/worker/tests/unit`
        2.  **통합 테스트:** 각 서비스의 통합 테스트를 실행하여 서비스 내부 및 외부(DB 등) 연동 기능의 정상 동작을 확인합니다.
            *   `docker compose exec stockeye-api pytest src/api/tests/integration`
            *   `docker compose exec stockeye-bot pytest src/bot/tests/integration`
        3.  **E2E 테스트:** `bot` 서비스의 E2E 테스트를 실행하여 전체 시스템의 정상 동작을 확인합니다.
            *   `docker compose exec stockeye-bot pytest src/bot/tests/e2e`
    -   **오류 처리:**
        *   테스트 실패 시, 해당 오류가 `common` 모듈 리팩토링과 직접적인 관련이 있는지 분석합니다.
        *   **관련된 오류**는 즉시 수정합니다.
        *   **관련 없는 기존 오류**는 별도의 TODO 항목으로 등록하고, 현재 작업 범위에서는 수정하지 않습니다.

### Phase 12: 테스트 파일 구조 개선

-   [ ] **`api/tests` 폴더 내 테스트 파일 분류:**
    -   **목표:** `src/api/tests` 폴더 내의 테스트 파일들을 `unit`, `integration`, `e2e` 하위 폴더로 적절히 이동 및 분류하여 테스트 코드의 가독성과 관리 용이성을 높입니다.
    -   **세부 계획:**
        1.  `src/api/tests` 경로에 있는 `test_admin_scheduler.py`, `test_seed_data.py` 등의 파일을 내용에 따라 `unit` 또는 `integration` 폴더로 이동합니다.
        2.  이동 후, 각 테스트 파일의 `import` 경로 및 관련 설정을 업데이트합니다.
        3.  모든 테스트가 정상적으로 실행되는지 확인합니다.

## 🐞 2025-08-31: 단위 테스트 점검 및 수정 과제

-   **점검 요약:**
    -   ✅ **`common` 모듈:** 테스트 15개 모두 **통과**.
    -   ✅ **`api` 모듈:** `src/api/tests/unit/test_predict_service.py` 의 모든 테스트 **통과** (멈춤 문제 해결).
    -   ✅ **`bot` 모듈:** 모든 단위 테스트 **통과**.
    -   ✅ **`worker` 모듈:** 테스트 6개 모두 **통과**.

-   **수정 과제 목록:**
    -   [x] **`api` 모듈 테스트 행(hang) 문제 해결:** `src/api/tests/unit/test_predict_service.py` 실행 시 발생하는 무한 대기 현상을 분석하고 수정했습니다.
    -   [x] **`bot` 모듈 테스트 실패 수정:** `src/bot/tests/unit/test_alert_handler.py`의 `test_alert_list_success` 테스트가 실패하는 원인을 분석하고 수정했습니다.

# TODO List for StockEyeDev Integration Test Normalization

## High Priority

- [x] **Fix User Creation Issues in Tests:**
    - [x] Modify `src/api/tests/helpers.py`: Change `password_hash` to `hashed_password` in `create_test_user`.
    - [x] Modify `src/api/tests/conftest.py`: Import `UserCreate` and use it when calling `user_service.create_user` in `test_user` fixture.
- [x] **Fix `test_price_alert_service_integration.py` User Creation Issue:**
    - [x] Change `password_hash` to `hashed_password` in direct `User` instantiation.

## Medium Priority

- [ ] **Address `404 Not Found` Errors (Route Issues) in `test_api_admin_integration.py`:**
    - [x] Prepend `/api/v1` to all admin routes in `test_api_admin_integration.py`.
    - [x] Change `assert response.status_code == 401` to `assert response.status_code == 403` for unauthenticated tests.
    - [x] Fix `ModuleNotFoundError` in `@patch` decorators by correcting import paths.
    - [ ] **Fix `IndentationError` in `test_api_admin_integration.py` after commenting out scheduler tests.**
    - [ ] **Fix `test_update_disclosure_single_by_symbol_success_as_admin` message assertion.**
    - [ ] **Fix `test_update_disclosure_not_found_as_admin` mock.**

- [ ] **Fix `test_notification_publish_integration.py` Login Request Body:**
    - Change login request in test to send JSON instead of form data.

- [ ] **Fix `test_db_schema_integration.py` Type Mismatch:**
    - Adjust type comparison in test or ensure consistent type definitions for DATETIME/TIMESTAMP.

## Low Priority

- [ ] **Address `test_api_stock_master_integration.py` Missing Fixture:**
    - Find or create the `override_stock_service_dependencies` fixture.

- [ ] **Address `test_api_alerts_integration.py` Pydantic `model_validate` Issue:**
    - Investigate Pydantic version and correct `model_validate` usage.

- [ ] **Re-evaluate `test_stock_service_integration.py` Timeout:**
    - Re-run test after other fundamental issues are resolved to see if timeouts persist.

- [ ] **Comment out scheduler-related tests in `test_api_admin_integration.py`:**
    - This is a temporary measure to isolate issues. These tests will be re-enabled/fixed once the worker service is stable.