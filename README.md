# OLD-PJT 통합 서비스

## 개요
기존 OLD-PJT의 여러 프로젝트 기능을 하나의 서비스로 통합하여 관리 효율성과 확장성을 높인 프로젝트입니다. API 서비스와 봇 서비스로 구성되며, Docker 및 PostgreSQL을 기반으로 운영됩니다.

## 폴더 구조 (개선 제안 반영)
```
├── src/
│   ├── api/           # FastAPI 기반 API 서비스
│   │   ├── main.py      # FastAPI 앱 초기화, 스케줄러 설정
│   │   ├── models/      # SQLAlchemy DB 모델
│   │   ├── routers/     # API 엔드포인트별 라우터
│   │   ├── services/    # 핵심 비즈니스 로직
│   │   ├── schemas/     # Pydantic 데이터 검증 스키마
│   │   └── tests/       # API 서비스 테스트 코드
│   ├── bot/           # 텔레그램 챗봇 서비스
│   │   ├── main.py      # 텔레그램 봇 앱 초기화
│   │   ├── handlers/    # 챗봇 명령어/메시지 핸들러
│   │   └── tests/       # 봇 서비스 테스트 코드
│   └── common/        # 두 서비스가 공유하는 공통 모듈
│       ├── db_connector.py # DB 연결 및 세션 관리
│       ├── notify_service.py # 텔레그램 메시지 발송 서비스
│       ├── dart_utils.py   # DART API 연동 유틸리티
│       └── http_client.py  # (신규) 재시도 로직 포함 HTTP 클라이언트
├── db/
│   └── db_data/       # PostgreSQL 데이터 영속성 볼륨
├── scripts/           # 운영/관리용 쉘 스크립트
├── docs/              # 프로젝트 문서 (개발 계획, 요구사항 등)
├── logs/              # 서비스 운영 로그
├── .env.dev           # 개발 환경 변수 파일
├── settings.env.example # 환경 변수 예시
├── requirements.txt   # Python 의존성 목록
├── docker-compose.yml # Docker 서비스 통합 관리
└── README.md          # 프로젝트 개요 및 안내
```

## 설치 및 실행 방법
1. Python 3.x 설치
2. 가상환경 생성 및 활성화
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. 패키지 설치
   ```bash
   pip install -r requirements.txt
   ```
4. 환경 변수 설정
   - `settings.env.example` 파일을 복사해 `.env` 또는 `settings.env`로 사용하고 실제 값을 입력
   - `.env.dev` 파일을 프로젝트 루트에 아래와 같이 생성
     ```env
     DB_HOST=db
     DB_PORT=5432
     DB_USER=postgres
     DB_PASSWORD=postgres
     DB_NAME=service_db
     ```
   - 운영 환경은 .env.prod 등 별도 파일로 관리 가능
5. Docker 기반 통합 실행
   ```bash
   docker compose --env-file .env.dev up -d
   ```
   - 운영 환경은
     ```bash
     docker compose --env-file .env.prod up -d
     ```
   - 환경별로 env 파일만 바꿔주면 됩니다.

## 주요 서비스 및 명령어
- **API 서비스:** FastAPI 기반 RESTful 엔드포인트 제공
- **봇 서비스:** 텔레그램 챗봇 명령어 및 자연어 질의 지원
- **주요 챗봇 명령어:**
  - `/start`, `/help` : 명령어 안내
  - `/predict [종목코드]` : 예측 결과
  - `/watchlist_add [코드]`, `/watchlist_get`, `/watchlist_remove [코드]`
  - `/trade_simulate buy 005930 10000 10`, `/trade_history`
  - `/symbols`, `/symbols_search [키워드]`, `/symbol_info [코드]`
  - 자연어 질의: "삼성전자 얼마야", "005930 예측" 등

## 운영/배포/백업/문서화
- **운영 자동화:**
  - `scripts/service_control.sh start|stop|restart|status|logs` : 전체 서비스 일괄 관리
  - `scripts/backup_restore.sh backup` : DB 백업
  - `scripts/backup_restore.sh restore <백업파일명>` : DB 복구
- **장애/복구:**
  - DB 장애 시 `docker compose restart db` 또는 백업/복구 스크립트 활용
  - 주요 데이터는 PostgreSQL 컨테이너 볼륨에 저장됨
- **문서화:**
  - `docs/PLAN.MD`: 통합 개발/운영 계획 및 TODO
  - `docs/requirement.md`: 요구사항 명세
  - `docs/통합_미병합_기능_분석.md`: 미병합 기능 분석
  - `src/api/README.md`, `src/bot/README.md`: 각 서비스별 상세 구조/설계

## 기타
- 소스 버전 관리는 Git을 사용합니다.
- 각 서비스별 상세 구조 및 기능은 docs/PLAN.MD, docs/requirement.md를 참고하세요. 

## 테스트 실행 방법

### 1. 컨테이너 기반 전체 테스트 (권장)
- API/봇 서비스 모두 Docker 컨테이너에서 자동화 테스트 가능

```bash
# API 테스트 (컨테이너 내부)
docker compose --env-file .env.dev run --rm api pytest -v --disable-warnings --capture=no src/api/tests/

# 봇 테스트 (컨테이너 내부, 무한대기 방지 타임아웃 적용)
docker compose --env-file .env.dev run --rm bot pytest -v --disable-warnings --capture=no src/bot/tests/
```

### 2. 로컬 환경에서 직접 테스트
- 가상환경 활성화 후 아래 명령 실행

```bash
# API 테스트
PYTHONPATH=. pytest -v --disable-warnings src/api/tests/

# 봇 테스트 (환경변수 필요)
export TELEGRAM_BOT_TOKEN=dummy
export TELEGRAM_ADMIN_ID=dummy
PYTHONPATH=. pytest -v --disable-warnings src/bot/tests/
```

### 3. 테스트 관련 참고사항
- 봇 테스트는 무한대기(run_polling) 구조이므로, 타임아웃 및 예외처리로 자동화됨
- 실제 토큰이 없을 경우 InvalidToken 에러가 발생해도 정상 동작으로 간주
- 테스트 결과는 통과/실패 여부와 함께 AssertionError, Timeout 등으로 확인 가능 