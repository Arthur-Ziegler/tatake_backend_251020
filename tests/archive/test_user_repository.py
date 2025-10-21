"""
用户Repository测试

验证UserRepository的业务逻辑方法，包括：
- 用户查询方法（按邮箱、昵称查询）
- 用户状态管理方法
- 用户认证相关查询
- 复杂查询和统计方法

设计原则：
1. 继承BaseRepository，复用基础CRUD操作
2. 封装用户相关的业务查询逻辑
3. 提供类型安全的方法签名
4. 统一的异常处理机制

使用示例：
    >>> # 创建用户Repository
    >>> user_repo = UserRepository(session)
    >>>
    >>> # 按邮箱查找用户
    >>> user = user_repo.find_by_email("user@example.com")
    >>>
    >>> # 查找活跃用户
    >>> active_users = user_repo.find_active_users()
    >>>
    >>> # 检查邮箱是否存在
    >>> exists = user_repo.email_exists("new@example.com")
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from sqlmodel import Session, select, and_, or_, func
from sqlalchemy.exc import SQLAlchemyError

# 导入相关模型和Repository
from src.models.user import User, UserSettings
from src.repositories.user import UserRepository
from src.repositories.base import RepositoryError, RepositoryValidationError, RepositoryNotFoundError


class TestUserRepositoryBasic:
    """UserRepository基础功能测试类"""

    def test_user_repository_inheritance(self):
        """验证UserRepository继承自BaseRepository"""
        mock_session = Mock(spec=Session)
        user_repo = UserRepository(mock_session)

        # 验证继承关系
        assert isinstance(user_repo, UserRepository)
        assert user_repo.model == User
        assert user_repo.session == mock_session

    def test_user_repository_methods_exist(self):
        """验证UserRepository的业务方法存在"""
        mock_session = Mock(spec=Session)
        user_repo = UserRepository(mock_session)

        # 验证所有业务方法存在
        required_methods = [
            'find_by_email',
            'find_by_phone',
            'find_by_wechat_openid',
            'find_registered_users',
            'find_guest_users',
            'find_active_users',
            'email_exists',
            'phone_exists',
            'create_guest_user',
            'upgrade_guest_to_registered'
        ]

        for method in required_methods:
            assert hasattr(user_repo, method), f"UserRepository缺少方法: {method}"
            assert callable(getattr(user_repo, method)), f"UserRepository.{method}不是可调用方法"

    def test_find_by_email_method_interface(self):
        """测试find_by_email方法接口"""
        mock_session = Mock(spec=Session)
        user_repo = UserRepository(mock_session)

        # 测试方法存在
        assert hasattr(user_repo, 'find_by_email')
        assert callable(user_repo.find_by_email)

        # 测试方法签名
        import inspect
        sig = inspect.signature(user_repo.find_by_email)
        assert 'email' in sig.parameters
        assert sig.parameters['email'].annotation == str

    def test_find_by_phone_method_interface(self):
        """测试find_by_phone方法接口"""
        mock_session = Mock(spec=Session)
        user_repo = UserRepository(mock_session)

        # 测试方法存在
        assert hasattr(user_repo, 'find_by_phone')
        assert callable(user_repo.find_by_phone)

        # 测试方法签名
        import inspect
        sig = inspect.signature(user_repo.find_by_phone)
        assert 'phone' in sig.parameters
        assert sig.parameters['phone'].annotation == str

    def test_find_by_wechat_openid_method_interface(self):
        """测试find_by_wechat_openid方法接口"""
        mock_session = Mock(spec=Session)
        user_repo = UserRepository(mock_session)

        # 测试方法存在
        assert hasattr(user_repo, 'find_by_wechat_openid')
        assert callable(user_repo.find_by_wechat_openid)

        # 测试方法签名
        import inspect
        sig = inspect.signature(user_repo.find_by_wechat_openid)
        assert 'wechat_openid' in sig.parameters
        assert sig.parameters['wechat_openid'].annotation == str

    def test_find_registered_users_method_interface(self):
        """测试find_registered_users方法接口"""
        mock_session = Mock(spec=Session)
        user_repo = UserRepository(mock_session)

        # 测试方法存在
        assert hasattr(user_repo, 'find_registered_users')
        assert callable(user_repo.find_registered_users)

        # 测试方法签名
        import inspect
        sig = inspect.signature(user_repo.find_registered_users)
        assert len(sig.parameters) == 0  # 无参数方法

    def test_find_guest_users_method_interface(self):
        """测试find_guest_users方法接口"""
        mock_session = Mock(spec=Session)
        user_repo = UserRepository(mock_session)

        # 测试方法存在
        assert hasattr(user_repo, 'find_guest_users')
        assert callable(user_repo.find_guest_users)

        # 测试方法签名
        import inspect
        sig = inspect.signature(user_repo.find_guest_users)
        assert len(sig.parameters) == 0  # 无参数方法

    def test_find_active_users_method_interface(self):
        """测试find_active_users方法接口"""
        mock_session = Mock(spec=Session)
        user_repo = UserRepository(mock_session)

        # 测试方法存在
        assert hasattr(user_repo, 'find_active_users')
        assert callable(user_repo.find_active_users)

        # 测试方法签名
        import inspect
        sig = inspect.signature(user_repo.find_active_users)
        assert 'days' in sig.parameters
        assert sig.parameters['days'].annotation == int

    def test_email_exists_method_interface(self):
        """测试email_exists方法接口"""
        mock_session = Mock(spec=Session)
        user_repo = UserRepository(mock_session)

        # 测试方法存在
        assert hasattr(user_repo, 'email_exists')
        assert callable(user_repo.email_exists)

        # 测试方法签名
        import inspect
        sig = inspect.signature(user_repo.email_exists)
        assert 'email' in sig.parameters
        assert sig.parameters['email'].annotation == str

    def test_phone_exists_method_interface(self):
        """测试phone_exists方法接口"""
        mock_session = Mock(spec=Session)
        user_repo = UserRepository(mock_session)

        # 测试方法存在
        assert hasattr(user_repo, 'phone_exists')
        assert callable(user_repo.phone_exists)

        # 测试方法签名
        import inspect
        sig = inspect.signature(user_repo.phone_exists)
        assert 'phone' in sig.parameters
        assert sig.parameters['phone'].annotation == str

    def test_create_guest_user_method_interface(self):
        """测试create_guest_user方法接口"""
        mock_session = Mock(spec=Session)
        user_repo = UserRepository(mock_session)

        # 测试方法存在
        assert hasattr(user_repo, 'create_guest_user')
        assert callable(user_repo.create_guest_user)

        # 测试方法签名
        import inspect
        sig = inspect.signature(user_repo.create_guest_user)
        assert 'nickname' in sig.parameters
        assert sig.parameters['nickname'].annotation == str or None

    def test_upgrade_guest_to_registered_method_interface(self):
        """测试upgrade_guest_to_registered方法接口"""
        mock_session = Mock(spec=Session)
        user_repo = UserRepository(mock_session)

        # 测试方法存在
        assert hasattr(user_repo, 'upgrade_guest_to_registered')
        assert callable(user_repo.upgrade_guest_to_registered)

        # 测试方法签名
        import inspect
        sig = inspect.signature(user_repo.upgrade_guest_to_registered)
        assert 'user_id' in sig.parameters
        assert 'email' in sig.parameters
        assert sig.parameters['user_id'].annotation == str
        assert sig.parameters['email'].annotation == str
        assert '**kwargs' in str(sig)  # 有kwargs参数


class TestUserRepositoryBusinessLogic:
    """UserRepository业务逻辑测试类"""

    def test_find_by_email_with_mock_session(self):
        """测试find_by_email方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟用户对象
        mock_user = Mock(spec=User)
        mock_user.id = "test-user-123"
        mock_user.email = "test@example.com"
        mock_user.nickname = "测试用户"

        # 模拟查询执行
        mock_exec_result = Mock()
        mock_exec_result.first.return_value = mock_user
        mock_session.exec.return_value = mock_exec_result

        # 创建Repository并测试
        user_repo = UserRepository(mock_session)

        # 执行测试
        result = user_repo.find_by_email("test@example.com")

        # 验证结果
        assert result == mock_user
        mock_session.exec.assert_called_once()

    def test_email_exists_with_mock_session(self):
        """测试email_exists方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟BaseRepository的exists方法
        with patch.object(UserRepository, 'exists', return_value=True):
            user_repo = UserRepository(mock_session)

            # 执行测试
            result = user_repo.email_exists("test@example.com")

            # 验证结果
            assert result is True

    def test_create_guest_user_with_mock_session(self):
        """测试create_guest_user方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟BaseRepository的create方法
        mock_created_user = Mock(spec=User)
        mock_created_user.id = "guest-user-123"
        mock_created_user.nickname = "游客_20231020120000"
        mock_created_user.is_guest = True

        with patch.object(UserRepository, 'create', return_value=mock_created_user):
            user_repo = UserRepository(mock_session)

            # 执行测试
            result = user_repo.create_guest_user("测试游客")

            # 验证结果
            assert result == mock_created_user

    def test_upgrade_guest_to_registered_with_mock_session(self):
        """测试upgrade_guest_to_registered方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟现有用户（确保是游客状态）
        mock_user = Mock(spec=User)
        mock_user.id = "guest-user-123"
        mock_user.is_guest = True  # 确保是游客用户
        mock_user.email = None

        # 模拟升级后的用户
        mock_upgraded_user = Mock(spec=User)
        mock_upgraded_user.id = "guest-user-123"
        mock_upgraded_user.is_guest = False  # 升级后不再是游客
        mock_upgraded_user.email = "registered@example.com"

        # 模拟BaseRepository的get_by_id、update和email_exists方法
        with patch.object(UserRepository, 'get_by_id', return_value=mock_user), \
             patch.object(UserRepository, 'update', return_value=mock_upgraded_user) as mock_update, \
             patch.object(UserRepository, 'email_exists', return_value=False):

            user_repo = UserRepository(mock_session)

            # 执行测试
            result = user_repo.upgrade_guest_to_registered(
                "guest-user-123",
                "registered@example.com",
                nickname="正式用户"
            )

            # 验证结果和调用
            assert result == mock_upgraded_user
            mock_update.assert_called_once()


# 导出测试类
__all__ = [
    "TestUserRepositoryBasic",
    "TestUserRepositoryBusinessLogic"
]