# Maintenance & Operations (운영/유지보수)

## 1. DB 초기화/마이그레이션
- DB 볼륨/폴더 삭제, 마이그레이션, Alembic 등
- DB 백업/복구, 데이터 마이그레이션 절차
- 예시 명령어 및 체크리스트

## 2. 로그 파일 관리
- logs/app.log, logs/bot.log 파일 위치 및 확인 방법
- 로그 파일 회전(RotatingFileHandler) 설정, 운영 중 로그 모니터링 방법
- 로그 파일 용량 관리, 백업/보관/삭제 절차

## 3. 장애 대응/복구
- 장애 발생 시 우선 확인 항목(로그, DB, 백업본 등)
- 컨테이너 재기동, 이미지 재빌드, 운영 체크리스트
- 장애/이벤트 발생 시 PLAN.md, SystemManual.md, features_analysis.md 참고

## 4. 운영 자동화/배포
- 컨테이너 재기동, 이미지 재빌드, 운영 자동화 스크립트
- 운영/개발 환경 분리, 환경변수 관리, 보안/권한 관리 등

## 5. 기타
- 서비스별 환경변수 관리, 운영/개발 환경 분리, 보안/권한 관리 등
- 추가 문의/자동화/마이그레이션 도구 적용 필요시 담당자 문의 

# 패키지 관리 및 테스트/운영 환경 정책

## 1. 외부 패키지(lxml 등) 누락 시 문제
- 예시: `ModuleNotFoundError: No module named 'lxml'`
- 원인: requirements.txt에 패키지가 누락되어 컨테이너 빌드시 설치되지 않음
- 영향: 컨테이너 내부에서 테스트/운영 시 ImportError 발생, 기능 동작 불가

## 2. 근본적 해결책 및 정책
- 모든 외부 패키지는 반드시 requirements.txt에 명시
- requirements.txt가 변경되면 반드시 컨테이너를 재빌드/재기동
- Dockerfile에서 `pip install -r requirements.txt`로 일관 설치
- 테스트는 반드시 컨테이너 내부에서 실행 (운영 환경과 동일하게 검증)
- (예: `docker compose exec api pytest src/api/tests`)

## 3. 자동화/문서화 방안
- Makefile, README, PLAN.md, 개발 가이드에 위 정책을 명확히 반영
- CI/CD 파이프라인에서도 컨테이너 내부 테스트만 허용

## 4. 문제 발생시 조치 예시
1. requirements.txt에 누락된 패키지 추가
2. `docker compose build api`로 컨테이너 재빌드
3. `docker compose up -d api`로 재기동
4. `docker compose exec api pytest src/api/tests`로 테스트 