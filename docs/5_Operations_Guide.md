# 운영 가이드

이 문서는 StockEye 서비스의 배포, 운영, 유지보수에 필요한 절차와 가이드를 제공합니다.

## 1. 배포 (Deployment)

### 1.1. 최초 배포

1.  **서버 준비:** Git, Docker, Docker Compose가 설치된 서버를 준비합니다.
2.  **소스 코드 복제:** `git clone`으로 소스 코드를 내려받습니다.
3.  **운영 환경변수 설정:** `settings.env.example` 파일을 복사하여 `.env.production` 파일을 생성하고, 운영에 필요한 실제 값(DB 정보, API 키, 토큰 등)을 입력합니다.
4.  **서비스 빌드 및 기동:** `dev_ops.sh` 스크립트를 사용하여 운영 환경으로 서비스를 빌드하고 시작합니다.
    ```bash
    ./dev_ops.sh build production
    ```
5.  **상태 확인:** `docker compose ps`로 모든 컨테이너가 `Up` 상태인지, `docker compose logs -f api bot`으로 서비스 로그에 오류가 없는지 확인합니다.

### 1.2. 업데이트 배포

1.  **최신 소스 반영:** `git pull`로 최신 소스 코드를 받습니다.
2.  **서비스 재빌드 및 재시작:** `dev_ops.sh` 스크립트를 사용하여 서비스를 다시 빌드하고 재시작합니다.
    ```bash
    ./dev_ops.sh build production
    ```

## 2. 백업 및 복구

`scripts/backup_restore.sh` 스크립트를 사용하여 데이터베이스를 백업하고 복구할 수 있습니다.

### 2.1. 백업

- `db/backups/` 디렉토리에 `stocks_db_YYYY-MM-DD_HH-MM-SS.sql.gz` 형식으로 압축된 백업 파일이 생성됩니다.

```bash
./scripts/backup_restore.sh backup
```

### 2.2. 복구

- 복구할 백업 파일명을 인자로 전달합니다. 파일은 `db/backups/` 디렉토리에 위치해야 합니다.

```bash
./scripts/backup_restore.sh restore stocks_db_2025-08-01_12-00-00.sql.gz
```

## 3. 로깅 및 모니터링

- **로그 확인:** 각 서비스의 로그는 `docker compose logs` 명령을 통해 실시간으로 확인할 수 있습니다. 로그 파일은 `logs/` 디렉토리에도 기록됩니다.
  ```bash
  # API 서비스 로그 실시간 확인
  docker compose logs -f api

  # Bot 서비스 로그 실시간 확인
  docker compose logs -f bot
  ```
- **스케줄러 동작 확인:** `api` 서비스 로그에서 `APScheduler` 관련 로그를 필터링하여 백그라운드 작업이 정상적으로 실행되는지 확인할 수 있습니다.
  ```bash
  docker compose logs api | grep APScheduler
  ```

## 4. 트러블슈팅

- **서비스가 시작되지 않을 때:**
  - `docker compose logs`로 특정 서비스의 로그를 확인하여 오류의 원인을 파악합니다. (DB 연결 정보, 환경 변수 설정 등)
- **텔레그램 알림이 오지 않을 때:**
  - `api` 서비스의 동기 코드(스케줄러 등)에서 `python-telegram-bot`의 비동기 함수를 `asyncio.run()`으로 올바르게 호출했는지 확인합니다. (`src/common/notify_service.py` 참고)
- **컨테이너 내부 접속:**
  - `docker compose exec <service_name> bash` 명령으로 컨테이너 내부에 직접 접속하여 문제를 진단할 수 있습니다. (e.g., `docker compose exec api bash`)
