# 시작하기

이 문서는 StockEye 프로젝트의 개발 환경을 설정하고 서비스를 실행하는 방법을 안내합니다.

## 1. 요구사항

- Python 3.10 이상
- Docker 및 Docker Compose
- Git

## 2. 설치 및 실행

### 2.1. 소스 코드 복제

```bash
git clone https://github.com/lkhkhk/StockEye.git
cd StockEye
```

### 2.2. Python 가상환경 설정

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2.3. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

### 2.4. 환경 변수 설정

프로젝트는 `APP_ENV` 환경 변수(`development` 또는 `production`)에 따라 다른 `.env` 파일을 로드합니다. `settings.env.example` 파일을 복사하여 환경에 맞는 `.env` 파일을 생성하고 필요한 값을 채워주세요.

**개발 환경:**
```bash
cp settings.env.example .env.development
```

**운영 환경:**
```bash
cp settings.env.example .env.production
```

생성된 `.env.*` 파일 내에 아래와 같이 실제 값들을 입력해야 합니다.
- `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰
- `TELEGRAM_ADMIN_ID`: 텔레그램 관리자 사용자 ID
- `DART_API_KEY`: DART API 키
- `JWT_SECRET_KEY`: JWT 서명에 사용할 비밀 키 (복잡한 문자열 권장)
- `DB_USER`, `DB_PASSWORD`, `DB_NAME`: PostgreSQL 접속 정보

### 2.5. Docker를 이용한 서비스 실행

`stockeye.sh` 스크립트를 사용하여 모든 서비스를 한 번에 빌드하고 실행할 수 있습니다.

**개발 환경으로 실행 (기본값):**
```bash
./stockeye.sh build
# 또는
./stockeye.sh build development
```

**운영 환경으로 실행:**
```bash
./stockeye.sh build production
```

스크립트를 사용하지 않고 직접 `docker compose` 명령을 사용할 수도 있습니다.

```bash
# 개발 환경
APP_ENV=development docker compose up -d --build

# 운영 환경
APP_ENV=production docker compose up -d --build
```

## 3. 서비스 상태 확인

```bash
# 모든 서비스 컨테이너 상태 확인
docker compose ps

# 특정 서비스 로그 확인 (api, bot, db)
docker compose logs api
```
