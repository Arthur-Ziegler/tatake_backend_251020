"""
API层配置文件

包含FastAPI应用的所有配置选项，包括数据库连接、中间件设置、
安全配置等。
"""

import os
import secrets
from typing import Optional, Union

from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field, field_validator


class APIConfig(BaseSettings):
    """API配置类"""

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow"  # 允许额外字段，兼容现有环境变量
    )

    # 应用基础配置
    app_name: str = Field(default="TaKeKe API", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")

    # API配置
    api_prefix: str = Field(default="", description="API路径前缀")
    api_host: str = Field(default="0.0.0.0", description="API主机地址（用于服务器监听）", env="API_HOST")
    api_port: int = Field(default=8001, description="API端口", env="API_PORT")

    # Swagger UI外部访问配置
    swagger_server_url: Optional[str] = Field(
        default=None,
        description="Swagger UI服务器URL（外部访问地址，如 http://45.152.65.130:2025）",
        env="SWAGGER_SERVER_URL"
    )

    # 数据库配置
    database_url: str = Field(
        default="sqlite+aiosqlite:///./tatake.db",
        description="数据库连接URL"
    )

    
    # JWT配置
    jwt_secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(64),
        description="JWT密钥"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT算法")
    jwt_access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间(分钟)")
    jwt_refresh_token_expire_days: int = Field(default=7, description="刷新令牌过期时间(天)")

    def get_secure_jwt_config(self) -> dict:
        """
        获取安全的JWT配置

        Returns:
            安全的JWT配置字典
        """
        # 确保密钥长度足够
        secret_key = self.jwt_secret_key
        if len(secret_key) < 32:
            secret_key = secrets.token_urlsafe(64)
            print("警告：JWT密钥长度不足，已生成新的安全密钥")

        # 确保使用强算法
        algorithm = self.jwt_algorithm
        if algorithm not in ['HS256', 'HS384', 'HS512']:
            algorithm = 'HS256'
            print("警告：JWT算法不安全，已切换到HS256")

        return {
            'secret_key': secret_key,
            'algorithm': algorithm,
            'access_token_expiry': self.jwt_access_token_expire_minutes * 60,  # 转换为秒
            'refresh_token_expiry': self.jwt_refresh_token_expire_days * 24 * 60 * 60,  # 转换为秒
            'issuer': 'tatake-api',
            'audience': 'tatake-client'
        }

    # CORS配置 - 超级开放，允许所有IP访问所有端口和所有API
    allowed_origins: Union[list, str] = Field(
        default=["*"],
        description="允许的源地址（超级开放，允许所有IP、域名、子域名、端口访问所有API）",
        env="CORS_ORIGINS"
    )
    allowed_methods: Union[list, str] = Field(
        default=["*"],
        description="允许的HTTP方法（超级开放，允许所有HTTP方法）",
        env="CORS_ALLOW_METHODS"
    )
    allowed_headers: Union[list, str] = Field(
        default=["*"],
        description="允许的请求头（超级开放，允许所有请求头包括自定义headers）",
        env="CORS_ALLOW_HEADERS"
    )
    allow_credentials: bool = Field(
        default=True,
        description="是否允许认证凭据（超级开放，允许所有认证凭据）",
        env="CORS_ALLOW_CREDENTIALS"
    )

    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        """解析允许的源地址"""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            elif v.strip() == "":
                return ["*"]
            else:
                return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator('allowed_methods', mode='before')
    @classmethod
    def parse_allowed_methods(cls, v):
        """解析允许的HTTP方法（超级开放）"""
        if isinstance(v, str):
            if v == "*" or v.strip() == "":
                return ["*"]  # 超级开放，返回通配符
            else:
                return [method.strip() for method in v.split(",")]
        return v

    @field_validator('allowed_headers', mode='before')
    @classmethod
    def parse_allowed_headers(cls, v):
        """解析允许的请求头"""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            elif v.strip() == "":
                return ["*"]
            else:
                return [header.strip() for header in v.split(",")]
        return v

    # 限流配置
    rate_limit_enabled: bool = Field(default=True, description="是否启用限流")
    rate_limit_requests_per_minute: int = Field(default=60, description="每分钟请求数限制")
    rate_limit_burst_size: int = Field(default=10, description="突发请求大小")

    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(default="json", description="日志格式")

    # 安全配置
    secure_cookies: bool = Field(default=True, description="安全Cookie")
    csrf_protection: bool = Field(default=True, description="CSRF保护")

    # 文件上传配置
    max_file_size: int = Field(default=10 * 1024 * 1024, description="最大文件大小(字节)")
    allowed_file_types: list = Field(default=["jpg", "jpeg", "png", "gif"], description="允许的文件类型")

    # 性能配置
    request_timeout: int = Field(default=30, description="请求超时时间(秒)")
    max_concurrent_requests: int = Field(default=1000, description="最大并发请求数")

    # Task微服务配置 (已迁移到新服务器)
    task_service_url: str = Field(
        default="http://api.aitodo.it:20253",
        description="Task微服务URL (已迁移至新服务器)",
        env="TASK_SERVICE_URL"
    )
    task_service_timeout: int = Field(
        default=30,
        description="Task微服务调用超时时间(秒)"
    )
    task_service_max_retries: int = Field(
        default=3,
        description="Task微服务调用最大重试次数"
    )
    task_service_retry_delays: str = Field(
        default="1.0,2.0,4.0",
        description="Task微服务调用重试延迟(秒)，逗号分隔"
    )
    task_service_connect_timeout: float = Field(
        default=5.0,
        description="Task微服务连接超时时间(秒)"
    )
    task_service_read_timeout: float = Field(
        default=30.0,
        description="Task微服务读取超时时间(秒)"
    )
    task_service_write_timeout: float = Field(
        default=10.0,
        description="Task微服务写入超时时间(秒)"
    )
    task_service_pool_timeout: float = Field(
        default=60.0,
        description="Task微服务连接池超时时间(秒)"
    )
    task_service_max_keepalive_connections: int = Field(
        default=20,
        description="Task微服务最大保持连接数"
    )
    task_service_max_connections: int = Field(
        default=100,
        description="Task微服务最大连接数"
    )
    task_service_health_check_interval: int = Field(
        default=60,
        description="Task微服务健康检查间隔(秒)"
    )

    # 聊天微服务配置 (已迁移到新服务器)
    chat_service_url: str = Field(
        default="http://api.aitodo.it:20252",
        description="聊天微服务URL (已迁移至新服务器)",
        env="CHAT_SERVICE_URL"
    )
    chat_service_timeout: int = Field(
        default=30,
        description="聊天微服务调用超时时间(秒)"
    )

    # 认证微服务配置 (已迁移到新服务器)
    auth_service_url: str = Field(
        default="http://api.aitodo.it:20251",
        description="认证微服务URL (已迁移至新服务器)",
        env="AUTH_SERVICE_URL"
    )
    auth_service_timeout: int = Field(
        default=30,
        description="认证微服务调用超时时间(秒)"
    )

    # 奖励微服务配置 (已迁移到新服务器)
    reward_service_url: str = Field(
        default="http://45.152.65.130:20254",
        description="奖励微服务URL (已迁移至新服务器)",
        env="REWARD_SERVICE_URL"
    )
    reward_service_enabled: bool = Field(
        default=True,
        description="是否启用奖励微服务",
        env="REWARD_SERVICE_ENABLED"
    )
    reward_service_timeout: int = Field(
        default=30,
        description="奖励微服务调用超时时间(秒)",
        env="REWARD_SERVICE_TIMEOUT"
    )

    # Top3微服务配置 (已集成到Task微服务)
    top3_service_url: str = Field(
        default="http://45.152.65.130:20253",
        description="Top3微服务URL (已集成到Task微服务)",
        env="TOP3_SERVICE_URL"
    )
    top3_service_enabled: bool = Field(
        default=True,
        description="是否启用Top3微服务",
        env="TOP3_SERVICE_ENABLED"
    )
    top3_service_timeout: int = Field(
        default=30,
        description="Top3微服务调用超时时间(秒)",
        env="TOP3_SERVICE_TIMEOUT"
    )

    # Focus微服务配置 (已迁移到新服务器)
    focus_service_url: str = Field(
        default="http://45.152.65.130:20255",
        description="Focus微服务URL (已迁移至新服务器)",
        env="FOCUS_SERVICE_URL"
    )
    focus_service_enabled: bool = Field(
        default=True,
        description="是否启用Focus微服务",
        env="FOCUS_SERVICE_ENABLED"
    )
    focus_service_timeout: int = Field(
        default=30,
        description="Focus微服务调用超时时间(秒)",
        env="FOCUS_SERVICE_TIMEOUT"
    )

    chat_service_timeout: int = Field(
        default=30,
        description="聊天微服务调用超时时间(秒)"
    )


# 全局配置实例
config = APIConfig()


# 配置访问方法
def get_chat_service_url() -> str:
    """获取聊天微服务URL"""
    return config.chat_service_url


def get_chat_service_timeout() -> str:
    """获取聊天微服务超时时间"""
    return str(config.chat_service_timeout)


def get_task_service_url() -> str:
    """获取Task微服务URL"""
    return config.task_service_url


def get_task_service_timeout() -> str:
    """获取Task微服务超时时间"""
    return str(config.task_service_timeout)