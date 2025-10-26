"""
Auth领域依赖注入模块

提供统一的依赖注入支持，解决session管理和服务实例化问题。
设计原则：
1. 统一session管理：所有数据库操作使用相同的session管理策略
2. 依赖注入：通过FastAPI的Depends机制实现依赖注入
3. 生命周期管理：确保session的正确创建和销毁
4. 测试友好：支持测试时的mock和替换

使用方法：
```python
@router.post("/auth/some-endpoint")
async def some_endpoint(
    auth_service: AuthService = Depends(get_auth_service_with_db)
):
    return await auth_service.some_method()
```
"""

from contextlib import contextmanager
from typing import Generator, Optional

from fastapi import Depends

from .database import get_auth_db
from .service import AuthService


@contextmanager
def get_auth_service_with_session() -> Generator[AuthService, None, None]:
    """
    获取带session的认证服务实例

    这是一个同步的context manager，用于创建带有数据库session的AuthService实例。
    确保session在整个请求生命周期内正确管理，并在请求结束时自动清理。

    Yields:
        AuthService: 带有数据库session的认证服务实例

    Example:
        ```python
        with get_auth_service_with_session() as auth_service:
            result = auth_service.some_method()
        ```
    """
    with get_auth_db() as session:
        # 创建带session的AuthService实例
        auth_service = AuthService(session)
        yield auth_service


def get_auth_service_with_db() -> Generator[AuthService, None, None]:
    """
    FastAPI依赖注入函数：获取带session的认证服务

    这个函数专门用于FastAPI的Depends机制，通过context manager
    确保每个请求都有独立的数据库session，避免session冲突。

    Returns:
        Generator[AuthService, None, None]: 生成AuthService实例的生成器

    Note:
        - 每个API请求都会获得独立的session
        - 请求结束后session自动关闭
        - 事务自动管理（commit/rollback）

    Raises:
        Exception: 数据库连接或操作异常
    """
    with get_auth_db() as session:
        yield AuthService(session)


def get_auth_service_without_db() -> AuthService:
    """
    获取不带数据库的认证服务实例

    用于不需要数据库操作的场景，如JWT验证等。
    这种方式创建的AuthService实例需要手动管理session。

    Returns:
        AuthService: 不带数据库session的认证服务实例

    Warning:
        使用此服务实例进行数据库操作会抛出异常，
        因为没有提供有效的数据库session。
    """
    return AuthService()


# 为了向后兼容，提供一个别名
create_auth_service_with_db = get_auth_service_with_db