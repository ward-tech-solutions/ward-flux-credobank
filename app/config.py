"""Application configuration"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "WARD OPS"
    DEBUG: bool = True

    # Database
    DATABASE_PATH: str = "data/ward_ops.db"

    # Zabbix
    ZABBIX_URL: str = os.getenv("ZABBIX_URL", "http://10.199.96.5:8080")
    ZABBIX_USER: str = os.getenv("ZABBIX_USER", "Admin")
    ZABBIX_PASSWORD: str = os.getenv("ZABBIX_PASSWORD", "zabbix")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
