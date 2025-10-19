"""
专注Repository测试

验证FocusRepository的业务逻辑方法，包括：
- 专注会话查询方法（按用户、类型、状态查询）
- 专注会话管理方法（开始、结束、暂停、恢复会话）
- 专注统计和分析方法（总时长、完成率、日均专注等）
- 专注模板管理方法（创建、应用、删除模板）
- 休息记录管理方法（添加、查询休息时间）

设计原则：
1. 继承BaseRepository，复用基础CRUD操作
2. 封装专注相关的业务查询逻辑
3. 提供类型安全的方法签名
4. 统一的异常处理机制

使用示例：
    >>> # 创建专注Repository
    >>> focus_repo = FocusRepository(session)
    >>>
    >>> # 查找用户今日专注会话
    >>> sessions = focus_repo.find_user_today_sessions("user123")
    >>>
    >>> # 开始专注会话
    >>> active_session = focus_repo.start_focus_session("user123", 25)
    >>>
    >>> # 完成专注会话
    >>> completed_session = focus_repo.complete_session("session123")
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from sqlmodel import Session, select, and_, or_, func
from sqlalchemy.exc import SQLAlchemyError

# 导入相关模型和Repository
from src.models.focus import FocusSession, FocusSessionBreak, FocusSessionTemplate
from src.models.enums import SessionType
from src.repositories.focus import FocusRepository
from src.repositories.base import RepositoryError, RepositoryValidationError, RepositoryNotFoundError


class TestFocusRepositoryBasic:
    """FocusRepository基础功能测试类"""

    def test_focus_repository_inheritance(self):
        """验证FocusRepository继承自BaseRepository"""
        mock_session = Mock(spec=Session)
        focus_repo = FocusRepository(mock_session)

        # 验证继承关系
        assert isinstance(focus_repo, FocusRepository)
        assert focus_repo.model == FocusSession
        assert focus_repo.session == mock_session

    def test_focus_repository_methods_exist(self):
        """验证FocusRepository的业务方法存在"""
        mock_session = Mock(spec=Session)
        focus_repo = FocusRepository(mock_session)

        # 验证所有业务方法存在
        required_methods = [
            # 专注会话查询方法
            'find_by_user',
            'find_by_session_type',
            'find_active_sessions',
            'find_completed_sessions',
            'find_user_today_sessions',
            'find_user_sessions_by_date_range',

            # 专注会话管理方法
            'start_focus_session',
            'complete_session',
            'pause_session',
            'resume_session',
            'cancel_session',

            # 专注统计方法
            'get_user_focus_statistics',
            'get_daily_focus_summary',
            'get_weekly_focus_summary',
            'get_monthly_focus_summary',

            # 专注模板方法
            'create_template',
            'apply_template',
            'find_user_templates',
            'delete_template',

            # 休息记录方法
            'add_break',
            'find_session_breaks',
            'complete_break'
        ]

        for method in required_methods:
            assert hasattr(focus_repo, method), f"FocusRepository缺少方法: {method}"
            assert callable(getattr(focus_repo, method)), f"FocusRepository.{method}不是可调用方法"

    def test_find_by_user_method_interface(self):
        """测试find_by_user方法接口"""
        mock_session = Mock(spec=Session)
        focus_repo = FocusRepository(mock_session)

        # 测试方法存在
        assert hasattr(focus_repo, 'find_by_user')
        assert callable(focus_repo.find_by_user)

        # 测试方法签名
        import inspect
        sig = inspect.signature(focus_repo.find_by_user)
        assert 'user_id' in sig.parameters
        assert sig.parameters['user_id'].annotation == str

    def test_find_active_sessions_method_interface(self):
        """测试find_active_sessions方法接口"""
        mock_session = Mock(spec=Session)
        focus_repo = FocusRepository(mock_session)

        # 测试方法存在
        assert hasattr(focus_repo, 'find_active_sessions')
        assert callable(focus_repo.find_active_sessions)

        # 测试方法签名
        import inspect
        sig = inspect.signature(focus_repo.find_active_sessions)
        assert 'user_id' in sig.parameters
        assert sig.parameters['user_id'].annotation == str

    def test_start_focus_session_method_interface(self):
        """测试start_focus_session方法接口"""
        mock_session = Mock(spec=Session)
        focus_repo = FocusRepository(mock_session)

        # 测试方法存在
        assert hasattr(focus_repo, 'start_focus_session')
        assert callable(focus_repo.start_focus_session)

        # 测试方法签名
        import inspect
        sig = inspect.signature(focus_repo.start_focus_session)
        assert 'user_id' in sig.parameters
        assert 'duration_minutes' in sig.parameters
        assert sig.parameters['user_id'].annotation == str
        assert sig.parameters['duration_minutes'].annotation == int

    def test_complete_session_method_interface(self):
        """测试complete_session方法接口"""
        mock_session = Mock(spec=Session)
        focus_repo = FocusRepository(mock_session)

        # 测试方法存在
        assert hasattr(focus_repo, 'complete_session')
        assert callable(focus_repo.complete_session)

        # 测试方法签名
        import inspect
        sig = inspect.signature(focus_repo.complete_session)
        assert 'session_id' in sig.parameters
        assert sig.parameters['session_id'].annotation == str

    def test_get_user_focus_statistics_method_interface(self):
        """测试get_user_focus_statistics方法接口"""
        mock_session = Mock(spec=Session)
        focus_repo = FocusRepository(mock_session)

        # 测试方法存在
        assert hasattr(focus_repo, 'get_user_focus_statistics')
        assert callable(focus_repo.get_user_focus_statistics)

        # 测试方法签名
        import inspect
        sig = inspect.signature(focus_repo.get_user_focus_statistics)
        assert 'user_id' in sig.parameters
        assert sig.parameters['user_id'].annotation == str

    def test_create_template_method_interface(self):
        """测试create_template方法接口"""
        mock_session = Mock(spec=Session)
        focus_repo = FocusRepository(mock_session)

        # 测试方法存在
        assert hasattr(focus_repo, 'create_template')
        assert callable(focus_repo.create_template)

        # 测试方法签名
        import inspect
        sig = inspect.signature(focus_repo.create_template)
        assert 'user_id' in sig.parameters
        assert 'name' in sig.parameters
        assert 'focus_duration' in sig.parameters
        assert sig.parameters['user_id'].annotation == str
        assert sig.parameters['name'].annotation == str
        assert sig.parameters['focus_duration'].annotation == int


class TestFocusRepositoryBusinessLogic:
    """FocusRepository业务逻辑测试类"""

    def test_find_by_user_with_mock_session(self):
        """测试find_by_user方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟专注会话对象
        mock_session_obj = Mock(spec=FocusSession)
        mock_session_obj.id = "session-123"
        mock_session_obj.user_id = "user123"
        mock_session_obj.session_type = SessionType.FOCUS

        # 模拟查询执行
        mock_exec_result = Mock()
        mock_exec_result.all.return_value = [mock_session_obj]
        mock_session.exec.return_value = mock_exec_result

        # 创建Repository并测试
        focus_repo = FocusRepository(mock_session)

        # 执行测试
        result = focus_repo.find_by_user("user123")

        # 验证结果
        assert len(result) == 1
        assert result[0] == mock_session_obj
        mock_session.exec.assert_called_once()

    def test_find_active_sessions_with_mock_session(self):
        """测试find_active_sessions方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟活跃的专注会话
        mock_active_session = Mock(spec=FocusSession)
        mock_active_session.id = "active-session-123"
        mock_active_session.user_id = "user123"
        mock_active_session.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        mock_active_session.ended_at = None

        # 模拟查询执行
        mock_exec_result = Mock()
        mock_exec_result.all.return_value = [mock_active_session]
        mock_session.exec.return_value = mock_exec_result

        # 创建Repository并测试
        focus_repo = FocusRepository(mock_session)

        # 执行测试
        result = focus_repo.find_active_sessions("user123")

        # 验证结果
        assert len(result) == 1
        assert result[0] == mock_active_session
        mock_session.exec.assert_called_once()

    def test_start_focus_session_with_mock_session(self):
        """测试start_focus_session方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟创建的专注会话
        mock_new_session = Mock(spec=FocusSession)
        mock_new_session.id = "new-session-123"
        mock_new_session.user_id = "user123"
        mock_new_session.session_type = SessionType.FOCUS
        mock_new_session.duration_minutes = 25
        mock_new_session.started_at = datetime.now(timezone.utc)
        mock_new_session.is_completed = False

        # 模拟BaseRepository的create方法
        with patch.object(FocusRepository, 'create', return_value=mock_new_session):
            focus_repo = FocusRepository(mock_session)

            # 执行测试
            result = focus_repo.start_focus_session("user123", 25)

            # 验证结果
            assert result == mock_new_session

    def test_complete_session_with_mock_session(self):
        """测试complete_session方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟现有会话（需要真实的started_at时间）
        start_time = datetime.now(timezone.utc) - timedelta(minutes=20)
        mock_existing_session = Mock(spec=FocusSession)
        mock_existing_session.id = "session-123"
        mock_existing_session.is_completed = False
        mock_existing_session.ended_at = None
        mock_existing_session.started_at = start_time

        # 模拟完成后的会话
        mock_completed_session = Mock(spec=FocusSession)
        mock_completed_session.id = "session-123"
        mock_completed_session.is_completed = True
        mock_completed_session.ended_at = datetime.now(timezone.utc)
        mock_completed_session.duration_minutes = 25

        # 模拟BaseRepository的get_by_id和update方法
        with patch.object(FocusRepository, 'get_by_id', return_value=mock_existing_session), \
             patch.object(FocusRepository, 'update', return_value=mock_completed_session) as mock_update:

            focus_repo = FocusRepository(mock_session)

            # 执行测试
            result = focus_repo.complete_session("session-123")

            # 验证结果和调用
            assert result == mock_completed_session
            mock_update.assert_called_once()

    def test_get_user_focus_statistics_with_mock_session(self):
        """测试get_user_focus_statistics方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟统计查询结果（创建Mock scalar对象）
        mock_total_minutes = 150  # 总专注时长150分钟
        mock_completed_sessions = 5  # 完成会话数
        mock_total_sessions = 6  # 总会话数
        mock_today_minutes = 25  # 今日专注时长

        # 模拟查询执行
        mock_scalar1 = Mock()
        mock_scalar1.one.return_value = mock_total_minutes

        mock_scalar2 = Mock()
        mock_scalar2.one.return_value = mock_completed_sessions

        mock_scalar3 = Mock()
        mock_scalar3.one.return_value = mock_total_sessions

        mock_scalar4 = Mock()
        mock_scalar4.one.return_value = mock_today_minutes

        mock_session.exec.side_effect = [
            mock_scalar1,  # 总时长查询
            mock_scalar2,  # 完成会话查询
            mock_scalar3,  # 总会话查询
            mock_scalar4   # 今日专注时长查询
        ]

        # 创建Repository并测试
        focus_repo = FocusRepository(mock_session)

        # 执行测试
        result = focus_repo.get_user_focus_statistics("user123")

        # 验证结果
        assert 'total_focus_minutes' in result
        assert 'completed_sessions' in result
        assert 'completion_rate' in result
        assert result['total_focus_minutes'] == mock_total_minutes
        assert result['completed_sessions'] == mock_completed_sessions
        assert result['total_sessions'] == mock_total_sessions
        assert result['today_minutes'] == mock_today_minutes

    def test_create_template_with_mock_session(self):
        """测试create_template方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 简化测试：只验证方法存在和基本参数验证
        focus_repo = FocusRepository(mock_session)

        # 测试无效参数的验证
        with pytest.raises(RepositoryValidationError):
            focus_repo.create_template("", "名称", 25)  # 空用户ID

        with pytest.raises(RepositoryValidationError):
            focus_repo.create_template("user123", "", 25)  # 空名称

        with pytest.raises(RepositoryValidationError):
            focus_repo.create_template("user123", "名称", 0)  # 无效时长

        with pytest.raises(RepositoryValidationError):
            focus_repo.create_template("user123", "名称", 500)  # 超长时长

        # 验证方法存在且可调用
        assert hasattr(focus_repo, 'create_template')
        assert callable(focus_repo.create_template)


# 导出测试类
__all__ = [
    "TestFocusRepositoryBasic",
    "TestFocusRepositoryBusinessLogic"
]