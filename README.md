# OLD-PJT 통합 서비스

## 개요
기존 OLD-PJT의 여러 프로젝트 기능을 하나의 서비스로 통합하여 관리 효율성과 확장성을 높인 프로젝트입니다. API 서비스와 봇 서비스로 구성되며, Docker 및 PostgreSQL을 기반으로 운영됩니다.

## 폴더 구조
```
├── OLD-PJT/           # 기존 프로젝트 소스 (현상태 유지)
├── venv/              # Python 가상환경
├── requirement.md     # 요구사항 명세
├── PLAN.MD            # 개발 계획 및 TODO 리스트
└── README.md          # 프로젝트 개요 및 문서
```

## 설치 방법
1. Python 3.x 설치
2. 가상환경 생성 및 활성화
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. (추후) 필요한 패키지 설치
   ```bash
   pip install -r requirements.txt
   ```

## 사용 방법
- 개발 및 실행 방법, API/봇 서비스 실행법 등은 추후 문서화 예정입니다.

## 운영/배포 자동화 및 실서비스 가이드

### Docker 기반 통합 운영
- `docker compose up -d` : 전체 서비스(API/DB/봇) 일괄 기동
- `docker compose down` : 전체 서비스 중지
- 신규 파일 추가/구조 변경 시 반드시 이미지 삭제 후 재빌드 필요
  ```bash
  docker compose down
  docker images | grep stockscursor | awk '{print $3}' | xargs -r docker rmi -f
  docker compose build --no-cache
  docker compose up -d
  ```

### 환경변수 관리
- `.env` 파일에 DB, 텔레그램 토큰 등 주요 환경변수 관리
- 예시:
  ```env
  DB_HOST=postgres_db
  DB_PORT=5432
  DB_USER=postgres
  DB_PASSWORD=postgres
  DB_NAME=service_db
  TELEGRAM_BOT_TOKEN=xxx
  ```

### 주요 챗봇 명령어
- `/start`, `/help` : 명령어 안내
- `/predict [종목코드]` : 예측 결과
- `/watchlist_add [코드]`, `/watchlist_get`, `/watchlist_remove [코드]`
- `/trade_simulate buy 005930 10000 10`, `/trade_history`
- `/symbols`, `/symbols_search [키워드]`, `/symbol_info [코드]`
- 자연어 질의: "삼성전자 얼마야", "005930 예측" 등

### 장애/복구/백업
- DB 장애 시 `docker compose restart db` 또는 백업/복구 스크립트 활용
- 주요 데이터는 PostgreSQL 컨테이너 볼륨에 저장됨
- 운영 중 장애 발생 시 PLAN.MD, README, 로그 참고

### 문서화/운영 가이드
- PLAN.MD: 통합 개발/운영 계획 및 TODO
- src/api/README.md, src/bot/README.md: 각 서비스별 상세 구조/설계
- requirements.txt: 전체 의존성 관리

### 운영 자동화 스크립트
- `scripts/service_control.sh start|stop|restart|status|logs` : 전체 서비스 일괄 관리
- `scripts/backup_restore.sh backup` : DB 백업
- `scripts/backup_restore.sh restore <백업파일명>` : DB 복구

---

## 기타
- 소스 버전 관리는 Git을 사용합니다.
- 각 서비스별 상세 구조 및 기능은 PLAN.MD와 requirement.md를 참고하세요. 