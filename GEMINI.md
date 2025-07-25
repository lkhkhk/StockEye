# Gemini CLI Agent 지시사항 및 작업 기록

이 문서는 Gemini CLI Agent가 프로젝트 작업을 수행하면서 받은 주요 지시사항과 작업 기록을 관리합니다.

## 1. 작업 원칙 및 워크플로우

*   **선행 테스트:** 모든 신규 작업 착수 전, 전체 테스트를 먼저 실행하여 현 시스템의 안정성을 확인합니다.
*   **계획 수립 및 관리:**
    *   진행할 과제에 대한 상세 계획을 수립합니다.
    *   이 계획을 `docs/PLAN.MD` 파일에 To-Do 항목으로 추가하고, 진행 상황에 따라 항상 최신 상태로 업데이트합니다.
*   **개발 워크플로우:**
    1.  신규/변경 기능에 대한 **테스트 코드를 먼저 작성**합니다.
    2.  테스트를 통과하는 기능 코드를 구현합니다.
    3.  `docker compose`를 사용하여 전체 서비스를 다시 빌드하고 재기동합니다.
    4.  컨테이너 내에서 실제 기능을 테스트하여 완료를 확인합니다.
    5.  계획된 작업 단위가 완료되면, 진행 상황을 보고하고 다음 단계 진행에 대한 지시를 기다립니다.
*   **코드 품질 및 구조:**
    *   꼼꼼하고 신중하게 작업하며, 변경 사항이 기존 코드에 미치는 영향을 항상 확인합니다.
    *   기존 프로젝트 구조를 최대한 유지하며, 변경이 필요할 경우 사전에 상세 설명과 함께 문의합니다.
*   **`replace` 도구 사용 지침:**
    *   `replace` 도구 사용 전에는 반드시 `read_file`로 대상 파일의 현재 내용을 읽어옵니다.
    *   `old_string` 인자는 `read_file` 결과에서 변경할 부분을 정확히 복사하여 사용합니다. (공백, 들여쓰기, 줄바꿈 포함)
    *   `old_string`이 짧아 중복될 가능성이 있는 경우, 최소 3줄 이상의 충분한 컨텍스트를 포함합니다.
    *   여러 번 변경이 필요한 경우 `expected_replacements` 인자를 명시합니다.
*   **`src/common` 모듈 변경 시 주의사항:**
    *   `api`와 `bot` 서비스는 `src/common` 디렉토리를 공유하므로, 이 디렉토리 내의 파일 변경은 두 서비스 모두에 영향을 미칩니다.
    *   `src/common` 파일 변경 시, 해당 변경이 영향을 미치는 모든 `api` 및 `bot` 서비스의 관련 파일을 **동시에, 그리고 일관되게 수정**해야 합니다.
*   **실행 환경:**
    *   `docker compose` 명령어를 사용합니다.
    *   테스트 코드 작성 및 실행은 각 서비스(`api`, `bot`)의 `tests` 폴더 내에서, 컨테이너 안에서 수행합니다.
    *   파일 삭제 등 권한 문제가 발생할 수 있는 작업은 반드시 컨테이너 내부에서 실행합니다.
*   **커뮤니케이션:**
    *   지시사항을 잊지 않고 반복적인 지시가 발생하지 않도록 합니다.

## 2. 작업 기록

### 2.1. 프로젝트 분석 및 문서 현행화 (2025-07-25)

*   **목표:** 현재 프로젝트의 구조, 기술 스택, 기능 등을 분석하고 관련 문서를 최신화.
*   **수행 내용:**
    *   `README.md`, `docker-compose.yml`, `requirements.txt`, `PLAN.MD` 등 주요 설정 파일 분석.
    *   `src` 디렉토리 내 모든 Python 소스 코드 분석을 통해 기능 및 구현 상태 파악.
    *   `docs/PLAN.MD` 파일에 개발 단계별 현황 및 상세 TODO 항목 업데이트.
    *   `README.md` 파일의 폴더 구조 설명을 최신 상태 및 개선 제안 반영하여 업데이트.

### 2.2. 구조 개선 및 리팩토링 (2025-07-25)

*   **목표:** 코드의 일관성, 재사용성, 유지보수성을 높이기 위한 구조 개선 및 리팩토링 수행.
*   **수행 내용:**
    *   **라우터 통합:** `src/api/routers/admin_router.py` 파일을 삭제하고, 해당 라우터의 기능을 `src/api/routers/admin.py`로 통합.
    *   **공통 유틸리티 중앙화:** `requests_retry_session` 함수를 `src/common/http_client.py`로 분리하고, 관련 파일들에서 `session` 객체를 `src/common/http_client`에서 직접 import하도록 수정.
    *   **서비스 의존성 주입(DI) 패턴 적용:**
        *   `src/api/routers/admin.py`: `StockService`를 `Depends`를 통해 주입받도록 변경.
        *   `src/api/routers/stock_master.py`: `StockService`를 `Depends`를 통해 주입받도록 변경.
        *   `src/api/routers/simulated_trade.py`: `StockService`를 `Depends`를 통해 주입받도록 변경.
        *   `src/api/routers/predict.py`: `predict_stock_movement` 함수를 `Depends`를 통해 주입받도록 변경.
        *   `src/api/routers/notification.py`: `PriceAlertService`를 `Depends`를 통해 주입받도록 변경.
        *   `src/api/routers/bot_router.py`: `UserService`와 `PriceAlertService`를 `Depends`를 통해 주입받도록 변경.
        *   `src/api/main.py`: 스케줄러 잡에서 서비스 인스턴스를 직접 생성하는 대신, `get_stock_service` 및 `get_price_alert_service` 함수를 통해 인스턴스를 얻도록 변경.
        *   `src/api/services/user_service.py`: `user_service = UserService()` 직접 인스턴스화 제거.
    *   **불필요한 파일 제거:** `src/bot/services/notify_service.py` 파일 삭제.
*   **검증:** 각 변경 사항 적용 후 `docker compose up -d --build`를 통해 서비스 재빌드 및 재기동. `api` 및 `bot` 서비스의 모든 `pytest`를 실행하여 기능 및 안정성 검증 완료.