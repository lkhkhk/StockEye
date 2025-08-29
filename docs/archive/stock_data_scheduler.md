# 종목정보/일별시세 자동화 스케줄러 및 운영 가이드

## 1. 개요
- 종목마스터(상장종목) 및 일별 시세(OHLCV) 데이터의 자동/수동 갱신을 위해 API 서버에 내장 스케줄러를 도입
- 운영자는 텔레그램 봇 명령어로 수동 트리거 및 스케줄 관리 가능

## 2. 구조 및 흐름

### A. API 서버 내장 스케줄러
- APScheduler 등으로 FastAPI 서버 내에서 주기적 잡 등록/관리
- 예시: 매일 새벽 3시 종목마스터 갱신, 18시 일별 시세 갱신
- 스케줄러는 API 서버 기동 시 자동 등록, 필요시 동적 추가/삭제/즉시 실행 가능

### B. 수동 갱신: 봇 명령어 → API 호출
- 운영자가 텔레그램 봇에 `/update_master`, `/update_price` 등 명령어 입력
- 봇이 API 서버의 `/admin/update_master`, `/admin/update_price` 등 엔드포인트 호출
- API 서버는 해당 잡을 즉시 실행하거나, 스케줄러에 등록

### C. 잡 관리 및 확장
- 봇 명령어로 즉시 실행, 주기적 스케줄 등록/해제, 스케줄 상태 조회 등 가능
- 필요시 잡 추가/삭제/변경/상태조회 API 확장 가능

## 3. 장점
- 운영자가 서버에 직접 접속할 필요 없이, 텔레그램 봇 명령어만으로 모든 갱신/스케줄 관리 가능
- 스케줄/즉시실행/상태조회 등 통합 관리
- crontab 등 외부 의존성 없이 서비스 내에서 일원화

## 4. 운영/개발 가이드

### 1) 스케줄러 연동
- FastAPI(main.py 등)에서 APScheduler 인스턴스 생성 및 샘플 잡 등록
- 예시: 종목마스터/일별시세 갱신 함수 등록

### 2) 관리자용 API 엔드포인트
- `/admin/update_master` : 종목마스터 즉시 갱신
- `/admin/update_price` : 일별시세 즉시 갱신
- `/admin/schedule/list` : 등록된 잡/스케줄 상태 조회
- `/admin/schedule/add`/`/remove` : 스케줄 추가/삭제(확장)

### 3) 봇 명령어 연동
- `/update_master` → API 호출(즉시 실행)
- `/update_price` → API 호출(즉시 실행)
- `/show_schedules` → API 호출(스케줄 상태 조회)
- `/add_schedule` `/remove_schedule` 등도 확장 가능

### 4) 운영 자동화/문서화
- 운영자는 봇 명령어만으로 데이터 갱신/스케줄 관리 가능
- 주요 운영/배포/복구 절차는 README 및 docs/ 내 문서 참고

## 5. 참고
- APScheduler, FastAPI, 텔레그램 봇 연동 예제 및 샘플 코드는 src/api, src/bot, scripts/ 폴더 참고
- 보안상 관리자 인증/권한 체크 필수
- 장애/이벤트 발생 시 TODO.md, README, 로그, DB 백업본 우선 확인 