import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_fixed

from src.common.database.db_connector import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1

@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before_sleep=lambda retry_state: logger.info(
        f"Retrying DB connection... Attempt #{retry_state.attempt_number}"
    ),
)
def check_db() -> None:
    try:
        db: Session = SessionLocal()
        # Try to create session to check if DB is awake
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        logger.error(e)
        raise e

if __name__ == "__main__":
    logger.info("Initializing service")
    check_db()
    logger.info("Service finished initializing")
