# StockEye (주시봇)

실시간 주식 공시 정보 알림 텔레그램 봇

## 주요 기능

*   **실시간 공시 알림:** 사용자가 등록한 주식의 새로운 공시 정보를 DART에서 주기적으로 확인하여 텔레그램 메시지로 알림을 보냅니다.
*   **사용자 관리:**
    *   `/register`: 봇 사용을 위한 사용자 등록 (간단한 인증 키 필요).
    *   `/list_users [페이지번호]` (관리자 전용): 등록된 모든 사용자 목록 보기 (페이지네이션, 사용자별 등록 종목 수 표시).
    *   `/delete_user <user_id>` (관리자 전용): 특정 사용자 및 관련 데이터 삭제.
*   **주식 모니터링 관리:**
    *   `/add`: 모니터링할 주식 추가 (종목코드 또는 이름으로 DB 검색 및 확인 절차 포함). 검색 결과 없을 시 `/search` 안내.
    *   `/remove`: 모니터링 중인 주식을 버튼으로 선택하여 삭제.
    *   `/list`: 현재 모니터링 중인 주식 목록 보기 (종목 선택 시 최근 공시 5건 조회 가능).
    *   `/search <검색어>`: DB에 저장된 주식 검색 (종목코드 또는 이름). 결과에서 '➕' 버튼으로 바로 모니터링 추가 가능.
*   **DB 및 공시 정보 관리:**
    *   **자동 DART 기업 정보 갱신:** 매일 새벽 4시 (기본값) 및 봇 시작 시 DART 고유번호 정보를 자동으로 다운로드하여 `stocks` DB에 **삽입 또는 갱신(Upsert)**합니다. (DART 목록의 모든 유효한 종목 반영).
    *   `/update_corp_codes` (관리자 전용): DART 고유번호 정보를 수동으로 즉시 갱신 (DB Upsert 수행). 삽입/갱신 결과 알림.
    *   `/check_disclosures [corp_code|all]` (관리자 전용): 특정 기업(고유번호) 또는 전체 모니터링 대상의 공시 정보를 수동으로 즉시 확인 및 알림 발송.
    *   `/list_all_stocks [페이지번호]` (관리자 전용): DB에 저장된 전체 주식 목록 보기 (페이지네이션 지원).
*   **기타:**
    *   `/start`: 봇 시작 및 환영 메시지 (관리자에게는 관리 메뉴 안내 추가).
    *   `/help`: 도움말 및 명령어 안내.
    *   `/admin` (관리자 전용): 관리자 명령어 목록 보기.
    *   `/broadcast <message>` (관리자 전용): 모든 등록 사용자에게 공지 메시지 발송.
    *   `/cancel`: 진행 중인 대화(등록, 추가 등) 취소.
    *   **설정 가능:** `.env` 파일에서 DART API 키, 텔레그램 봇 토큰, DB 정보, 공시 확인 주기(`UPDATE_INTERVAL`, 분 단위), 관리자 ID 등을 설정할 수 있습니다.
    *   **로깅:** JSON 형식의 로그를 표준 출력으로 제공합니다.
    *   **모니터링:** Prometheus 메트릭 엔드포인트 제공 (`:8000`).

## 기술 스택

*   Python 3.11+
*   Telegram Bot API (python-telegram-bot v20+)
*   PostgreSQL (asyncpg)
*   Redis (redis-py) - (선택적, 현재 직접 사용 빈도 낮음)
*   HTTPX (DART API 통신)
*   APScheduler (DART 정보 자동 갱신 및 주기적 공시 확인 스케줄링)
*   lxml (XML 파싱)
*   Docker & Docker Compose

## 소스 구조

```
StockEye/
├── app/
│   ├── core/                 # 핵심 모듈 (설정, DB 연결/초기화, 로거, 스케줄러)
│   │   ├── config.py         # 환경 변수 및 설정 관리
│   │   ├── database.py       # 데이터베이스 연결 및 테이블 초기화
│   │   ├── logger.py         # 로깅 설정
│   │   └── scheduler.py      # APScheduler 설정 및 관리
│   ├── models/               # 데이터 모델 정의 (Pydantic 또는 dataclasses)
│   │   ├── user.py           # 사용자 모델
│   │   └── stock.py          # 주식 모델
│   ├── services/             # 주요 비즈니스 로직
│   │   ├── telegram.py       # 텔레그램 봇 핸들러, 명령어 처리, 콜백 로직
│   │   ├── disclosure.py     # 공시 정보 확인 및 알림 관련 로직
│   │   └── dart_updater.py   # DART API 통신 및 기업 고유번호 DB 갱신 로직
│   └── __main__.py           # 애플리케이션 진입점, 초기화, 메인 루프
├── migrations/             # 데이터베이스 마이그레이션 스크립트 (Alembic 등, 필요시 사용)
├── tests/                  # 단위 테스트, 통합 테스트 코드 (선택 사항)
├── .env                    # 환경 변수 설정 파일 (사용자가 직접 생성)
├── .gitignore              # Git 무시 파일 목록
├── docker-compose.yml      # Docker Compose 설정 (DB, Redis, 앱 서비스 정의)
├── Dockerfile              # 애플리케이션 Docker 이미지 빌드 설정
└── README.md               # 프로젝트 설명 및 안내 문서 (현재 파일)
```

## 설치 및 실행

**(설치 단계는 기존 내용을 유지)**

**환경 변수 설정 (`.env`):**

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 필수적으로 채웁니다. 다른 값은 필요에 따라 조정합니다.

```dotenv
# --- 필수 설정 ---
DART_API_KEY=YOUR_DART_API_KEY_HERE              # DART API 인증키
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE  # 텔레그램 봇 토큰
DB_PASSWORD=YOUR_SECURE_DB_PASSWORD          # PostgreSQL 비밀번호

# --- 선택 및 기본값 설정 ---
ADMIN_ID=YOUR_TELEGRAM_ADMIN_USER_ID_HERE    # 관리자 기능 사용 시 필수 (숫자 ID)
UPDATE_INTERVAL=15                           # 공시 확인 주기 (분 단위, 변경 후 봇 재시작 필요)
DB_HOST=stockeye_db                          # Docker 내부 DB 호스트 이름 (보통 변경 불필요)
DB_PORT=5432
DB_NAME=stockeye
DB_USER=stockeye
REDIS_HOST=stockeye_redis                      # Docker 내부 Redis 호스트 이름 (보통 변경 불필요)
REDIS_PORT=6379
LOG_LEVEL=INFO                               # 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
```

**서비스 실행 (Docker Compose 권장):**

프로젝트 루트 디렉토리에서 다음 명령어를 실행합니다.

*   **최초 빌드 및 백그라운드 실행:**
    ```bash
    docker-compose up --build -d
    ```
*   **실행 중인 컨테이너 확인:**
    ```bash
    docker ps
    ```
*   **애플리케이션 로그 확인:**
    ```bash
    docker-compose logs -f stockeye_app
    ```
*   **서비스 중지 및 컨테이너/네트워크 제거:**
    ```bash
    docker-compose down
    ```
*   **코드 수정 후 재시작 (이미지 재빌드 포함):**
    ```bash
    # 1. 중지 및 제거 (볼륨 데이터는 유지됨)
    docker-compose down --remove-orphans
    # 2. 재빌드 및 재시작
    docker-compose up --build --force-recreate -d
    ```

## 서비스 사용법 (텔레그램 봇 명령어)

봇과의 대화창에서 다음 명령어들을 사용할 수 있습니다.

**일반 사용자 명령어:**

*   `/start` : 봇 시작 및 환영 메시지 표시
*   `/help` : 사용 가능한 명령어 및 도움말 보기
*   `/register` : 봇 사용을 위한 사용자 등록 (기본 인증 키: `stockeye`)
*   `/add` : 모니터링할 주식 추가 시작. '종목코드 종목명' 또는 '종목명' 또는 '종목코드' 형식으로 입력. (예: `005930 삼성전자`, `삼성전자`, `005930`). DB 검색 후 확인 절차 진행.
*   `/remove` : 모니터링 중인 주식을 버튼으로 선택하여 삭제
*   `/list` : 현재 모니터링 중인 주식 목록 보기. 목록에서 종목 버튼 클릭 시 최근 공시 5건 조회 가능 (DART 고유번호가 있는 경우).
*   `/search <검색어>`: DB에 저장된 주식 검색 (종목코드 또는 이름). 결과 목록의 버튼 클릭 시 해당 종목 모니터링 추가 가능.
*   `/cancel` : 진행 중인 작업(등록, 추가 등) 취소

**관리자 전용 명령어:** (`.env` 파일에 `ADMIN_ID` 설정 필요)

*   `/admin` : 관리자 명령어 목록 보기
*   `/list_users [페이지번호]` : 모든 등록 사용자 목록 보기 (페이지네이션 지원). 사용자 정보 및 모니터링 중인 종목 수 표시.
*   `/list_all_stocks [페이지번호]` : DB에 저장된 전체 주식 목록 보기 (페이지네이션 지원). 종목 코드, 이름, DART 고유번호 표시.
*   `/delete_user <user_id>` : 특정 사용자 및 사용자의 모니터링 정보 삭제 (주의!).
*   `/broadcast <메시지>` : 모든 등록 사용자에게 공지 메시지 발송.
*   `/update_corp_codes` : DART API에서 최신 기업 고유번호 정보를 가져와 DB에 즉시 반영(Upsert). 작업 결과 (삽입/갱신 건수) 알림.
*   `/check_disclosures [corp_code|all]` : 특정 기업(8자리 고유번호) 또는 전체 모니터링 대상 종목의 공시 정보를 수동으로 즉시 확인하고 사용자에게 알림 발송.

**(프로젝트 구조, 라이선스 등 기타 필요한 내용은 여기에 추가)**
