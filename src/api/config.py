"""
API层配置文件

包含FastAPI应用的所有配置选项，包括数据库连接、中间件设置、
安全配置等。
"""

import os
from typing import Optional

from pydantic import BaseSettings


class APIConfig(BaseSettings):
    """API配置类"""

    # 应用基础配置
    app_name: str = "TaKeKe API"
    app_version: str = "1.0.0"
    debug: bool = False

    # API配置
    api_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # 数据库配置
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://tatake:tatake@localhost:5432/tatake_db"
    )

    # Redis配置
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # JWT配置
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS配置
    allowed_origins: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://tatake.app"
    ]
    allowed_methods: list = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers: list = ["*"]

    # 限流配置
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst_size: int = 10

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "json"

    # 安全配置
    secure_cookies: bool = True
    csrf_protection: bool = True

    # 文件上传配置
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: list = ["jpg", "jpeg", "png", "gif"]

    # 性能配置
    request_timeout: int = 30  # 秒
    max_concurrent_requests: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
config = APIConfig()