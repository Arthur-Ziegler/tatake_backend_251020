"""
依赖注入系统测试

测试ServiceFactory模式的依赖注入系统，包括数据库连接管理、
服务实例创建、缓存机制等功能。
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from api.dependencies import (
    ServiceFactory,
    service_factory,
    get_db_session,
    get_current_user,
    get_optional_current_user,
    get_pagination_params,
    get_search_params,
    get_file_upload_config,
    initialize_dependencies,
    cleanup_dependencies
)
from api.middleware.auth import verify_token


class TestServiceFactory:
    """ServiceFactory测试类"""

    @pytest.fixture
    def mock_factory(self):
        """创建模拟的ServiceFactory实例"""
        factory = ServiceFactory()
        return factory

    @pytest.mark.asyncio
    async def test_initialization(self, mock_factory):
        """测试ServiceFactory初始化"""
        # 模拟数据库连接（移除Redis）
        with patch('api.dependencies.create_async_engine') as mock_engine, \
             patch('api.dependencies.sessionmaker') as mock_sessionmaker:

            # 设置模拟对象
            mock_engine.return_value = AsyncMock()
            mock_sessionmaker.return_value = AsyncMock()

            # 执行初始化
            await mock_factory.initialize()

            # 验证初始化调用
            mock_engine.assert_called_once()
            mock_sessionmaker.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_database_session(self, mock_factory):
        """测试数据库会话获取"""
        # 模拟session factory和session
        mock_session = AsyncMock()

        # 创建一个真正的异步上下文管理器
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_factory():
            yield mock_session

        mock_factory._db_session_factory = mock_session_factory

        # 使用上下文管理器获取session
        async with mock_factory.get_database_session() as session:
            assert session == mock_session

        # 验证session提交和关闭
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_database_session_with_rollback(self, mock_factory):
        """测试数据库会话异常回滚"""
        # 模拟session
        mock_session = AsyncMock()

        # 创建一个真正的异步上下文管理器
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_factory():
            yield mock_session

        mock_factory._db_session_factory = mock_session_factory

        # 模拟异常
        with pytest.raises(Exception):
            async with mock_factory.get_database_session() as session:
                raise Exception("测试异常")

        # 验证session回滚和关闭
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    def test_get_redis_client_removed(self, mock_factory):
        """测试Redis客户端获取 - 已移除"""
        # Redis客户端已被移除，这个测试应该被跳过
        pytest.skip("Redis客户端已被移除")

    def test_get_redis_client_uninitialized_removed(self, mock_factory):
        """测试未初始化时获取Redis客户端 - 已移除"""
        # Redis客户端已被移除，这个测试应该被跳过
        pytest.skip("Redis客户端已被移除")

    def test_get_user_repository(self, mock_factory):
        """测试用户Repository创建"""
        # 模拟session
        mock_session = AsyncMock()

        # 获取Repository
        repo1 = mock_factory.get_user_repository(mock_session)
        repo2 = mock_factory.get_user_repository(mock_session)

        # 验证缓存机制
        assert repo1 is repo2
        assert len(mock_factory._repositories) == 1

    def test_get_task_repository(self, mock_factory):
        """测试任务Repository创建"""
        # 模拟session
        mock_session = AsyncMock()

        # 获取Repository
        repo = mock_factory.get_task_repository(mock_session)

        # 验证Repository类型
        assert repo is not None

    def test_get_focus_repository(self, mock_factory):
        """测试专注Repository创建"""
        # 模拟session
        mock_session = AsyncMock()

        # 获取Repository
        repo = mock_factory.get_focus_repository(mock_session)

        # 验证Repository类型
        assert repo is not None

    def test_get_reward_repository(self, mock_factory):
        """测试奖励Repository创建"""
        # 模拟session
        mock_session = AsyncMock()

        # 获取Repository
        repo = mock_factory.get_reward_repository(mock_session)

        # 验证Repository类型
        assert repo is not None

    def test_get_chat_repository(self, mock_factory):
        """测试对话Repository创建"""
        # 模拟session
        mock_session = AsyncMock()

        # 获取Repository
        repo = mock_factory.get_chat_repository(mock_session)

        # 验证Repository类型
        assert repo is not None

    @pytest.mark.asyncio
    async def test_get_auth_service(self, mock_factory):
        """测试认证Service创建"""
        # 模拟依赖（移除Redis）
        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()

        with patch.object(mock_factory, 'get_user_repository', return_value=mock_user_repo):
            # 获取Service
            service1 = await mock_factory.get_auth_service(mock_session)
            service2 = await mock_factory.get_auth_service(mock_session)

            # 验证缓存机制
            assert service1 is service2
            assert len(mock_factory._services) == 1

    @pytest.mark.asyncio
    async def test_get_user_service(self, mock_factory):
        """测试用户Service创建"""
        # 模拟依赖
        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()

        with patch.object(mock_factory, 'get_user_repository', return_value=mock_user_repo):
            # 获取Service
            service = await mock_factory.get_user_service(mock_session)

            # 验证Service类型
            assert service is not None

    @pytest.mark.asyncio
    async def test_get_task_service(self, mock_factory):
        """测试任务Service创建"""
        # 模拟依赖
        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_task_repo = AsyncMock()

        with patch.object(mock_factory, 'get_user_repository', return_value=mock_user_repo), \
             patch.object(mock_factory, 'get_task_repository', return_value=mock_task_repo):
            # 获取Service
            service = await mock_factory.get_task_service(mock_session)

            # 验证Service类型
            assert service is not None

    def test_clear_cache(self, mock_factory):
        """测试缓存清理"""
        # 添加一些缓存数据
        mock_session = AsyncMock()
        mock_factory.get_user_repository(mock_session)
        mock_factory.get_task_repository(mock_session)

        # 验证缓存存在
        assert len(mock_factory._repositories) > 0

        # 清理缓存
        mock_factory.clear_cache()

        # 验证缓存已清理
        assert len(mock_factory._repositories) == 0
        assert len(mock_factory._services) == 0

    @pytest.mark.asyncio
    async def test_close(self, mock_factory):
        """测试关闭连接"""
        # 模拟依赖（移除Redis）
        mock_engine = AsyncMock()

        mock_factory._db_engine = mock_engine

        # 关闭连接
        await mock_factory.close()

        # 验证关闭调用
        mock_engine.dispose.assert_called_once()


class TestFastAPIDependencies:
    """FastAPI依赖函数测试类"""

    @pytest.mark.asyncio
    async def test_get_db_session(self):
        """测试数据库会话依赖"""
        # 模拟service_factory
        with patch('api.dependencies.service_factory') as mock_factory:
            mock_session = AsyncMock()
            mock_factory.get_database_session.return_value.__aenter__.return_value = mock_session

            # 调用依赖函数
            async for session in get_db_session():
                assert session == mock_session
                break

    @pytest.mark.asyncio
    async def test_get_redis_client_removed(self):
        """测试Redis客户端依赖 - 已移除"""
        # Redis客户端已被移除，这个测试应该被跳过
        pytest.skip("Redis客户端已被移除")

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """测试获取当前用户成功"""
        # 模拟token验证
        mock_payload = {
            "user_id": "test_user_123",
            "user_type": "user",
            "exp": 1234567890
        }

        with patch('api.dependencies.verify_token', return_value=mock_payload):
            from fastapi.security import HTTPAuthorizationCredentials

            # 模拟认证凭据
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="test_token"
            )

            # 调用依赖函数
            user_info = await get_current_user(credentials)
            assert user_info["user_id"] == "test_user_123"
            assert user_info["user_type"] == "user"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_payload(self):
        """测试获取当前用户无效payload"""
        # 模拟无效payload
        mock_payload = {}

        with patch('api.dependencies.verify_token', return_value=mock_payload):
            from fastapi.security import HTTPAuthorizationCredentials

            # 模拟认证凭据
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="test_token"
            )

            # 验证抛出异常
            with pytest.raises(Exception):  # HTTPException
                await get_current_user(credentials)

    @pytest.mark.asyncio
    async def test_get_current_user_verification_error(self):
        """测试获取当前用户验证错误"""
        # 模拟验证异常
        with patch('api.dependencies.verify_token', side_effect=Exception("验证失败")):
            from fastapi.security import HTTPAuthorizationCredentials

            # 模拟认证凭据
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="invalid_token"
            )

            # 验证抛出异常
            with pytest.raises(Exception):  # HTTPException
                await get_current_user(credentials)

    @pytest.mark.asyncio
    async def test_get_optional_current_user_with_credentials(self):
        """测试可选认证用户 - 有认证信息"""
        # 模拟成功认证
        mock_payload = {
            "user_id": "test_user_123",
            "user_type": "user"
        }

        with patch('api.dependencies.verify_token', return_value=mock_payload):
            from fastapi.security import HTTPAuthorizationCredentials

            # 模拟认证凭据
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="test_token"
            )

            # 调用依赖函数
            user_info = await get_optional_current_user(credentials)
            assert user_info["user_id"] == "test_user_123"

    @pytest.mark.asyncio
    async def test_get_optional_current_user_without_credentials(self):
        """测试可选认证用户 - 无认证信息"""
        # 调用依赖函数
        user_info = await get_optional_current_user(None)
        assert user_info is None

    def test_get_pagination_params_default(self):
        """测试分页参数 - 默认值"""
        params = get_pagination_params()
        assert params["page"] == 1
        assert params["limit"] == 20
        assert params["offset"] == 0

    def test_get_pagination_params_custom(self):
        """测试分页参数 - 自定义值"""
        params = get_pagination_params(page=2, limit=10, max_limit=50)
        assert params["page"] == 2
        assert params["limit"] == 10
        assert params["offset"] == 10

    def test_get_pagination_params_invalid(self):
        """测试分页参数 - 无效值处理"""
        # 无效页码
        params = get_pagination_params(page=0, limit=20)
        assert params["page"] == 1
        assert params["offset"] == 0

        # 无效限制
        params = get_pagination_params(page=1, limit=0)
        assert params["limit"] == 20

        # 超过最大限制
        params = get_pagination_params(page=1, limit=150, max_limit=100)
        assert params["limit"] == 100

    def test_get_search_params_default(self):
        """测试搜索参数 - 默认值"""
        params = get_search_params()
        assert params["query"] is None
        assert params["sort"] == "created_at"
        assert params["order"] == "desc"

    def test_get_search_params_custom(self):
        """测试搜索参数 - 自定义值"""
        params = get_search_params(q="test", sort="title", order="asc")
        assert params["query"] == "test"
        assert params["sort"] == "title"
        assert params["order"] == "asc"

    def test_get_search_params_invalid_order(self):
        """测试搜索参数 - 无效排序"""
        params = get_search_params(order="invalid")
        assert params["order"] == "desc"  # 默认值

    def test_get_file_upload_config(self):
        """测试文件上传配置"""
        config1 = get_file_upload_config()
        config2 = get_file_upload_config()

        # 验证缓存机制
        assert config1 is config2

        # 验证配置结构
        assert "max_file_size" in config1
        assert "allowed_file_types" in config1

    @pytest.mark.asyncio
    async def test_initialize_dependencies(self):
        """测试初始化依赖注入系统"""
        with patch('api.dependencies.service_factory') as mock_factory:
            mock_factory.initialize = AsyncMock()
            await initialize_dependencies()
            mock_factory.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_dependencies(self):
        """测试清理依赖注入系统"""
        with patch('api.dependencies.service_factory') as mock_factory:
            mock_factory.close = AsyncMock()
            await cleanup_dependencies()
            mock_factory.close.assert_called_once()


class TestDependencyIntegration:
    """依赖注入集成测试类"""

    @pytest.mark.asyncio
    async def test_service_factory_end_to_end(self):
        """测试ServiceFactory端到端流程（简化版）"""
        # 测试基本功能而不需要完整的数据库设置
        factory = ServiceFactory()

        # 验证初始状态
        assert factory._db_engine is None
        assert factory._db_session_factory is None
        assert len(factory._repositories) == 0
        assert len(factory._services) == 0

        # 测试Repository缓存功能（使用模拟session）
        mock_session = AsyncMock()

        user_repo = factory.get_user_repository(mock_session)
        task_repo = factory.get_task_repository(mock_session)

        # 验证Repository被创建和缓存
        assert user_repo is not None
        assert task_repo is not None
        assert len(factory._repositories) == 2

        # 再次获取同样的Repository应该返回缓存实例
        user_repo2 = factory.get_user_repository(mock_session)
        assert user_repo is user_repo2

        # 测试缓存清理
        factory.clear_cache()
        assert len(factory._repositories) == 0
        assert len(factory._services) == 0


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])