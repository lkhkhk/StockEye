# 서브 프로젝트: 알림 시스템 리팩토링

**최종 업데이트:** 2025-09-04

## 1. 프로젝트 목표

현재 알림 시스템은 가격 알림과 공시 알림이 하나의 모델로 혼재되어 있어 구조가 복잡하고 사용자에게 혼란을 줍니다. 본 서브 프로젝트는 전체 알림 시스템을 리팩토링하여 두 종류의 알림을 명확히 분리하고, 이를 통해 더 안정적이고 확장 가능하며 사용자 친화적인 기능을 제공하는 것을 목표로 합니다.

## 2. 핵심 요구사항

- **관심사 분리:** 가격 알림과 공시 알림을 시스템 전반(데이터베이스, API, 봇)에서 독립적인 기능으로 관리합니다.
- **일관된 관리 경험:** 사용자가 `추가`, `목록`, `삭제`, `일시정지`, `재개` 등 통일된 명령어 체계로 두 종류의 알림을 모두 관리할 수 있도록 합니다.
- **사용자 플로우 개선:** 봇의 명령어 구조와 알림 설정을 위한 대화 흐름을 더 직관적으로 개선합니다.

---

## 3. 리팩토링 계획

### 1단계: 백엔드 (API) 및 데이터베이스 리팩토링 (완료)

본 단계의 목표는 데이터 및 API 레벨에서 가격 알림과 공시 알림을 명확하게 분리하는 것입니다.

-   [x] **과제 1.1: 데이터베이스 모델 재설계 (`src/common/models`)**
    -   [x] `price_alert.py` 수정: `notify_on_disclosure` 컬럼 제거 (완료)
    -   [x] `disclosure_alert.py` 생성: `id`, `user_id`, `symbol`, `is_active` 필드를 가진 신규 모델 생성 (완료)
    -   [x] `user.py` 수정: `User` 모델에 신규 `disclosure_alerts` 관계 추가 (완료)

-   [x] **과제 1.2: API 스키마 재설계 (`src/common/schemas`)**
    -   [x] `price_alert.py` 수정: 모든 Pydantic 스키마에서 `notify_on_disclosure` 필드 제거 (완료)
    -   [x] `disclosure_alert.py` 생성: `DisclosureAlertCreate`, `DisclosureAlertRead`, `DisclosureAlertUpdate` 등 신규 Pydantic 스키마 작성 (완료)

-   [x] **과제 1.3: API 서비스 계층 리팩토링 (`src/common/services`)**
    -   [x] `disclosure_alert_service.py` 생성: 공시 알림에 대한 CRUD 서비스 로직 구현 (완료)
    -   [x] `price_alert_service.py` 수정: `notify_on_disclosure` 관련 로직 제거 (완료)

-   [x] **과제 1.4: API 라우터 리팩토링 (`src/api/routers`)**
    -   [x] `disclosure_alert_router.py` 생성: 공시 알림 관리를 위한 API 엔드포인트 (`/disclosure-alerts/`) 구현 (완료)
    -   [x] `notification.py`를 `price_alert_router.py`로 이름 변경하여 명확성 확보 (완료)
    -   [x] `price_alert_router.py`에서 공시 관련 로직 제거 (완료)
    -   [x] `src/api/main.py` 수정: 신규 `disclosure_alert_router`를 포함하고, 라우터 이름 변경사항 반영 (완료)

### 2단계: 봇 핸들러 리팩토링 (완료)

본 단계는 새롭게 설계된 백엔드 기능을 명확하고 일관된 텔레그램 명령어를 통해 사용자에게 제공하는 데 중점을 둡니다.

-   [x] **과제 2.1: 봇 명령어 통일 (`src/bot/handlers/alert.py`)**
    -   [x] `/set_price` 명령어 폐지 (완료)
    -   [x] 사용자를 안내하는 메인 `/alert` 명령어 핸들러 생성 (완료)
    -   [x] `add`, `list`, `delete`, `pause`, `resume` 등 하위 기능에 대한 대화형 플로우 또는 서브 명령어 구현 (완료)

-   [x] **과제 2.2: 알림 생성 플로우 리팩토링 (`/alert add`)**
    -   [x] 사용자가 주식 종목을 입력하면, "가격 알림"과 "공시 알림" 옵션 제공 (완료)
    -   [x] 사용자가 선택한 유형에 맞춰 알림을 설정하도록 안내 (완료)
    -   [x] 유형에 맞는 신규 API 엔드포인트 (`/price-alerts/` 또는 `/disclosure-alerts/`) 호출 (완료)

-   [x] **과제 2.3: 알림 목록 플로우 리팩토링 (`/alert list`)**
    -   [x] `/price-alerts/`와 `/disclosure-alerts/` 엔드포인트에서 모두 데이터를 가져옴 (완료)
    -   [x] 두 종류의 알림이 명확히 구분되는 통합 목록을 사용자에게 표시 (완료)

-   [x] **과제 2.4: 알림 관리 플로우 구현 (`/alert delete`, `/alert pause` 등)**
    -   [x] 사용자가 자신의 알림 목록에서 특정 알림을 선택하여 관리 작업을 수행할 수 있도록 구현 (완료)
    -   [x] 각 작업에 맞는 `PUT` 또는 `DELETE` API 호출 (완료)

-   [x] **과제 2.5: 메인 봇 애플리케이션 업데이트 (`src/bot/main.py`)**
    -   [x] 기존 핸들러 (`set_price_alert` 등) 제거 (완료)
    -   [x] 신규 `/alert` 명령어 핸들러 및 관련 콜백 핸들러 등록 (완료)