# Email (SMTP) 설정 가이드

## 📧 Gmail SMTP 설정 방법

### 1. Gmail 앱 비밀번호 생성

1. Google 계정 설정으로 이동: https://myaccount.google.com/
2. "보안" 탭 선택
3. "2단계 인증" 활성화 (필수)
4. "앱 비밀번호" 생성
   - 앱 선택: "메일"
   - 기기 선택: "기타 (맞춤 이름)" → "StockEye" 입력
   - 생성된 16자리 비밀번호 복사

### 2. 환경 변수 설정

**`.env.development` 파일에 다음 내용 추가:**

```bash
# Email (SMTP) Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-digit-app-password
SMTP_USE_TLS=true
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=StockEye
```

**예시:**
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=stockeye.bot@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
SMTP_USE_TLS=true
SENDER_EMAIL=stockeye.bot@gmail.com
SENDER_NAME=StockEye
```

> **참고**: `.env.development` 파일은 개발 환경용입니다. 프로덕션 환경에서는 `.env.production` 파일을 사용하세요.

### 3. Docker 컨테이너 재시작

```bash
docker compose down
docker compose up -d
```

## 🧪 테스트 방법

### Python 코드로 테스트

```python
from src.common.services.notify_service import notification_service

# 이메일 전송 테스트
await notification_service.send_message(
    recipient="test@example.com",
    message="테스트 메시지입니다.",
    channel_name="email",
    subject="StockEye 테스트"
)
```

### 로그 확인

```bash
docker compose logs api | grep Email
docker compose logs worker | grep Email
```

## ⚠️ 주의사항

1. **앱 비밀번호 사용**: 일반 Gmail 비밀번호가 아닌 앱 비밀번호를 사용해야 합니다.
2. **2단계 인증 필수**: 앱 비밀번호 생성을 위해 2단계 인증이 활성화되어 있어야 합니다.
3. **발송 제한**: Gmail은 하루 500통의 이메일 발송 제한이 있습니다.
4. **보안**: `.env` 파일은 절대 Git에 커밋하지 마세요. (`.gitignore`에 포함되어 있음)

## 🔧 문제 해결

### "SMTP not configured" 로그가 나올 때
- `.env` 파일에 `SMTP_USERNAME`과 `SMTP_PASSWORD`가 설정되어 있는지 확인
- Docker 컨테이너를 재시작했는지 확인

### "Authentication failed" 에러
- 앱 비밀번호가 정확한지 확인 (공백 제거)
- 2단계 인증이 활성화되어 있는지 확인

### 이메일이 발송되지 않을 때
- 로그 확인: `docker compose logs api | grep -i email`
- SMTP 포트가 방화벽에서 차단되지 않았는지 확인
- Gmail 계정이 정지되지 않았는지 확인

## 📚 추가 정보

- Gmail SMTP 설정: https://support.google.com/mail/answer/7126229
- 앱 비밀번호 생성: https://support.google.com/accounts/answer/185833
