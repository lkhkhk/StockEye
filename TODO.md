# StockEye 프로젝트 TODO 리스트

## 🎯 최우선 과제 (High Priority)
- [ ] **테스트 보강**: `common`, `worker`, `api`, `bot`의 단위/통합/E2E 테스트 커버리지 보강.
- [ ] **`common` 모듈 리팩토링**: `utils`, `database` 등 하위 디렉토리 생성 및 파일 재분류, `import` 경로 수정.
- [ ] **`api/tests` 폴더 구조 개선**: `unit`, `integration`, `e2e` 하위 폴더로 테스트 파일 분류.

## 💡 신규 기능 및 개선 (Features & Enhancements)
- [ ] **알림 시스템 고도화**: 다중 채널(이메일, SMS 등) 지원을 위한 유연한 구조로 리팩토링.
- [ ] **알림 목록 조회 기능 개선**: 변동률 알림(`change_percent`) 처리 및 정보 표시.

## 🐞 버그 수정 (Bug Fixes)
- [ ] **API 인증 문제 (curl) 추가 디버깅**: (우선순위 낮음)
- [ ] **`test_api_admin_integration.py` 오류 수정**: `IndentationError` 및 메시지 단언문, Mock 관련 오류 수정.
- [ ] **`test_notification_publish_integration.py` 로그인 요청 수정**: JSON 형식으로 변경.
- [ ] **`test_db_schema_integration.py` 타입 불일치 수정**: DATETIME/TIMESTAMP 타입 일관성 확인.
- [ ] **`test_api_stock_master_integration.py` 픽스처 누락 처리**: `override_stock_service_dependencies` 픽스처 생성/확인.
- [ ] **`test_api_alerts_integration.py` Pydantic v2 마이그레이션**: `model_validate` 사용법 수정.
- [ ] **`test_stock_service_integration.py` 타임아웃 재평가**: 근본 원인 해결 후 테스트 재실행.
- [ ] **`test_symbols_integration.py` 단언문 실패 수정**.
- [ ] **`test_bot_symbols.py` Mock 호출 인자 문제 수정**.
- [ ] **`test_http_client.py` Mock 호출 인자 문제 수정**.
- [ ] **`test_stock_master_service.py` 단언문 실패 수정**.
- [ ] **`test_api_bot_e2e.py::test_alert_scenario_e2e` 403 오류 수정**.

## 🛠️ 리팩토링 및 기타 (Refactoring & Others)
- [ ] **DART API 최적화**: `last_rcept_no` 추가 검증.
- [ ] **가격 알림 확인 쿼리 최적화**: `check_and_notify_price_alerts` 함수 내 쿼리 성능 개선.
- [ ] **`api` 서비스의 `bot` 의존성 분리**: 공유 모듈 식별 및 분리.