### 2.47. 봇 관리자 명령어 (`show_schedules`) 오류 해결 완료 (2025-08-12)

*   **목표:** 텔레그램 봇의 `/show_schedules` 관리자 명령어 실행 시 발생하던 `404 Not Found` 오류를 해결하고, 스케줄러 제어 기능을 정상화합니다.

*   **문제 원인:**
    *   기존 아키텍처에서 `api` 서비스에 있던 스케줄러 기능이 `worker` 서비스로 분리되었으나, 봇이 워커와 통신하는 방법이 구현되지 않아 봇이 `api`에 요청 시 `404` 오류가 발생했습니다.
    *   `worker` 서비스가 FastAPI 애플리케이션으로 동작하지 않았고, `api` 서비스에서 `worker` 서비스의 스케줄러 상태를 조회하거나 제어할 수 있는 프록시 엔드포인트가 없었습니다.
    *   `worker` 서비스 내부에서 `main.py`와 `routers/scheduler.py` 간의 순환 임포트 문제가 발생하여 `worker` 서비스가 정상적으로 기동되지 못했습니다.

*   **해결 과정:**
    1.  **아키텍처 결정 (Bot -> API -> Worker):** 봇은 `api` 서비스와만 통신하고, `api` 서비스가 필요시 `worker` 서비스와 통신하는 구조로 결정했습니다. 이는 중앙화된 제어 및 인증/인가, 그리고 봇의 단순화를 가능하게 합니다.
    2.  **`worker` 서비스 FastAPI 애플리케이션으로 전환:**
        *   `src/worker/main.py`를 FastAPI 애플리케이션으로 리팩토링했습니다. `lifespan` 컨텍스트 매니저를 사용하여 스케줄러와 Redis 리스너의 생명주기를 관리하도록 했습니다.
        *   `src/worker/routers/scheduler.py` 파일을 생성하고, 스케줄러 상태 조회(`GET /scheduler/status`) 및 잡 수동 실행(`POST /scheduler/trigger/{job_id}`)을 위한 API 엔드포인트를 구현했습니다.
    3.  **순환 임포트 문제 해결:**
        *   `scheduler` 인스턴스 정의를 `src/worker/main.py`에서 `src/worker/scheduler_instance.py`라는 별도의 파일로 분리했습니다.
        *   `src/worker/main.py`와 `src/worker/routers/scheduler.py` 모두 `src/worker/scheduler_instance.py`에서 `scheduler`를 임포트하도록 수정하여 순환 참조 문제를 해결했습니다.
    4.  **`docker-compose.yml` 업데이트:**
        *   `stockeye-worker` 서비스의 `command`를 `uvicorn src.worker.main:app --host 0.0.0.0 --port 8001`로 변경하여 FastAPI 애플리케이션으로 실행되도록 했습니다.
        *   `stockeye-worker` 서비스의 포트 `8001`을 노출했습니다 (내부 네트워크 통신용).
        *   `stockeye-api` 서비스의 `environment`에 `WORKER_HOST=stockeye-worker`를 추가하여 `api`가 `worker`의 주소를 알 수 있도록 했습니다.
    5.  **`api` 서비스에 프록시 엔드포인트 추가:**
        *   `src/api/routers/admin.py`에 `GET /admin/schedule/status` 및 `POST /admin/schedule/trigger/{job_id}` 엔드포인트를 추가했습니다.
        *   이 엔드포인트들은 `httpx`를 사용하여 `stockeye-worker` 서비스의 해당 API를 호출하고 그 결과를 봇에게 프록시하는 역할을 합니다.
    6.  **`bot` 핸들러 확인:** `src/bot/handlers/admin.py`는 이미 `api` 서비스의 `/api/v1/admin/schedule/status` 및 `/api/v1/admin/schedule/trigger/{job_id}` 엔드포인트를 호출하도록 되어 있어 추가 수정이 필요 없음을 확인했습니다.

*   **결과:**
    *   모든 서비스(`stockeye-bot`, `stockeye-api`, `stockeye-worker`) 간의 통신이 정상적으로 이루어짐을 로그를 통해 확인했습니다.
    *   텔레그램 봇에서 `/show_schedules` 명령어를 실행했을 때, 스케줄러의 상태 및 잡 목록이 성공적으로 조회됨을 확인했습니다.
    *   이로써 `PLAN.MD`의 `[진행중] 봇 관리자 명령어(show_schedules) 오류 해결` 과제를 성공적으로 완료했습니다.