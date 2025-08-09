# StocksEye 개발 계획 및 현황

## 🚨 최우선 과제: 아키텍처 재설계 및 안정화

> **현황:** E2E 테스트 과정에서 `api`와 `bot` 서비스 간의 순환 의존성으로 인한 심각한 네트워크 오류 및 기능 미작동 문제가 발견되었습니다. 이를 해결하기 위해 Message Queue(Redis)를 도입하고, 비동기 작업을 처리하는 별도의 `worker` 서비스를 추가하는 것으로 아키텍처를 재설계하기로 결정했습니다.

> **목표:** 새로운 아키텍처를 성공적으로 도입하여 서비스 간 결합도를 낮추고, 시스템 전체의 안정성과 확장성을 확보합니다. 이 과정에서 기존의 핵심 기능 미작동 버그들을 모두 해결하고, 안정적인 E2E 테스트를 구축합니다.

---

### Phase 1: 아키텍처 재설계 및 인프라 구축

-   [x] **[인프라] `docker-compose.yml` 수정:**
    -   [x] `redis` 서비스를 신규 추가했습니다.
    -   [x] `worker` 서비스를 신규 추가하고 `Dockerfile`을 작성했습니다.
    -   [x] 모든 서비스(`api`, `bot`, `db`, `redis`, `worker`)의 이름과 `container_name`에 `stockseye-` 접두사를 붙여 명명 규칙을 통일했습니다.
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

-   [ ] **[기능 누락] 예측 이력 저장을 위한 `user_id` 전달:**
    -   **해결:** `predict`, `natural` 핸들러에서 `/predict` API 호출 시 `telegram_id`를 포함하도록 수정하고, `api`는 이를 `user_id`로 변환하여 이력을 저장하도록 합니다.
    -   **검증:** E2E 테스트를 통해 예측 이력이 DB에 정상적으로 저장되는지 확인합니다.

## 🌟 Phase 4: 테스트 고도화 및 지침 개선 (유지)

-   [ ] **(기존) 단위 테스트 커버리지 100% 달성**
    -   [ ] **Bot 핸들러:** `start.py`, `history.py` 등 누락된 단위 테스트를 작성합니다.
    -   [ ] **API 라우터:** `admin.py` 등 단위 테스트가 없는 모든 라우터에 대해 신규 작성합니다.
    -   [ ] **API 서비스:** `stock_service.py` 등 기존 테스트를 보강하고 순수 단위 테스트로 리팩토링합니다.
    -   [ ] **`common` 모듈:** 모든 공통 모듈에 대한 단위 테스트를 작성합니다.
-   [ ] **(기존) 통합 테스트 보강**
    -   [ ] `predict.py` 등 통합 테스트가 없는 API 라우터에 대해 신규 작성합니다.