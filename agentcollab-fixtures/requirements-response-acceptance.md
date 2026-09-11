# AgentCollab Requirements Response Acceptance Fixture

This file exists only as a disposable external-repository fixture for AgentCollab Issue #200 acceptance testing.

Expected behavior under test:

- a human Requirements answer is durably persisted before external dispatch;
- the exact continuation identity is preserved;
- the same response does not dispatch twice;
- stale response identity fails closed.

Do not merge this fixture PR as part of normal StockEye product work.
