# System Manual (시스템 매뉴얼)

## 1. System Overview
- 전체 시스템 구조, 주요 서비스(API, Bot, DB), 데이터 흐름, 운영자 역할 등

## 2. Data Scheduler & Automation
### 2.1. 개요
- 종목마스터/일별시세 자동화 스케줄러 구조 및 흐름
- FastAPI 내장 APScheduler, 봇 명령어 통한 수동 트리거/스케줄 관리

### 2.2. 구조 및 흐름
- API 서버 내장 스케줄러: APScheduler로 주기적 잡 등록/관리
- 봇 명령어 → API 호출로 수동 갱신/스케줄 관리
- 잡 관리 및 확장: 봇 명령어로 즉시 실행, 스케줄 추가/삭제/상태조회 등

### 2.3. 운영/개발 가이드
- 스케줄러 연동, 관리자용 API 엔드포인트, 봇 명령어 연동, 운영 자동화/문서화
- 주요 운영/배포/복구 절차는 아래 Maintenance & Recovery 참고

## 3. Logging & Monitoring
- API/Bot 모두 표준 logging 모듈 사용, stdout+파일(logs/app.log, logs/bot.log) 기록
- 도커 볼륨 마운트로 host에서 직접 로그 확인 가능
- 로그 파일 회전(RotatingFileHandler), 운영 중 로그 모니터링 방법

## 4. Maintenance & Recovery
### 4.1. DB 초기화/마이그레이션
- DB 볼륨/폴더 삭제, 마이그레이션, Alembic 등
- DB 백업/복구, 데이터 마이그레이션 절차

### 4.2. 운영 자동화/배포/복구
- 컨테이너 재기동, 이미지 재빌드, 운영 체크리스트
- 장애 발생 시 로그/DB/백업본 우선 확인

### 4.3. 기타 유지보수
- 서비스별 환경변수 관리, 운영/개발 환경 분리, 보안/권한 관리 등

## 5. Admin/Bot Integration
- 텔레그램 봇 명령어로 API 서버 관리(스케줄/즉시실행/상태조회 등)
- 관리자 인증/권한 체크, 봇-API 연동 구조

## 6. Security & Access Control
- JWT 인증, 관리자 권한, 환경변수 보안, DB 접근 제어 등

## 7. 참고 및 기타
- 각 기능별 상세/테스트/운영/장애 대응은 features_analysis.md, TODO.md, FAQ.md 참고 

# Alembic 기반 DB 마이그레이션 운영 매뉴얼 (현재 미사용)

> ⚠️ 현재 프로젝트에서는 Alembic 기반 자동 마이그레이션을 사용하지 않습니다. DB 스키마 변경 및 관리, 초기화는 수동으로 진행합니다.

## 1. Alembic 관련 기록 (참고용)
- Alembic 환경 설정, 마이그레이션 생성/적용, 문제 해결법 등은 과거 기록으로 남겨둡니다.
- 필요시 `alembic.ini`, `migrations/` 폴더를 복구하여 사용할 수 있습니다.

## 2. 현재 DB 스키마/마이그레이션 관리 방식
- DB 테이블/컬럼 추가, 변경, 삭제는 **직접 SQL 또는 ORM 모델 변경 후 수동 반영**
- 컨테이너 내에서 psql 등으로 직접 테이블 생성/수정
- 스키마 변경 시 반드시 전체 테스트를 수행하여 영향성 검증

## 3. 향후 Alembic 재도입 시 참고사항
- alembic.ini의 DB 주소, PYTHONPATH, 모델 import 등 환경설정에 주의
- 마이그레이션 파일 생성/적용 시 DB와 모델 상태 일치 필요

---

## 8. 운영 서버 서비스 기동 절차 (dev_ops.sh 활용)

이 절차는 `dev_ops.sh` 스크립트를 활용하여 StockEye 서비스를 운영 서버에 배포하고 기동하는 방법을 설명합니다.

#### 1. 사전 준비 (운영 서버)

*   **Git 설치**: 소스 코드 관리를 위해 Git이 설치되어 있어야 합니다.
*   **Docker 및 Docker Compose 설치**: 컨테이너 기반 서비스 배포를 위해 Docker와 Docker Compose가 설치되어 있어야 합니다.
    *   Docker 설치: `sudo apt-get update && sudo apt-get install docker-ce docker-ce-cli containerd.io`
    *   Docker Compose 설치: `sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose` (최신 안정 버전 확인 후 조정)

#### 2. 소스 코드 클론

운영 서버의 적절한 디렉토리(예: `/opt/StockEye`)에 Git 저장소를 클론합니다.

```bash
cd /opt
git clone https://github.com/lkhkhk/StockEye.git
cd StockEye
```

#### 3. 환경 변수 파일 생성 및 설정

`docker-compose.yml`은 `APP_ENV` 환경 변수에 따라 `.env.production` 파일을 로드합니다. 운영 환경에 맞는 `.env.production` 파일을 생성하고 필요한 환경 변수를 설정합니다.

```bash
# .env.production 파일 생성 (settings.env.example을 참고)
cp settings.env.example .env.production
```

`.env.production` 파일의 주요 설정 항목:

*   `TELEGRAM_ADMIN_ID=YOUR_TELEGRAM_ADMIN_ID`
*   `DART_API_KEY=YOUR_DART_API_KEY`
*   `JWT_SECRET_KEY=YOUR_JWT_SECRET_KEY` (강력하고 긴 문자열 사용)
*   `DB_HOST=db` (Docker Compose 내부 네트워크에서 DB 서비스 이름)
*   `DB_USER=stocks_user` (PostgreSQL 사용자명)
*   `DB_PASSWORD=stocks_password` (PostgreSQL 비밀번호)
*   `DB_NAME=stocks_db` (PostgreSQL 데이터베이스명)
*   `DB_PORT=5432` (PostgreSQL 포트)

**주의**: `DB_HOST`는 Docker Compose 내부 네트워크에서 서비스 이름인 `db`로 설정해야 합니다.

#### 4. 서비스 빌드 및 기동 (`dev_ops.sh` 활용)

`dev_ops.sh` 스크립트의 `build` 명령을 `production` 환경으로 지정하여 실행합니다.

```bash
./dev_ops.sh build production
```

*   `production`: `dev_ops.sh` 스크립트에게 `build_and_restart` 함수를 `production` 환경으로 실행하도록 지시합니다.

#### 5. 데이터베이스 초기화 및 마이그레이션 (최초 배포 시)

StockEye 서비스는 API 서비스 기동 시 SQLAlchemy 모델을 기반으로 테이블을 자동으로 생성합니다. 따라서 별도의 수동 마이그레이션 명령은 필요하지 않습니다.

#### 6. 서비스 상태 확인

서비스가 정상적으로 기동되었는지 확인합니다.

*   **컨테이너 상태 확인**:
    ```bash
    docker compose ps
    ```
    `db` 서비스의 컨테이너 이름은 `postgres_db`로 표시되지만, `STATUS`가 `Up` 상태여야 합니다. `postgres_db` 컨테이너는 `(healthy)` 상태여야 합니다.

*   **서비스 로그 확인**:
    ```bash
    docker compose logs api
    docker compose logs bot
    docker compose logs db # DB 서비스 로그 확인 시에도 서비스 이름 'db' 사용
    ```
    로그를 통해 오류 메시지가 없는지 확인합니다.

*   **API 헬스 체크 (선택 사항)**:
    ```bash
    curl http://localhost:8000/health
    ```
    API 서비스가 정상적으로 응답하는지 확인합니다.

#### 7. 서비스 업데이트 (향후 변경사항 배포 시)

소스 코드 변경사항이 있을 경우, 다음 절차로 업데이트합니다.

```bash
cd /opt/StockEye
git pull origin main # 또는 develop 등 작업 브랜치
./dev_ops.sh build production
```

#### 8. 문제 해결 및 디버깅

*   **로그 확인**: 문제가 발생하면 가장 먼저 `docker compose logs <service_name>` 명령으로 해당 서비스의 로그를 확인합니다.
*   **컨테이너 내부 접속**: `docker compose exec <service_name> bash` 명령으로 컨테이너 내부에 접속하여 직접 디버깅할 수 있습니다. (여기서 `<service_name>`은 `api`, `bot`, `db`와 같은 서비스 이름입니다.)
*   **환경 정리**: `APP_ENV=production ./dev_ops.sh clean` 명령은 모든 Docker 컨테이너, 네트워크, 볼륨을 삭제합니다. **운영 환경에서는 데이터 손실 위험이 매우 크므로, 이 명령은 극히 주의하여 사용해야 합니다.**

# FAQ (2025-07-21 기준)
- Q: Alembic 마이그레이션을 다시 사용하려면?
  - A: alembic.ini, migrations 폴더를 복구 후 환경설정 및 마이그레이션 생성/적용 절차를 따르면 됩니다.
- Q: DB 스키마 변경 후 반드시 해야 할 일은?
  - A: 전체 테스트를 실행하여 모든 기능이 정상 동작하는지 검증해야 합니다. 