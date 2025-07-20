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
- 각 기능별 상세/테스트/운영/장애 대응은 features_analysis.md, PLAN.md, FAQ.md 참고 

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

# FAQ (2025-07-21 기준)
- Q: Alembic 마이그레이션을 다시 사용하려면?
  - A: alembic.ini, migrations 폴더를 복구 후 환경설정 및 마이그레이션 생성/적용 절차를 따르면 됩니다.
- Q: DB 스키마 변경 후 반드시 해야 할 일은?
  - A: 전체 테스트를 실행하여 모든 기능이 정상 동작하는지 검증해야 합니다. 