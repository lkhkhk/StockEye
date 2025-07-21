# 실시간 공시 알림 기능

## 1. 개요

DART 공시 API를 주기적으로 확인하여 새로운 공시가 올라오면, 관련 정보를 구독한 사용자에게 텔레그램으로 실시간 알림을 보내는 기능입니다.

## 2. 아키텍처 및 흐름

```mermaid
sequenceDiagram
    participant Scheduler as APScheduler (in api)
    participant StockService as StockService (in api)
    participant DartApi as DART API (External)
    participant Database as PostgreSQL DB
    participant Telegram as Telegram API (External)

    Scheduler->>StockService: 5분마다 check_and_notify_new_disclosures() 호출
    StockService->>Database: 마지막으로 확인한 공시 ID(rcept_no) 조회
    Database-->>StockService: 마지막 공시 ID 반환
    StockService->>DartApi: 최신 공시 목록 요청
    DartApi-->>StockService: 최신 공시 목록 반환
    StockService->>StockService: DB에서 조회한 마지막 공시 ID와 비교하여 신규 공시 필터링
    alt 신규 공시 존재
        StockService->>Database: 해당 종목을 구독한 사용자 목록 조회
        Database-->>StockService: 사용자 목록(telegram_id) 반환
        loop 각 사용자
            StockService->>Telegram: 텔레그램 알림 메시지 전송
        end
        StockService->>Database: 마지막 신규 공시 ID를 DB에 업데이트
        Database-->>StockService: 업데이트 완료
    else 신규 공시 없음
        StockService->>StockService: 작업 종료
    end
```

## 3. 핵심 구현 내용

### 3.1. 주기적 실행 (Polling)

-   `api` 서비스의 `APScheduler`를 사용하여 `stock_service.check_and_notify_new_disclosures` 함수를 60분 간격으로 주기적으로 실행합니다.

### 3.2. 중복 알림 방지

-   서버가 재시작되어도 마지막으로 확인한 공시를 기억하기 위해, `system_config` 테이블을 사용합니다.
-   `key`가 `last_checked_rcept_no`인 값에 마지막으로 처리한 공시의 접수번호를 저장하고, 다음 실행 시 이 번호보다 최신인 공시만 처리합니다.
-   **테이블 모델:** `src/api/models/system_config.py`

### 3.3. 예외 처리 강화

-   **`DartApiError` 사용자 정의 예외:** DART API 통신 중 발생하는 오류(네트워크, API 응답 오류 등)를 명확하게 처리하기 위해 사용자 정의 예외 클래스를 도입했습니다. (`src/common/exceptions.py`)
-   **오류 상황별 처리:** API 사용량 초과(`status: 020`)와 같은 특정 오류 발생 시, `CRITICAL` 레벨의 로그를 남기고 작업을 안전하게 중단하여 서비스 안정성을 높였습니다.

### 3.4. 테스트 엔드포인트

-   스케줄러 주기를 기다리지 않고 기능을 즉시 테스트할 수 있도록 다음 엔드포인트를 추가했습니다.
    -   `POST /admin/trigger/check_disclosures`

## 4. 관련 파일

-   **핵심 로직:** `src/api/services/stock_service.py`
-   **API 통신:** `src/common/dart_utils.py`
-   **스케줄러 및 라우터:** `src/api/main.py`, `src/api/routers/admin.py`
-   **DB 모델:** `src/api/models/system_config.py`
-   **예외 클래스:** `src/common/exceptions.py` 