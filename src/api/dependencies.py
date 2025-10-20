"""
统一的依赖注入系统

实现ServiceFactory模式的依赖注入系统，提供数据库连接、
服务实例等依赖项的统一管理。
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Generator, AsyncGenerator, Dict, Any
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.services import (
    AuthService,
    JWTService,
    UserService,
    TaskService,
    FocusService,
    RewardService,
    StatisticsService,
    ChatService
)
from src.repositories import (
    UserRepository,
    TaskRepository,
    FocusRepository,
    RewardRepository,
    ChatRepository,
    TokenBlacklistRepository,
    SmsVerificationRepository,
    UserSessionRepository,
    AuthLogRepository
)
from .middleware.auth import verify_token
from .config import config


# HTTP Bearer认证方案
security = HTTPBearer()


class ServiceFactory:
    """服务工厂类，统一管理所有服务的创建和依赖注入"""

    def __init__(self):
        """
        初始化服务工厂

        移除Redis依赖，使用数据库存储替代Redis功能
        """
        self._db_engine = None
        self._db_session_factory = None

        # Repository缓存
        self._repositories: Dict[str, Any] = {}

        # Service缓存
        self._services: Dict[str, Any] = {}

    async def initialize(self):
        """
        初始化工厂，建立数据库连接

        移除Redis依赖，仅初始化数据库连接
        """
        # 确保使用异步数据库URL
        database_url = config.database_url
        if database_url.startswith("sqlite:///"):
            database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

        # 初始化数据库连接
        self._db_engine = create_async_engine(
            database_url,
            echo=config.debug,
            pool_pre_ping=True,
            pool_recycle=3600
        )

        self._db_session_factory = sessionmaker(
            bind=self._db_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def close(self):
        """
        关闭所有连接

        移除Redis依赖，仅关闭数据库连接
        """
        if self._db_engine:
            await self._db_engine.dispose()

    # 数据库连接管理
    @asynccontextmanager
    async def get_database_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话的上下文管理器"""
        if not self._db_session_factory:
            raise RuntimeError("ServiceFactory未初始化")

        async with self._db_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    
    # Repository创建
    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        """获取用户Repository实例"""
        cache_key = f"user_repo_{id(session)}"
        if cache_key not in self._repositories:
            self._repositories[cache_key] = UserRepository(session)
        return self._repositories[cache_key]

    def get_task_repository(self, session: AsyncSession) -> TaskRepository:
        """获取任务Repository实例"""
        cache_key = f"task_repo_{id(session)}"
        if cache_key not in self._repositories:
            self._repositories[cache_key] = TaskRepository(session)
        return self._repositories[cache_key]

    def get_focus_repository(self, session: AsyncSession) -> FocusRepository:
        """获取专注Repository实例"""
        cache_key = f"focus_repo_{id(session)}"
        if cache_key not in self._repositories:
            self._repositories[cache_key] = FocusRepository(session)
        return self._repositories[cache_key]

    def get_reward_repository(self, session: AsyncSession) -> RewardRepository:
        """获取奖励Repository实例"""
        cache_key = f"reward_repo_{id(session)}"
        if cache_key not in self._repositories:
            self._repositories[cache_key] = RewardRepository(session)
        return self._repositories[cache_key]

    def get_chat_repository(self, session: AsyncSession) -> ChatRepository:
        """获取对话Repository实例"""
        cache_key = f"chat_repo_{id(session)}"
        if cache_key not in self._repositories:
            self._repositories[cache_key] = ChatRepository(session)
        return self._repositories[cache_key]

    # 认证相关Repository
    def get_token_blacklist_repository(self, session: AsyncSession) -> TokenBlacklistRepository:
        """获取JWT令牌黑名单Repository实例"""
        cache_key = f"token_blacklist_repo_{id(session)}"
        if cache_key not in self._repositories:
            self._repositories[cache_key] = TokenBlacklistRepository(session)
        return self._repositories[cache_key]

    def get_sms_verification_repository(self, session: AsyncSession) -> SmsVerificationRepository:
        """获取短信验证码Repository实例"""
        cache_key = f"sms_verification_repo_{id(session)}"
        if cache_key not in self._repositories:
            self._repositories[cache_key] = SmsVerificationRepository(session)
        return self._repositories[cache_key]

    def get_user_session_repository(self, session: AsyncSession) -> UserSessionRepository:
        """获取用户会话Repository实例"""
        cache_key = f"user_session_repo_{id(session)}"
        if cache_key not in self._repositories:
            self._repositories[cache_key] = UserSessionRepository(session)
        return self._repositories[cache_key]

    def get_auth_log_repository(self, session: AsyncSession) -> AuthLogRepository:
        """获取认证日志Repository实例"""
        cache_key = f"auth_log_repo_{id(session)}"
        if cache_key not in self._repositories:
            self._repositories[cache_key] = AuthLogRepository(session)
        return self._repositories[cache_key]

    # Service创建
    async def get_auth_service(self, session: AsyncSession) -> AuthService:
        """
        获取认证Service实例

        移除Redis依赖，使用数据库存储替代Redis功能
        """
        cache_key = f"auth_service_{id(session)}"
        if cache_key not in self._services:
            user_repo = self.get_user_repository(session)
            token_blacklist_repo = self.get_token_blacklist_repository(session)
            sms_verification_repo = self.get_sms_verification_repository(session)
            user_session_repo = self.get_user_session_repository(session)
            auth_log_repo = self.get_auth_log_repository(session)

            self._services[cache_key] = AuthService(
                user_repo=user_repo,
                token_blacklist_repo=token_blacklist_repo,
                sms_verification_repo=sms_verification_repo,
                user_session_repo=user_session_repo,
                auth_log_repo=auth_log_repo
            )
        return self._services[cache_key]

    async def get_user_service(self, session: AsyncSession) -> UserService:
        """获取用户Service实例"""
        cache_key = f"user_service_{id(session)}"
        if cache_key not in self._services:
            user_repo = self.get_user_repository(session)
            self._services[cache_key] = UserService(user_repo)
        return self._services[cache_key]

    async def get_task_service(self, session: AsyncSession) -> TaskService:
        """获取任务Service实例"""
        cache_key = f"task_service_{id(session)}"
        if cache_key not in self._services:
            user_repo = self.get_user_repository(session)
            task_repo = self.get_task_repository(session)
            self._services[cache_key] = TaskService(user_repo, task_repo)
        return self._services[cache_key]

    async def get_focus_service(self, session: AsyncSession) -> FocusService:
        """获取专注Service实例"""
        cache_key = f"focus_service_{id(session)}"
        if cache_key not in self._services:
            user_repo = self.get_user_repository(session)
            task_repo = self.get_task_repository(session)
            focus_repo = self.get_focus_repository(session)
            self._services[cache_key] = FocusService(user_repo, task_repo, focus_repo)
        return self._services[cache_key]

    async def get_reward_service(self, session: AsyncSession) -> RewardService:
        """获取奖励Service实例"""
        cache_key = f"reward_service_{id(session)}"
        if cache_key not in self._services:
            user_repo = self.get_user_repository(session)
            reward_repo = self.get_reward_repository(session)
            self._services[cache_key] = RewardService(user_repo, reward_repo)
        return self._services[cache_key]

    async def get_statistics_service(self, session: AsyncSession) -> StatisticsService:
        """获取统计Service实例"""
        cache_key = f"statistics_service_{id(session)}"
        if cache_key not in self._services:
            user_repo = self.get_user_repository(session)
            task_repo = self.get_task_repository(session)
            focus_repo = self.get_focus_repository(session)
            reward_repo = self.get_reward_repository(session)
            self._services[cache_key] = StatisticsService(
                user_repo, task_repo, focus_repo, reward_repo
            )
        return self._services[cache_key]

    async def get_chat_service(self, session: AsyncSession) -> ChatService:
        """获取对话Service实例"""
        cache_key = f"chat_service_{id(session)}"
        if cache_key not in self._services:
            user_repo = self.get_user_repository(session)
            task_repo = self.get_task_repository(session)
            chat_repo = self.get_chat_repository(session)
            self._services[cache_key] = ChatService(user_repo, task_repo, chat_repo)
        return self._services[cache_key]

    # JWT服务
    async def get_jwt_service(self, session: AsyncSession) -> JWTService:
        """获取JWT服务实例"""
        cache_key = f"jwt_service_{id(session)}"
        if cache_key not in self._services:
            token_blacklist_repo = self.get_token_blacklist_repository(session)
            self._services[cache_key] = JWTService(
                token_blacklist_repo=token_blacklist_repo,
                secret_key=config.jwt_secret_key,
                algorithm=config.jwt_algorithm,
                access_token_expiry=config.jwt_access_token_expire_minutes * 60,  # 转换为秒
                refresh_token_expiry=config.jwt_refresh_token_expire_days * 24 * 60 * 60  # 转换为秒
            )
        return self._services[cache_key]

    def clear_cache(self):
        """清理缓存"""
        self._repositories.clear()
        self._services.clear()


# 全局ServiceFactory实例
service_factory = ServiceFactory()


# FastAPI依赖函数
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的FastAPI依赖"""
    async with service_factory.get_database_session() as session:
        yield session




# 用户认证依赖
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """获取当前用户信息"""
    try:
        payload = verify_token(credentials.credentials)
        user_id = payload.get("user_id")
        user_type = payload.get("user_type", "user")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的用户信息"
            )

        return {
            "user_id": user_id,
            "user_type": user_type,
            "token_exp": payload.get("exp")
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"认证失败: {str(e)}"
        )


# 可选认证依赖
async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """获取当前用户信息（可选）"""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# 用户权限验证依赖
async def require_user_type(required_type: str):
    """要求特定用户类型的依赖工厂函数"""
    async def dependency(current_user: dict = Depends(get_current_user)):
        if current_user["user_type"] != required_type:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要{required_type}权限"
            )
        return current_user
    return dependency


# Service依赖函数
async def get_auth_service(
    session: AsyncSession = Depends(get_db_session)
) -> AuthService:
    """获取认证Service的FastAPI依赖"""
    return await service_factory.get_auth_service(session)


async def get_user_service(
    session: AsyncSession = Depends(get_db_session)
) -> UserService:
    """获取用户Service的FastAPI依赖"""
    return await service_factory.get_user_service(session)


async def get_task_service(
    session: AsyncSession = Depends(get_db_session)
) -> TaskService:
    """获取任务Service的FastAPI依赖"""
    return await service_factory.get_task_service(session)


async def get_focus_service(
    session: AsyncSession = Depends(get_db_session)
) -> FocusService:
    """获取专注Service的FastAPI依赖"""
    return await service_factory.get_focus_service(session)


async def get_reward_service(
    session: AsyncSession = Depends(get_db_session)
) -> RewardService:
    """获取奖励Service的FastAPI依赖"""
    return await service_factory.get_reward_service(session)


async def get_statistics_service(
    session: AsyncSession = Depends(get_db_session)
) -> StatisticsService:
    """获取统计Service的FastAPI依赖"""
    return await service_factory.get_statistics_service(session)


async def get_chat_service(
    session: AsyncSession = Depends(get_db_session)
) -> ChatService:
    """获取对话Service的FastAPI依赖"""
    return await service_factory.get_chat_service(session)


async def get_jwt_service(
    session: AsyncSession = Depends(get_db_session)
) -> JWTService:
    """获取JWT服务的FastAPI依赖"""
    return await service_factory.get_jwt_service(session)


# 分页依赖
def get_pagination_params(
    page: int = 1,
    limit: int = 20,
    max_limit: int = 100
) -> dict:
    """获取分页参数的FastAPI依赖"""
    if page < 1:
        page = 1
    if limit < 1:
        limit = 20
    if limit > max_limit:
        limit = max_limit

    offset = (page - 1) * limit

    return {
        "page": page,
        "limit": limit,
        "offset": offset
    }


# 搜索依赖
def get_search_params(
    q: Optional[str] = None,
    sort: str = "created_at",
    order: str = "desc"
) -> dict:
    """获取搜索参数的FastAPI依赖"""
    if order not in ["asc", "desc"]:
        order = "desc"

    return {
        "query": q,
        "sort": sort,
        "order": order
    }


# 文件上传依赖
@lru_cache()
def get_file_upload_config():
    """获取文件上传配置的FastAPI依赖（缓存）"""
    return {
        "max_file_size": config.max_file_size,
        "allowed_file_types": config.allowed_file_types
    }


# 初始化和清理函数
async def initialize_dependencies():
    """初始化依赖注入系统"""
    await service_factory.initialize()


async def cleanup_dependencies():
    """清理依赖注入系统"""
    await service_factory.close()