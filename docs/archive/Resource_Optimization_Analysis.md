# 리소스 최적화 분석 보고서

## 1. 개요

본 문서는 StockEye 프로젝트의 서비스들이 잠재적으로 리소스를 과도하게 사용할 수 있는 지점들을 식별하고, 이에 대한 개선 방안을 제시합니다. 특히 Oracle VM 환경에서의 안정적인 운영을 위해 메모리, CPU, 네트워크, 디스크 I/O 측면에서 발생할 수 있는 병목 현상을 중점적으로 분석했습니다.

## 2. 분석 대상 및 방법

주요 서비스인 `stockeye-api`와 `stockeye-worker`를 중심으로, 대량의 데이터를 처리하거나 외부 API와 연동하는 함수들을 코드 레벨에서 상세히 검토했습니다. 과거 `worker` 서비스의 OOM(Out Of Memory) 발생 이력을 바탕으로 유사한 패턴을 가진 코드들을 우선적으로 점검했습니다.

## 3. 식별된 잠재적 리소스 병목 지점 및 개선 과제

### 3.1. `worker` 서비스 '종목마스터 갱신' OOM 문제 (OPT-000, 완료)

*   **관련 파일:** `src/common/dart_utils.py`
*   **문제점:** `dart_get_all_stocks` 함수가 DART API로부터 `CORPCODE.xml` 파일을 가져와 처리하는 과정에서 파일 전체를 메모리에 로드하고 XML 트리를 통째로 파싱하여 메모리 사용량이 급증했습니다.
*   **개선 내용:** `lxml.etree.iterparse`를 사용한 **스트리밍 파싱** 방식으로 변경하여 메모리 사용량을 획기적으로 줄였습니다.
*   **상태:** 완료 및 검증 완료.

### 3.2. `일별 시세 갱신` 작업 리소스 최적화 (OPT-001, 완료)

*   **관련 파일:** `src/api/services/stock_service.py`
*   **문제점:** `update_daily_prices` 함수가 DB의 모든 `StockMaster` 종목을 한 번에 가져오고, 각 종목의 `DailyPrice` 데이터를 개별적으로 `db.add()`하는 방식으로 처리하여 종목 수가 증가할수록 메모리 및 처리 시간이 선형적으로 증가했습니다.
*   **개선 내용:**
    1.  **배치 처리 (Batch Processing):** `StockMaster`를 100개씩 끊어서 처리하도록 변경했습니다.
    2.  **벌크 삽입 (Bulk Insertion):** `db.bulk_save_objects()`를 사용하여 `DailyPrice` 데이터를 배치로 DB에 삽입하도록 변경했습니다.
*   **상태:** 완료 및 검증 완료.

### 3.3. `전체 공시 갱신` 작업 리소스 최적화 (OPT-002, 진행 예정)

*   **관련 파일:** `src/api/services/stock_service.py`
*   **문제점:** `update_disclosures_for_all_stocks` 함수가 DART API에서 대량의 공시 데이터를 가져오고, DB에 이미 저장된 **모든 공시 접수번호**를 메모리에 로드하여 중복을 확인합니다. 공시 데이터가 많아질 경우 메모리 사용량이 급증하여 OOM 발생 가능성이 있습니다.
*   **개선 방안:**
    1.  **기존 공시 확인 최적화:** DART에서 가져온 `rcept_no` 목록을 사용하여 DB에 해당 공시가 이미 존재하는지 **배치로 확인**하는 쿼리 로직으로 변경.
    2.  **DART API `max_count` 재검토:** DART API의 페이지네이션 기능을 활용하여 데이터를 여러 번에 걸쳐 가져오는 방안 검토.
*   **상태:** 과제 등록 및 진행 예정.

### 3.4. `가격 알림 확인` 작업 내 쿼리 최적화 (OPT-003, 진행 예정)

*   **관련 파일:** `src/api/services/price_alert_service.py`
*   **문제점:** `check_and_notify_price_alerts` 함수 내에서 `db.query(DailyPrice).filter(DailyPrice.symbol.in_(symbols_to_check)).order_by(DailyPrice.date.desc()).all()` 쿼리가 각 종목별 최신 가격을 효율적으로 가져오지 못하고, `symbols_to_check`의 크기가 커질 경우 쿼리 성능에 영향을 줄 수 있습니다.
*   **개선 방안:** 각 종목별 최신 가격을 효율적으로 가져오도록 쿼리를 최적화 (예: 서브쿼리 또는 `DISTINCT ON` 사용).
*   **상태:** 과제 등록 및 진행 예정.

## 4. 결론 및 향후 계획

Oracle VM 환경에서의 안정적인 서비스 운영을 위해 리소스 관리는 매우 중요합니다. 현재까지 식별된 잠재적 병목 지점들은 `TODO.md`에 별도 과제(`OPT-XXX`)로 등록되었으며, 우선순위에 따라 순차적으로 개선 작업을 진행할 예정입니다. 지속적인 모니터링과 최적화를 통해 시스템의 안정성과 성능을 확보해 나가겠습니다.
