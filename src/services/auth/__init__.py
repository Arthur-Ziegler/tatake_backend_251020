"""
认证微服务客户端包

提供与外部认证微服务的HTTP客户端通信功能，包括：
- 认证API调用
- JWT令牌验证
- 自动参数注入
- 错误处理和重试
"""

from .client import AuthMicroserviceClient
from .jwt_validator import JWTValidator

__all__ = ["AuthMicroserviceClient", "JWTValidator"]