# FAQ (2025-07-21 기준)

## Q. Alembic 마이그레이션을 사용하나요?
A. 현재는 사용하지 않습니다. DB 스키마 변경은 수동(SQL/ORM)로 관리하며, 변경 후 전체 테스트를 반드시 수행합니다.

## Q. DB 스키마 변경 시 주의사항은?
A. 테이블/컬럼 추가, 삭제, 변경 시 전체 테스트를 실행하여 영향성을 반드시 검증해야 합니다.

## Q. Alembic을 다시 사용하려면?
A. alembic.ini, migrations 폴더를 복구 후 환경설정 및 마이그레이션 생성/적용 절차를 따르면 됩니다.

## Q. 문서화/운영 관련 파일은 어떻게 관리하나요?
A. PLAN.md, SystemManual.md, maintenance.md, FAQ.md 등에서 현황을 실시간으로 반영합니다. 

- Q: API 서버 500 에러 발생 시 어디를 확인해야 하나요?
  - A: `docker compose logs api` 명령으로 `api_service` 컨테이너의 로그를 확인하여 에러의 원인을 파악합니다. 주로 DB 연결 문제, 스키마 불일치, 코드 오류 등이 원인일 수 있습니다.

- Q: 스케줄러가 정상 동작하는지 어떻게 확인하나요?
  - A: `docker compose logs api | grep APScheduler` 명령으로 스케줄러 실행 로그를 확인할 수 있습니다.

- Q: API/스케줄러에서 보내는 텔레그램 알림이 오지 않아요.
  - A: 동기 코드에서 비동기 함수(telegram-python-bot)를 잘못 호출했을 가능성이 높습니다. `maintenance.md`의 트러블슈팅 사례를 참고하여 `asyncio.run()`을 적용했는지 확인하세요. 