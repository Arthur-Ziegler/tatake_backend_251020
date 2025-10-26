"""
Auth领域依赖注入测试

测试认证服务的依赖注入功能，确保：
1. session管理正确
2. 依赖注入正常工作
3. 生命周期管理正确
4. 错误处理机制有效

测试策略：
- 单元测试：测试依赖注入函数本身
- 集成测试：测试与数据库的交互
- 错误场景测试：测试异常情况处理

作者：TaKeKe团队
版本：1.0.0 - 依赖注入测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.domains.auth.dependencies import (
    get_auth_service_with_session,
    get_auth_service_with_db,
    get_auth_service_without_db,
)
from src.domains.auth.service import AuthService
from src.domains.auth.database import get_auth_db


@pytest.mark.unit
class TestAuthDependencies:
    """认证依赖注入测试类"""

    def test_get_auth_service_without_db(self):
        """测试获取不带数据库的认证服务"""
        service = get_auth_service_without_db()

        # 验证返回的是AuthService实例
        assert isinstance(service, AuthService)

        # 验证repository存在但没有有效的session
        assert hasattr(service, 'repository')
        # 由于传入的是context manager而不是session，repository的session是无效的
        # 这就是我们正在修复的核心问题

    @patch('src.domains.auth.dependencies.get_auth_db')
    def test_get_auth_service_with_session_context_manager(self, mock_get_auth_db):
        """测试session context manager的使用"""
        # 创建mock session和service
        mock_session = Mock(spec=Session)
        mock_get_auth_db.return_value.__enter__.return_value = mock_session
        mock_get_auth_db.return_value.__exit__.return_value = None

        # 使用context manager
        with get_auth_service_with_session() as service:
            assert isinstance(service, AuthService)
            # 验证service使用了正确的session
            assert service.repository.session == mock_session

        # 验证context manager被正确调用
        mock_get_auth_db.assert_called_once()

    @patch('src.domains.auth.dependencies.get_auth_db')
    def test_get_auth_service_with_db_dependency_injection(self, mock_get_auth_db):
        """测试FastAPI依赖注入模式"""
        # 创建mock session
        mock_session = Mock(spec=Session)
        mock_get_auth_db.return_value.__enter__.return_value = mock_session
        mock_get_auth_db.return_value.__exit__.return_value = None

        # 模拟FastAPI依赖注入的使用方式
        dependency_generator = get_auth_service_with_db()

        # 获取service实例
        service = next(dependency_generator)

        # 验证返回的是AuthService实例
        assert isinstance(service, AuthService)
        assert service.repository.session == mock_session

        # 验证数据库连接被正确初始化
        mock_get_auth_db.assert_called_once()

    @patch('src.domains.auth.dependencies.get_auth_db')
    def test_get_auth_service_with_db_session_cleanup(self, mock_get_auth_db):
        """测试session的自动清理"""
        mock_session = Mock(spec=Session)
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_get_auth_db.return_value = mock_context_manager

        # 模拟FastAPI请求处理
        dependency_generator = get_auth_service_with_db()
        service = next(dependency_generator)

        # 验证session被正确设置
        assert service.repository.session == mock_session

        # 模拟请求结束，生成器被清理
        try:
            next(dependency_generator)
        except StopIteration:
            pass

        # 验证context manager的exit被调用
        mock_context_manager.__exit__.assert_called_once()

    @patch('src.domains.auth.dependencies.get_auth_db')
    def test_dependency_injection_with_database_error(self, mock_get_auth_db):
        """测试数据库错误时的处理"""
        # 模拟数据库错误
        mock_get_auth_db.side_effect = Exception("Database connection failed")

        # 验证错误被正确抛出
        with pytest.raises(Exception, match="Database connection failed"):
            dependency_generator = get_auth_service_with_db()
            next(dependency_generator)

    @patch('src.domains.auth.dependencies.get_auth_db')
    def test_multiple_service_instances_isolation(self, mock_get_auth_db):
        """测试多个service实例的隔离"""
        # 创建不同的mock sessions
        mock_session1 = Mock(spec=Session)
        mock_session2 = Mock(spec=Session)

        # 配置context manager按顺序返回不同的session
        mock_get_auth_db.side_effect = [
            Mock(__enter__=Mock(return_value=mock_session1), __exit__=Mock(return_value=None)),
            Mock(__enter__=Mock(return_value=mock_session2), __exit__=Mock(return_value=None))
        ]

        # 创建两个service实例
        with get_auth_service_with_session() as service1:
            with get_auth_service_with_session() as service2:
                # 验证两个实例使用不同的session
                assert service1.repository.session == mock_session1
                assert service2.repository.session == mock_session2
                assert service1.repository.session != service2.repository.session

    def test_get_auth_service_with_db_real_session(self):
        """测试使用真实数据库session"""
        # 使用真实的数据库连接（测试数据库）
        dependency_generator = get_auth_service_with_db()

        try:
            # 获取service实例
            service = next(dependency_generator)

            # 验证service类型
            assert isinstance(service, AuthService)

            # 验证repository被正确初始化
            assert hasattr(service, 'repository')
            assert hasattr(service, 'audit_repository')
            assert hasattr(service, 'sms_client')

        finally:
            # 清理生成器
            try:
                next(dependency_generator)
            except StopIteration:
                pass


@pytest.mark.integration
class TestAuthDependenciesIntegration:
    """认证依赖注入集成测试"""

    def test_service_with_real_database_operations(self):
        """测试service与真实数据库的集成"""
        dependency_generator = get_auth_service_with_db()

        try:
            service = next(dependency_generator)

            # 测试基本的数据库操作
            # 注意：这里只测试service能正常使用数据库，不测试具体业务逻辑
            assert service.repository.session is not None

            # 验证session是活跃的
            assert service.repository.session.is_active

        finally:
            # 清理
            try:
                next(dependency_generator)
            except StopIteration:
                pass

    def test_database_transaction_commit(self):
        """测试数据库事务的提交"""
        dependency_generator = get_auth_service_with_db()

        try:
            service = next(dependency_generator)

            # 验证session存在且活跃
            session = service.repository.session
            assert session is not None
            assert session.is_active

            # 这里可以测试具体的数据操作，但为了避免影响测试数据库，
            # 我们只验证session的基本功能

        finally:
            # 清理
            try:
                next(dependency_generator)
            except StopIteration:
                pass


@pytest.mark.unit
class TestDependenciesEdgeCases:
    """依赖注入边界情况测试"""

    def test_dependency_injection_generator_exhaustion(self):
        """测试依赖注入生成器的耗尽情况"""
        generator = get_auth_service_with_db()

        # 第一次调用应该成功
        service1 = next(generator)
        assert isinstance(service1, AuthService)

        # 清理
        try:
            next(generator)
        except StopIteration:
            pass

        # 第二次调用应该抛出StopIteration
        with pytest.raises(StopIteration):
            next(generator)

    def test_context_manager_exception_handling(self):
        """测试context manager的异常处理"""
        with patch('src.domains.auth.dependencies.get_auth_db') as mock_get_auth_db:
            # 模拟context manager抛出异常
            mock_get_auth_db.side_effect = Exception("Context manager error")

            with pytest.raises(Exception, match="Context manager error"):
                with get_auth_service_with_session() as service:
                    # 这里的代码不应该执行
                    assert False, "不应该到达这里"

    def test_session_attribute_access(self):
        """测试service的session属性访问"""
        dependency_generator = get_auth_service_with_db()

        try:
            service = next(dependency_generator)

            # 验证session可以被访问
            session = service.repository.session
            assert session is not None

            # 验证session有基本的数据库操作方法
            assert hasattr(session, 'execute')
            assert hasattr(session, 'commit')
            assert hasattr(session, 'rollback')
            assert hasattr(session, 'close')

        finally:
            # 清理
            try:
                next(dependency_generator)
            except StopIteration:
                pass


@pytest.mark.unit
class TestDependenciesBackwardCompatibility:
    """向后兼容性测试"""

    def test_create_auth_service_with_db_alias(self):
        """测试向后兼容的别名函数"""
        from src.domains.auth.dependencies import create_auth_service_with_db

        # 验证别名函数存在
        assert callable(create_auth_service_with_db)

        # 验证别名函数与原函数相同
        assert create_auth_service_with_db is get_auth_service_with_db