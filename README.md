# StockEye (주시봇) 👁️

실시간 주식 공시 정보를 모니터링하고 텔레그램으로 알림을 보내주는 봇입니다.

## 주요 기능

*   DART(금융감독원 전자공시시스템) API를 이용한 실시간 공시 정보 확인
*   사용자별 관심 종목 등록, 삭제, 조회 (텔레그램 봇 인터페이스)
*   새로운 공시 발생 시 또는 공시 부재 시 텔레그램 알림
*   Docker 기반 실행 환경 제공
*   Prometheus 메트릭 노출 (기본 포트 8000)

## 프로젝트 구조

```
/StockEye
├── app/                  # 애플리케이션 소스 코드
│   ├── core/             # 핵심 모듈 (설정, DB, 로깅)
│   ├── models/           # 데이터 모델 (Pydantic)
│   ├── services/         # 비즈니스 로직 (공시, 텔레그램)
│   ├── __init__.py
│   └── __main__.py       # 애플리케이션 진입점
├── docker/               # Docker 관련 파일
│   └── Dockerfile
├── db_data/              # Docker 볼륨 마운트 (DB, Redis 데이터 저장 - .gitignore 처리됨)
│   ├── postgres/
│   └── redis/
├── tests/                # 테스트 코드
│   ├── __init__.py
│   ├── test_disclosure.py
│   └── test_telegram.py
├── .env                  # 환경 변수 설정 파일 (Git 무시됨)
├── .gitignore            # Git 무시 목록
├── .venv/                # Python 가상 환경 (Git 무시됨)
├── docker-compose.yml    # Docker Compose 설정 파일
├── requirements.txt      # Python 의존성 목록
└── README.md             # 프로젝트 설명 파일
```

## 설치 및 설정

**사전 요구 사항:**

*   Python 3.11 이상
*   Docker 및 Docker Compose
*   PostgreSQL 클라이언트 (선택 사항 - 직접 DB 접속 확인용)
*   Redis 클라이언트 (선택 사항 - 직접 Redis 확인용)

**설치 단계:**

1.  **저장소 복제:**
    ```bash
    git clone https://github.com/lkhkhk/stockeye.git
    cd StockEye
    ```
2.  **가상 환경 생성 및 활성화:**
    ```bash
    python -m venv .venv
    # Windows
    .\.venv\Scripts\activate
    # Linux/macOS
    # source .venv/bin/activate
    ```
3.  **의존성 설치:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **환경 변수 설정 (`.env` 파일 생성):**
    프로젝트 루트 디렉토리 (`StockEye/`)에 `.env` 파일을 생성하고 아래 내용을 참고하여 실제 값으로 채웁니다.
    ```dotenv
    # PostgreSQL 연결 정보
    #   Docker 실행 시 서비스 이름
    DB_HOST=stockeye_postgres
    #   로컬 실행 시  
    # DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=stockeye
    DB_USER=stockeye
    # 실제 비밀번호로 변경
    DB_PASSWORD=your_secret_db_password

    # Redis 연결 정보
    #   Docker 실행 시 서비스 이름
    REDIS_HOST=stockeye_redis
    #   로컬 실행 시
    # REDIS_HOST=localhost
    REDIS_PORT=6379

    # API 키 및 토큰
    DART_API_KEY=your_dart_api_key       # 실제 DART API 키로 변경
    TELEGRAM_BOT_TOKEN=your_telegram_bot_token # 실제 봇 토큰으로 변경

    # 테스트 변수 (선택 사항)
    TEST_VAR=it_works
    ```
    **주의:** `.env` 파일은 민감 정보를 포함하므로 `.gitignore`에 반드시 추가하여 Git 저장소에 올라가지 않도록 합니다.

5.  **로컬 데이터 디렉토리 생성 (Docker 사용 시):**
    Docker 볼륨 마운트를 위해 프로젝트 루트에 디렉토리를 생성합니다.
    ```bash
    mkdir db_data
    mkdir db_data\postgres # Windows
    mkdir db_data\redis   # Windows
    # mkdir -p db_data/postgres db_data/redis # Linux/macOS
    ```

## 서비스 실행

**1. Docker Compose 사용 (권장):**

*   **빌드 및 백그라운드 실행:**
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
*   **서비스 중지 (컨테이너 유지):**
    ```bash
    docker-compose stop
    ```

**2. 로컬 직접 실행 (DB 및 Redis 서버 별도 실행 필요):**

    **주의:** 이 방법은 로컬 컴퓨터에 PostgreSQL과 Redis 서버가 설치 및 실행 중이어야 합니다. `.env` 파일의 `DB_HOST`와 `REDIS_HOST`를 `localhost` 또는 실제 서버 주소로 변경해야 합니다.

*   **애플리케이션 실행:**
    ```bash
    # 가상 환경 활성화 확인
    python -m app
    ```
*   **종료:** 터미널에서 `Ctrl+C`를 누릅니다.

## 테스트 실행

1.  **테스트 환경 설정:** 개발 의존성이 설치되어 있는지 확인합니다. (`requirements.txt`에 포함됨)
2.  **테스트 실행:** 프로젝트 루트 디렉토리에서 다음 명령어를 실행합니다.
    ```bash
    pytest
    ```

## 서비스 사용법 (텔레그램 봇 명령어)

봇과 대화하여 다음 명령어들을 사용할 수 있습니다.

*   `/start` : 봇 시작 및 환영 메시지 표시
*   `/help` : 사용 가능한 명령어 및 도움말 보기
*   `/register` : 봇 사용을 위한 사용자 등록 시작 (간단한 인증 필요)
*   `/add` : 모니터링할 주식 추가 시작 (예: `005930 삼성전자` 형식으로 입력)
*   `/remove` : 모니터링 중인 주식 목록을 버튼으로 보여주고 선택하여 삭제
*   `/list` : 현재 모니터링 중인 주식 목록 보기
*   `/cancel` : 진행 중인 작업(등록, 추가 등) 취소

## Git 사용 가이드

*   **브랜치 전략:**
    *   `main` (또는 `master`): 안정적인 프로덕션 릴리즈 브랜치
    *   `develop`: 개발 진행 및 다음 릴리즈 준비 브랜치
    *   `feature/이슈번호-기능명`: 새로운 기능 개발 브랜치 (예: `feature/12-add-stock-validation`)
    *   `fix/이슈번호-버그명`: 버그 수정 브랜치
*   **커밋 컨벤션:** [Conventional Commits](https://www.conventionalcommits.org/) 규칙 사용 권장 (예: `feat: Add user registration feature`, `fix: Correct database connection error`)
*   **`.gitignore`:** `.venv/`, `__pycache__/`, `*.pyc`, `*.log`, `db_data/`, `.env`, `.pytest_cache/` 등 불필요하거나 민감한 파일/폴더를 Git 추적에서 제외합니다.
