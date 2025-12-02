# StockEye 문서 인덱스

이 문서는 StockEye 프로젝트의 모든 문서를 체계적으로 안내합니다.

## 📚 문서 구조

```
docs/
├── README.md (이 파일)
├── 주요 문서 (1-6)
├── guides/ (가이드 문서)
├── features/ (기능 제안서)
├── archive/ (아카이브)
└── worklogs/ (작업 로그)
```

---

## 📖 주요 문서

프로젝트의 핵심 문서들입니다. 번호 순서대로 읽으시면 프로젝트를 이해하는 데 도움이 됩니다.

1. **[프로젝트 개요](./1_Project_Overview.md)**
   - 프로젝트 목표, 시스템 아키텍처, 핵심 기능 명세
   - MSA 구조, 서비스 간 통신 방식

2. **[시작하기](./2_Getting_Started.md)**
   - 개발 환경 설정
   - Docker Compose를 이용한 설치 및 실행 방법

3. **[사용자 가이드](./3_User_Guide.md)**
   - 텔레그램 봇 명령어 및 사용법
   - 주요 기능 사용 방법

4. **[개발자 가이드](./4_Developer_Guide.md)**
   - 개발 철학 및 코드 컨벤션
   - Git 브랜치 구조 및 워크플로우
   - API/Bot/Common 모듈 테스트 작성 가이드
   - Bot-API 간 인증 흐름

5. **[운영 가이드](./5_Operations_Guide.md)**
   - 서버 배포 절차
   - 백업 및 복구
   - 모니터링 및 로그 관리

6. **[문제 해결 가이드](./6_Troubleshooting.md)**
   - 자주 발생하는 문제와 해결 방법
   - 디버깅 팁

### 특수 목적 문서

- **[이메일 설정 가이드](./EMAIL_SETUP.md)**
  - Gmail SMTP를 이용한 이메일 알림 설정 방법

---

## 🛠️ 가이드 문서 (guides/)

개발 및 운영에 필요한 특수 가이드 문서들입니다.

- **[Gemini Code Assist 워크플로우](./guides/gemini-code-assist.md)**
  - Gemini AI 에이전트의 작업 흐름도

- **[작업 시작 가이드](./guides/start_work.md)**
  - 새로운 작업을 시작할 때 참고할 가이드

- **[Docker 설치 및 설정](./guides/docker_guide.md)**
  - Docker 설치 및 권한 설정 방법

- **[테스트 코드 작성 가이드](./guides/testing_guide.md)**
  - API/Bot/Common 모듈의 테스트 작성 표준 가이드라인
  - Given-When-Then 패턴, Mock 사용법

- **[httpx Mocking 가이드](./guides/mocking_guide.md)**
  - pytest와 unittest.mock을 이용한 httpx 비동기 클라이언트 Mocking 방법

---

## 🚀 기능 제안서 (features/)

향후 구현 예정이거나 검토 중인 기능들의 설계 문서입니다.

- **[아키텍처 개선 제안](./features/architecture_improvement_proposal.md)**
- **[예측 플로우 개선](./features/enhanced_prediction_flow.md)**
- **[실시간 공시 알림](./features/realtime_disclosure_notice.md)**
- **[알림 시스템 리팩토링](./features/refactor_alert_system.md)**

---

## 📦 아카이브 (archive/)

과거 문서, 분석 보고서, 완료된 작업 관련 문서들입니다.

### AI 대화 메모
- `AI-대화메모(cursor).md`
- `AI-대화메모(gemini).md`

### 분석 및 보고서
- `CURRENT_WORK_SUMMARY.md` - 작업 요약
- `features_analysis.md` - 기능 분석
- `TESTING_ANALYSIS.md` - 테스트 분석
- `Resource_Optimization_Analysis.md` - 리소스 최적화 분석
- `Test_Analysis_Report.md` - 테스트 분석 보고서
- `통합_미병합_기능_분석.md` - 미병합 기능 분석

### 시스템 문서
- `FAQ.md` - 자주 묻는 질문
- `SystemManual.md` - 시스템 매뉴얼
- `maintenance.md` - 유지보수 가이드
- `requirement.md` - 요구사항 명세

### 아키텍처 문서
- `notification_system_architecture.md` - 알림 시스템 아키텍처
- `stock_data_scheduler.md` - 주식 데이터 스케줄러

### 리팩토링 계획
- `refactor_user_service.md` - 사용자 서비스 리팩토링

---

## 📝 작업 로그 (worklogs/)

날짜별 작업 진행 상황을 기록한 문서들입니다.

- `2025-07.md` ~ `2025-12-02.md`
- 각 날짜별로 완료된 작업, 테스트 결과, 다음 작업 계획 등을 기록

---

## 🔗 관련 링크

- [프로젝트 루트 README](../README.md)
- [TODO 리스트](../TODO.md)
- [완료된 작업 아카이브](../DONE.md)
- [Gemini CLI Agent 지침서](../GEMINI.md)
