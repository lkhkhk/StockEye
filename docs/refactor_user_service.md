# 리팩토링: UserService를 공통 모듈로 이동

## 1. 무엇을 하는 작업인가요?

- `src/api/services/user_service.py` 파일을 `src/common/services/user_service.py`로 이동합니다.
- 이를 통해 `UserService`를 `api`, `bot`, `worker` 등 모든 서비스에서 사용할 수 있는 공통 컴포넌트로 만듭니다.

## 2. 왜 이 작업을 하나요?

- **서비스 결합도 완화:** 다른 서비스가 `api` 서비스의 내부 구현에 직접 의존하는 문제를 해결합니다.
- **코드 재사용성 향상:** 모든 서비스가 사용자 관리 로직을 재사용할 수 있도록 합니다.
- **유지보수 용이성 증대:** 사용자 관리 로직을 한 곳에서 중앙 관리하여 유지보수성을 높입니다.

## 3. 어떻게 진행하나요? (작업 체크리스트)

- [ ] **1. 파일 이동:**
    - `mv src/api/services/user_service.py src/common/services/user_service.py`
- [ ] **2. Import 경로 수정:**
    - [ ] 프로젝트 전체에서 `from src.api.services.user_service import` 구문을 검색합니다.
    - [ ] 검색된 모든 구문을 `from src.common.services.user_service import` 로 변경합니다.
- [ ] **3. 변경 사항 검증:**
    - [ ] `api` 서비스 단위 테스트 실행
    - [ ] `api` 서비스 통합 테스트 실행
    - [ ] `bot` 서비스 단위 테스트 실행
    - [ ] `bot` 서비스 E2E 테스트 실행
    - [ ] `worker` 서비스 단위 테스트 실행
    - [ ] `worker` 서비스 E2E 테스트 실행
