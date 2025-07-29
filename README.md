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
├── .env.development   # 개발 환경 변수 파일 (APP_ENV=development)
├── .env.production    # 운영 환경 변수 파일 (APP_ENV=production)
├── settings.env.example # 환경 변수 예시 (템플릿)
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
   - `settings.env.example` 파일을 복사하여 `.env.development` 또는 `.env.production`으로 사용하고 실제 값을 입력하세요.
   - `APP_ENV` 변수를 `development` 또는 `production`으로 설정하여 환경을 구분합니다.

5. Docker 기반 통합 실행
   - `dev_ops.sh` 스크립트를 사용하여 빌드 및 실행할 수 있습니다.
   ```bash
   # 개발 환경으로 빌드 및 실행 (기본값)
   ./dev_ops.sh build

   # 또는 명시적으로 개발 환경 지정
   ./dev_ops.sh build development

   # 운영 환경으로 빌드 및 실행
   ./dev_ops.sh build production
   ```

   (참고: `docker compose up -d` 명령어를 직접 사용하는 경우, `APP_ENV` 환경 변수를 설정해야 합니다.)
   ```bash
   # 개발 환경으로 실행 (기본값)
   docker compose up -d

   # 또는 명시적으로 개발 환경 지정
   APP_ENV=development docker compose up -d

   # 운영 환경으로 실행
   APP_ENV=production docker compose up -d
   ```

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

### 1. 스크립트를 이용한 컨테이너 기반 전체 테스트 (권장)
- `dev_ops.sh` 스크립트를 사용하여 API/봇 서비스의 테스트를 실행할 수 있습니다.

```bash
# API 테스트
./dev_ops.sh api-test

# 봇 테스트
./dev_ops.sh bot-test

# 모든 테스트 실행
./dev_ops.sh all-test
```

### 2. 로컬 환경에서 직접 테스트
- 가상환경 활성화 후 아래 명령 실행
- 로컬 환경 테스트 시에도 `APP_ENV` 환경 변수를 설정해야 합니다.

```bash
# API 테스트
APP_ENV=development PYTHONPATH=. pytest -v --disable-warnings src/api/tests/

# 봇 테스트
APP_ENV=development PYTHONPATH=. pytest -v --disable-warnings src/bot/tests/
```

### 3. 테스트 관련 참고사항
- 봇 테스트는 무한대기(run_polling) 구조이므로, 타임아웃 및 예외처리로 자동화됨
- 실제 토큰이 없을 경우 InvalidToken 에러가 발생해도 정상 동작으로 간주
- 테스트 결과는 통과/실패 여부와 함께 AssertionError, Timeout 등으로 확인 가능 