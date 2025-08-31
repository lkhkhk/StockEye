# 서비스 결합도 완화 과제 계획서

**날짜:** 2025-08-29

**목표:** `worker` 서비스가 `api` 서비스의 소스 코드에 직접 의존하는 문제를 해결하여, 각 서비스가 독립적으로 배포되고 수정될 수 있는 진정한 마이크로서비스 아키텍처를 구현합니다.

---

## 1단계: 공유 모듈 식별 및 파일 이동

`worker`가 사용하는 `api`의 서비스와 모델 파일을 `src/common` 디렉토리로 이동합니다.

- **대상 파일:**
    - `src/api/services/price_alert_service.py`
    - `src/api/services/stock_service.py`
    - `src/api/models/` 디렉토리의 모든 모델 파일
- **이동 경로:**
    - `src/common/services/`
    - `src/common/models/`

## 2단계: 소스 코드 및 설정 파일 수정

파일 이동에 따라, 코드가 새로운 경로를 참조하도록 `import` 구문을 수정하고 불필요한 Docker 볼륨 설정을 제거합니다.

- **`src/worker/main.py` 수정:**
    - `from src.api.services...` -> `from src.common.services...`
    - `from src.api.models...` -> `from src.common.models...`
- **`src/api` 전체 코드 수정:**
    - `api` 서비스 내에서 이동된 서비스나 모델을 사용하던 모든 파일의 `import` 경로도 `src/common/...`으로 변경합니다.
- **`docker-compose.yml` 수정:**
    - `stockeye-worker` 서비스 설정에서 아래 두 줄의 볼륨 마운트 설정을 삭제합니다.
      ```yaml
      - ./src/api/services:/app/src/api/services
      - ./src/api/models:/app/src/api/models
      ```

## 3단계: 전체 시스템 검증

리팩토링으로 인해 기존 기능에 문제가 발생하지 않았는지 확인하기 위해 전체 테스트 및 서비스 재기동을 수행합니다.

- **테스트 실행:** `api`, `bot`, `worker` 각 서비스에 대해 모든 단위/통합/E2E 테스트를 실행하여 통과하는지 확인합니다.
- **서비스 재기동:** `docker compose up -d --build` 명령으로 모든 서비스를 다시 빌드하고 시작합니다.
- **로그 확인:** 재기동 후, 모든 서비스의 로그를 확인하여 `import` 오류 없이 정상적으로 시작되는지 최종 검증합니다.

### 3.1. 단위 테스트 검증 현황 (2025-08-30)

- **결론:** `api`, `bot`, `worker` 서비스의 단위 테스트는 **아직 완전히 완료되지 않았습니다.**
- **상세 현황:**
    - **`api` 서비스 단위 테스트:**
        - `src/api/tests/unit/test_stock_service.py` (`test_check_and_notify_new_disclosures_success`) - **완료**
        - `src/api/tests/unit/test_admin_router.py` (`test_admin_stats`) - **완료**
        - 그 외 API 라우터 및 서비스 단위 테스트 - **진행 중**
    - **`bot` 서비스 단위 테스트:**
        - `src/bot/handlers/start.py` - **완료**
        - `src/bot/tests/unit/test_history_handler.py` (`history_command`) - **완료**
        - 그 외 봇 핸들러 단위 테스트 - **진행 중**
    - **`worker` 서비스 단위 테스트:**
        - `src/worker/tests/unit/test_listener.py` - **완료**
        - `src/worker/tests/unit/test_scheduler.py` - **완료**
        - 그 외 워커 단위 테스트 - **진행 중**
    - **`common` 모듈 단위 테스트:**
        - `dart_utils.py`, `db_connector.py`, `http_client.py`, `notify_service.py` 등 - **완료**
        - 그 외 공통 모듈 단위 테스트 - **진행 중**

---