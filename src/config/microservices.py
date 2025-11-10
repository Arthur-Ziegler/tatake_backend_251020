"""
微服务配置管理模块

功能描述：
统一管理所有微服务的连接配置，支持：
- 默认配置设置
- 环境变量覆盖
- 配置验证
- 类型安全

修改记录：
- v1.0.0 (2024-01-10): 初始实现，基于TDD原则
- 优化现有配置系统，整合微服务配置

依赖服务：
- pydantic_settings: 配置管理
- 外部微服务: Auth, Task, Reward, Chat, Focus

设计原则：
1. 类型安全：使用Pydantic确保配置类型正确
2. 默认值：提供合理的生产环境默认配置
3. 环境变量：支持通过.env文件和环境变量覆盖
4. 验证机制：严格的配置验证和错误提示
5. 兼容性：与现有配置系统兼容
"""

import os
from typing import Optional
from pydantic import BaseModel, Field, field_validator, HttpUrl
from pydantic_settings import BaseSettings
from urllib.parse import urlparse


class MicroserviceSettings(BaseSettings):
    """
    微服务配置管理类

    统一管理所有微服务的连接配置，提供类型安全和验证机制。
    基于TDD原则设计，确保配置的正确性和可靠性。
    """

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # 忽略额外字段，兼容现有环境变量
        "env_prefix": "MICROSERVICE_",  # 只处理MICROSERVICE_前缀的环境变量
    }

    # 项目标识符 - 用于多租户数据隔离
    project: str = Field(
        default="tatake_backend",
        description="项目标识符，用于微服务多租户数据隔离",
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$"
    )

    # Auth Service配置
    auth_service_url: str = Field(
        default="http://api.aitodo.it:20251",
        description="认证微服务URL",
        alias="AUTH_MICROSERVICE_URL"  # 兼容现有环境变量名
    )

    # Task Service配置
    task_service_url: str = Field(
        default="http://api.aitodo.it:20253",
        description="任务管理微服务URL",
        alias="TASK_SERVICE_URL"
    )

    # Reward Service配置
    reward_service_url: str = Field(
        default="http://api.aitodo.it:20254",
        description="奖励系统微服务URL",
        alias="REWARD_SERVICE_URL"
    )

    # Chat Service配置
    chat_service_url: str = Field(
        default="http://api.aitodo.it:20252",
        description="聊天系统微服务URL",
        alias="CHAT_SERVICE_URL"
    )

    # Focus Service配置
    focus_service_url: str = Field(
        default="http://api.aitodo.it:20255",
        description="专注系统微服务URL"
    )

    # 通用配置
    request_timeout: int = Field(
        default=30,
        description="微服务请求超时时间（秒）",
        ge=1,  # 最小值1秒
        le=300  # 最大值5分钟
    )

    # HTTP/2支持配置
    http2_enabled: bool = Field(
        default=True,
        description="是否启用HTTP/2支持以提升性能"
    )

    # 连接池配置
    max_connections: int = Field(
        default=100,
        description="每个微服务的最大连接数",
        ge=1,
        le=1000
    )

    max_keepalive_connections: int = Field(
        default=20,
        description="每个微服务的最大保持连接数",
        ge=1,
        le=100
    )

    # 重试配置
    max_retries: int = Field(
        default=3,
        description="微服务调用失败时的最大重试次数",
        ge=0,
        le=10
    )

    retry_delay: float = Field(
        default=1.0,
        description="重试延迟时间（秒）",
        ge=0.1,
        le=60.0
    )

    @field_validator('project')
    @classmethod
    def validate_project(cls, v: str) -> str:
        """验证项目名称格式"""
        if not v or not v.strip():
            raise ValueError("项目名称不能为空")

        v = v.strip()

        # 检查长度
        if len(v) > 50:
            raise ValueError("项目名称长度不能超过50个字符")

        # 检查字符
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("项目名称只能包含字母、数字、下划线和短横线")

        return v

    @field_validator('auth_service_url', 'task_service_url', 'reward_service_url',
                     'chat_service_url', 'focus_service_url')
    @classmethod
    def validate_service_url(cls, v: str) -> str:
        """验证服务URL格式"""
        if not v or not v.strip():
            raise ValueError("服务URL不能为空")

        v = v.strip().rstrip('/')

        try:
            parsed = urlparse(v)
            if parsed.scheme not in ('http', 'https'):
                raise ValueError(f"URL协议必须是http或https，当前: {parsed.scheme}")

            if not parsed.netloc:
                raise ValueError("URL必须包含有效的主机名")

            # 验证端口范围
            if parsed.port and (parsed.port < 1 or parsed.port > 65535):
                raise ValueError(f"端口号必须在1-65535范围内，当前: {parsed.port}")

        except Exception as e:
            if "URL协议必须是" in str(e) or "端口号必须在" in str(e):
                raise
            raise ValueError(f"无效的URL格式: {v}")

        return v

    @field_validator('request_timeout')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """验证超时时间"""
        if v < 1:
            raise ValueError("请求超时时间必须大于0秒")

        if v > 300:
            raise ValueError("请求超时时间不能超过300秒（5分钟）")

        return v

    def get_service_config(self, service_name: str) -> dict:
        """
        获取指定服务的配置

        Args:
            service_name: 服务名称 (auth, task, reward, chat, focus)

        Returns:
            服务配置字典

        Raises:
            ValueError: 不支持的服务名称
        """
        service_configs = {
            'auth': {
                'url': self.auth_service_url,
                'timeout': self.request_timeout,
                'max_retries': self.max_retries,
                'retry_delay': self.retry_delay
            },
            'task': {
                'url': self.task_service_url,
                'timeout': self.request_timeout,
                'max_retries': self.max_retries,
                'retry_delay': self.retry_delay
            },
            'reward': {
                'url': self.reward_service_url,
                'timeout': self.request_timeout,
                'max_retries': self.max_retries,
                'retry_delay': self.retry_delay
            },
            'chat': {
                'url': self.chat_service_url,
                'timeout': self.request_timeout,
                'max_retries': self.max_retries,
                'retry_delay': self.retry_delay
            },
            'focus': {
                'url': self.focus_service_url,
                'timeout': self.request_timeout,
                'max_retries': self.max_retries,
                'retry_delay': self.retry_delay
            }
        }

        if service_name not in service_configs:
            raise ValueError(f"不支持的服务名称: {service_name}，支持的服务: {list(service_configs.keys())}")

        return service_configs[service_name]

    def get_http_client_config(self) -> dict:
        """
        获取HTTP客户端配置

        Returns:
            HTTP客户端配置字典
        """
        return {
            'timeout': self.request_timeout,
            'limits': {
                'max_connections': self.max_connections,
                'max_keepalive_connections': self.max_keepalive_connections,
                'keepalive_expiry': 30.0
            },
            'http2': self.http2_enabled,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay
        }

    def validate_all_services(self) -> dict:
        """
        验证所有微服务配置

        Returns:
            验证结果字典，包含每个服务的状态
        """
        results = {}
        services = ['auth', 'task', 'reward', 'chat', 'focus']

        for service in services:
            try:
                config = self.get_service_config(service)
                results[service] = {
                    'status': 'valid',
                    'url': config['url'],
                    'timeout': config['timeout']
                }
            except Exception as e:
                results[service] = {
                    'status': 'invalid',
                    'error': str(e)
                }

        return results

    def get_service_url(self, service_name: str) -> str:
        """
        获取指定服务的URL

        Args:
            service_name: 服务名称

        Returns:
            服务URL

        Raises:
            ValueError: 不支持的服务名称
        """
        config = self.get_service_config(service_name)
        return config['url']

    def is_healthy_config(self) -> bool:
        """
        检查配置是否健康

        Returns:
            配置是否健康
        """
        try:
            validation_results = self.validate_all_services()
            return all(result['status'] == 'valid' for result in validation_results.values())
        except Exception:
            return False


# 创建全局配置实例
# 使用函数延迟初始化，确保在导入时不会立即创建实例
def _create_microservice_config() -> MicroserviceSettings:
    """创建微服务配置实例"""
    return MicroserviceSettings()


# 全局配置实例（懒加载）
_microservice_config: Optional[MicroserviceSettings] = None


def get_microservice_config() -> MicroserviceSettings:
    """
    获取全局微服务配置实例

    使用懒加载模式，避免在模块导入时立即创建实例。

    Returns:
        微服务配置实例
    """
    global _microservice_config
    if _microservice_config is None:
        _microservice_config = _create_microservice_config()
    return _microservice_config


# 向后兼容的别名
microservice_config = get_microservice_config()


# 配置便捷访问函数
def get_auth_service_url() -> str:
    """获取认证服务URL"""
    return get_microservice_config().auth_service_url


def get_task_service_url() -> str:
    """获取任务服务URL"""
    return get_microservice_config().task_service_url


def get_reward_service_url() -> str:
    """获取奖励服务URL"""
    return get_microservice_config().reward_service_url


def get_chat_service_url() -> str:
    """获取聊天服务URL"""
    return get_microservice_config().chat_service_url


def get_focus_service_url() -> str:
    """获取专注服务URL"""
    return get_microservice_config().focus_service_url


def get_request_timeout() -> int:
    """获取请求超时时间"""
    return get_microservice_config().request_timeout


def get_project_identifier() -> str:
    """获取项目标识符"""
    return get_microservice_config().project