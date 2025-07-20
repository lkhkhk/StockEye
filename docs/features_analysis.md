# Features Analysis (통합/미병합/매핑 상세)

## 1. 프로젝트별 주요 기능 세부 목록
| 프로젝트 | 세부 기능 | 통합/병합 현황 | 통합된 기능(타 프로젝트) | 미병합/미구현 사유 | 관련 테스트 | PLAN.md TODO 매핑 |
|-----------|----------------------|----------------|----------------------|------------------|--------------|-------------------|
| StockEye  | 실시간 공시 알림 | 미구현(대상) | - | 미구현, 추후 구현 필요 | - | 실시간 공시 알림 구현 |
| StockEye  | 주식 모니터링 | 유사기능 타 프로젝트로 통합 | LetsGetRich_1(가격 알림) | 가격 알림/모니터링으로 통합 | test_api_alerts.py | 가격 알림 고도화 |
| StockEye  | 사용자/관리자 관리 | 병합 | StockBuySell(사용자), LetsGetRich_1(관리자) | 통합 | test_api_user.py | 사용자 관리 고도화 |
| StockEye  | 공시 이력/수동 갱신 | 미구현(대상) | - | 미구현, 추후 구현 필요 | - | 공시 이력/수동 갱신 구현 |
| StockEye  | Prometheus 모니터링 | 대상 아님 | - | 외부 모니터링, 통합 필요성 낮음 | - | - |
| StockBuySell | 종목별 예측 | 병합 | LetsGetRich(예측), LetsGetRich_1(예측) | 통합 | test_api_predict.py | 예측 기능 고도화 |
| StockBuySell | 관심종목 | 병합 | LetsGetRich_1(포트폴리오) | 통합 | test_api_watchlist.py | 관심종목 관리 개선 |
| StockBuySell | 모의매매/수익률 | 병합 | LetsGetRich_1(모의매매) | 통합 | test_api_simulated_trade.py | 모의매매/통계 고도화 |
| StockBuySell | 데이터 수집/저장/크롤링 | 미구현(대상) | - | 미구현, 추후 구현 필요 | - | 데이터 수집/크롤링 구현 |
| LetsGetRich_1 | 가격 알림 | 병합 | StockEye(모니터링) | 통합 | test_api_alerts.py | 가격 알림 고도화 |
| LetsGetRich_1 | 알림 히스토리 | 병합 | - | 통합 | test_api_alerts.py | 알림 이력 관리 |
| LetsGetRich_1 | 포트폴리오/매매/수익률/통계 | 병합 | StockBuySell(모의매매) | 통합 | test_api_simulated_trade.py | 포트폴리오/통계 고도화 |
| LetsGetRich_1 | 뉴스/공시/그래프 | 유사기능 타 프로젝트로 통합 | LetsGetRich(뉴스) | 뉴스/공시 통합 | test_api_prediction_history.py | 뉴스/공시 통합 관리 |
| LetsGetRich | 주식 뉴스 요약/검색 | 병합 | LetsGetRich_1(뉴스) | 통합 | test_api_prediction_history.py | 뉴스 요약/검색 고도화 |
| LetsGetRich | 주가 예측 | 병합 | StockBuySell(예측) | 통합 | test_api_predict.py | 예측 기능 고도화 |
| LetsGetRich | 챗봇 인터페이스 | 대상 아님 | - | 별도 챗봇, 통합 필요성 낮음 | - | - |

## 2. 기능별 상세/관계/과제/매핑
| 기능 | 상세 설명 | 병합 현황 | 통합/미병합/미구현 사유 | PLAN.md TODO 매핑 | 관련 테스트 |
|-------|----------------|-----------|------------------|-------------------|--------------|
| 가격 알림 | 가격 조건 충족 시 텔레그램 알림 | 병합 | StockEye, LetsGetRich_1 통합 | 가격 알림 고도화 | test_api_alerts.py |
| 종목마스터/시세 갱신 | APScheduler+API+Bot 연동 | 병합 | 통합 | 스케줄 관리 UI, 장애 대응 자동화 | test_admin_scheduler.py |
| 모의매매/수익률 | 매수/매도/수익률/통계 | 병합 | StockBuySell, LetsGetRich_1 통합 | 실거래 연동, 통계 고도화 | test_api_simulated_trade.py |
| 예측/뉴스/챗봇 | 주가 예측, 뉴스 요약, 챗봇 | 일부 병합 | LetsGetRich, StockBuySell 통합, 챗봇은 미구현(대상) | 자연어 처리 고도화, 챗봇 구현 | test_api_predict.py |
| 사용자/관리자 관리 | 회원가입/로그인/권한 | 병합 | StockEye, StockBuySell 통합 | 사용자 관리 고도화 | test_api_user.py |
| 알림 이력 | 알림 내역 저장/조회 | 병합 | LetsGetRich_1 통합 | 알림 이력 관리 | test_api_alerts.py |
| 포트폴리오/관심종목 | 관심종목/포트폴리오 관리 | 병합 | StockBuySell, LetsGetRich_1 통합 | 관심종목 관리 개선 | test_api_watchlist.py |
| 뉴스/공시 | 뉴스/공시 통합 | 일부 병합 | LetsGetRich, LetsGetRich_1 통합 | 뉴스/공시 통합 관리 | test_api_prediction_history.py |
| 외부 모니터링 | Prometheus 등 | 대상 아님 | 외부 연동, 통합 필요성 낮음 | - | - |
| 데이터 수집/크롤링 | 외부 데이터 | 미구현(대상) | 미구현, 추후 구현 필요 | 데이터 수집/크롤링 구현 | - |
| 챗봇 | 별도 챗봇 | 미구현(대상) | 미구현, 추후 구현 필요 | 챗봇 구현 | - |

## 3. 병합/미병합/미구현/통합대상/타 프로젝트 기능 매핑 요약
- **병합:** 가격 알림, 종목마스터/시세, 모의매매, 예측, 통계, 사용자/관리자, 알림 이력, 포트폴리오 등
- **미구현(대상):** 실시간 공시, 공시 이력/수동 갱신, 데이터 수집/크롤링, 챗봇 등 (추후 구현 필요, PLAN.md에 todo로 연동)
- **대상 아님:** Prometheus, 별도 챗봇 등(외부 연동, 통합 필요성 낮음)
- **유사기능 타 프로젝트로 통합:** 주식 모니터링(가격 알림), 뉴스/공시(뉴스 요약/검색 등)

## 4. todo/plan 연동
- 각 기능별 PLAN.md의 todo 항목과 매핑, 테스트 케이스와 직접 연결
- PLAN.md의 TODO는 기능별로 구체적으로 관리하며, 진행 상황을 실시간 반영 