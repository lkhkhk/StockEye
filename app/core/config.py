from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    # API 설정
    DART_API_KEY: str
    UPDATE_INTERVAL: int = 15  # 분 단위

    # 텔레그램 설정
    TELEGRAM_BOT_TOKEN: str
    ADMIN_ID: Optional[str] = None

    # 데이터베이스 설정
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "stockeye"
    DB_USER: str = "stockeye"
    DB_PASSWORD: str

    # Redis 설정
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings() 