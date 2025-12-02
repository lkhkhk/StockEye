# StockEye 프로젝트 TODO 리스트

## 🎯 현재 진행 중 (In Progress)
- 없음

## 💡 신규 기능 (New Features)

- [x] **알림 목록 조회 기능 개선** ✅
  - 변동률 알림(`change_percent`) 정보 표시
  - API 응답 형식 개선

## 🧪 테스트 및 품질 (Testing & Quality)
- [x] **Worker 테스트 보강** ✅
  - 현재: 35개 테스트 (26개 → 35개, +9개)
  - 커버리지: 94% (90% → 94%, +4%p)
  - tasks.py: 89% (78% → 89%, +11%p)

- [x] **Bot 테스트 검토** ✅
  - 현재: 10개 테스트 파일 (중복 제거 완료)
  - 67/67 단위 테스트 통과

## 🛠️ 기술 부채 및 최적화 (Tech Debt & Optimization)
- [x] **DART API 최적화** ✅
  - `last_rcept_no` 검증 완료
  - `update_disclosures_for_all_stocks`에 최적화 적용
  - 불필요한 API 호출 제거

- [x] **서비스 의존성 분리** ✅
  - API ↔ Bot 코드 의존성 없음 확인
  - 모든 공유 코드는 `src/common`에 위치
  - 이미 완벽하게 분리된 상태

## 🐞 알려진 이슈 (Known Issues)
- [x] **`test_stock_service_integration.py` 타임아웃** ✅
  - 파일명: `test_api_stock_master_integration.py`
  - 테스트 결과: 8/8 통과, 7.70초
  - 타임아웃 이슈 없음 확인

- [x] **API 인증 문제 (curl)** ✅
  - Health check: 정상
  - 사용자 등록/로그인: 정상
  - JWT 토큰 인증: 정상
  - 인증 문제 없음 확인

---

## 📋 완료된 작업 (Completed)
<details>
<summary>클릭하여 보기</summary>

### 구조 개선
- [x] `common` 모듈 리팩토링
- [x] `api/tests` 폴더 구조 개선

### 테스트
- [x] Common 모듈: 170개 단위 테스트 (100% 통과)
- [x] API 모듈: 162개 단위 테스트 (100% 통과, 11개 스킵)
- [x] Bot 모듈: 67개 단위 테스트 (100% 통과)

### 기능
- [x] 알림 시스템 고도화 (다중 채널)
- [x] 사용자 알림 설정 기능

### 성능
- [x] 가격 알림 쿼리 최적화 (N+1 해결)
- [x] DB 인덱스 최적화

### 코드 품질
- [x] **Pydantic V2 마이그레이션** ✅ (2025-12-02 완료)
  - 5개 스키마 파일 마이그레이션
  - `@validator` → `@field_validator`
  - `class Config` → `ConfigDict`
  - `.dict()` → `.model_dump()`
  - 모든 단위 테스트 통과 (399/399)
  - Bot 테스트 중복 제거 (3개 파일 삭제)
  - API 테스트 수정 (httpx mock, JWT, retry 카운트 등)

- [x] **Worker/Bot 테스트 커버리지 보강** ✅ (2025-12-02 완료)
  - Bot 단위 테스트: 67/67 통과
  - Worker 테스트: 12개 → 29개 (+17개, +142%)
  - Phase 1: Scheduler Router 테스트 8개
  - Phase 2: Helper Function 테스트 6개
  - Phase 3: Job Trigger 테스트 3개
  - Worker 커버리지: ~70% → ~95%

- [x] **이메일 알림 실제 구현** ✅ (2025-12-02 완료)
  - Gmail SMTP 통합 (aiosmtplib)
  - HTML 이메일 템플릿 3개 (base, notification, price_alert)
  - 환경 변수 기반 설정 (email_config.py)
  - 단위 테스트 4개 (100% 통과)
  - EMAIL_SETUP.md 가이드 작성

### 버그 수정
- [x] 모든 테스트 실패 해결
- [x] Pydantic v2 호환성 이슈 해결
- [x] Bot 핸들러 테스트 mock 이슈 해결
- [x] API 테스트 assertion 이슈 해결

</details>

---

## 🎯 다음 작업 우선순위
1. ~~**Pydantic V2 마이그레이션**~~ ✅ 완료
2. **Worker 테스트 보강** (품질 보증)
3. **이메일 알림 구현** (기능 완성)