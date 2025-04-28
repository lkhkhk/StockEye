import asyncpg
import redis.asyncio as redis
from typing import Optional
from .config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """데이터베이스 연결 초기화"""
        try:
            # PostgreSQL 연결 풀 생성
            self.pool = await asyncpg.create_pool(
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                host=settings.DB_HOST,
                port=settings.DB_PORT
            )

            # Redis 연결
            self.redis = redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                decode_responses=True
            )
            await self.redis.ping()

            await self._init_tables()
            logger.info("데이터베이스 및 Redis 연결이 성공적으로 초기화되었습니다.")

        except Exception as e:
            logger.error(f"데이터베이스 연결 중 오류 발생: {e}")
            raise

    async def disconnect(self):
        """데이터베이스 연결 종료"""
        if self.pool:
            await self.pool.close()
        if self.redis:
            await self.redis.aclose()
        logger.info("데이터베이스 및 Redis 연결이 종료되었습니다.")

    async def _init_tables(self):
        """테이블 초기화"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS stocks (
                    code TEXT PRIMARY KEY,
                    name TEXT,
                    corp_code TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_stocks (
                    user_id TEXT,
                    stock_code TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, stock_code),
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY (stock_code) REFERENCES stocks (code) ON DELETE CASCADE
                )
            ''')

            await conn.execute('CREATE INDEX IF NOT EXISTS idx_user_stocks_user_id ON user_stocks (user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_user_stocks_stock_code ON user_stocks (stock_code)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_stocks_corp_code ON stocks (corp_code)')

db = Database() 