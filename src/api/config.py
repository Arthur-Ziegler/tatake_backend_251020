"""
API层配置文件

包含FastAPI应用的所有配置选项，包括数据库连接、中间件设置、
安全配置等。
"""

import os
import secrets
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field


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
    api_host: str = Field(default="0.0.0.0", description="API主机地址")
    api_port: int = Field(default=8001, description="API端口")

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

    # CORS配置 - 允许所有访问，解决部署问题
    allowed_origins: list = Field(
        default=["*"],
        description="允许的源地址（部署环境允许所有访问）"
    )
    allowed_methods: list = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="允许的HTTP方法"
    )
    allowed_headers: list = Field(default=["*"], description="允许的请求头")

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


# 全局配置实例
config = APIConfig()