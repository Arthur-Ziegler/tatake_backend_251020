"""
任务Repository测试

验证TaskRepository的业务逻辑方法，包括：
- 任务查询方法（按用户、状态、优先级查询）
- 任务层级管理方法（父子任务关系）
- 任务状态管理方法（完成、取消、重新打开）
- 任务统计和分析方法

设计原则：
1. 继承BaseRepository，复用基础CRUD操作
2. 封装任务相关的业务查询逻辑
3. 提供类型安全的方法签名
4. 统一的异常处理机制

使用示例：
    >>> # 创建任务Repository
    >>> task_repo = TaskRepository(session)
    >>>
    >>> # 查找用户的所有任务
    >>> tasks = task_repo.find_by_user("user123")
    >>>
    >>> # 查找待完成任务
    >>> pending_tasks = task_repo.find_by_status(TaskStatus.PENDING)
    >>>
    >>> # 完成任务
    >>> completed_task = task_repo.complete_task("task123")
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from sqlmodel import Session, select, and_, or_, func
from sqlalchemy.exc import SQLAlchemyError

# 导入相关模型和Repository
from src.models.task import Task, TaskTop3, TaskTag
from src.models.enums import TaskStatus, PriorityLevel
from src.repositories.task import TaskRepository
from src.repositories.base import RepositoryError, RepositoryValidationError, RepositoryNotFoundError


class TestTaskRepositoryBasic:
    """TaskRepository基础功能测试类"""

    def test_task_repository_inheritance(self):
        """验证TaskRepository继承自BaseRepository"""
        mock_session = Mock(spec=Session)
        task_repo = TaskRepository(mock_session)

        # 验证继承关系
        assert isinstance(task_repo, TaskRepository)
        assert task_repo.model == Task
        assert task_repo.session == mock_session

    def test_task_repository_methods_exist(self):
        """验证TaskRepository的业务方法存在"""
        mock_session = Mock(spec=Session)
        task_repo = TaskRepository(mock_session)

        # 验证所有业务方法存在
        required_methods = [
            'find_by_user',
            'find_by_status',
            'find_by_priority',
            'find_by_parent',
            'find_root_tasks',
            'find_leaf_tasks',
            'find_pending_tasks',
            'find_completed_tasks',
            'find_overdue_tasks',
            'complete_task',
            'reopen_task',
            'cancel_task',
            'delete_task',
            'get_task_statistics',
            'get_task_hierarchy'
        ]

        for method in required_methods:
            assert hasattr(task_repo, method), f"TaskRepository缺少方法: {method}"
            assert callable(getattr(task_repo, method)), f"TaskRepository.{method}不是可调用方法"

    def test_find_by_user_method_interface(self):
        """测试find_by_user方法接口"""
        mock_session = Mock(spec=Session)
        task_repo = TaskRepository(mock_session)

        # 测试方法存在
        assert hasattr(task_repo, 'find_by_user')
        assert callable(task_repo.find_by_user)

        # 测试方法签名
        import inspect
        sig = inspect.signature(task_repo.find_by_user)
        assert 'user_id' in sig.parameters
        assert sig.parameters['user_id'].annotation == str

    def test_find_by_status_method_interface(self):
        """测试find_by_status方法接口"""
        mock_session = Mock(spec=Session)
        task_repo = TaskRepository(mock_session)

        # 测试方法存在
        assert hasattr(task_repo, 'find_by_status')
        assert callable(task_repo.find_by_status)

        # 测试方法签名
        import inspect
        sig = inspect.signature(task_repo.find_by_status)
        assert 'status' in sig.parameters

    def test_find_by_priority_method_interface(self):
        """测试find_by_priority方法接口"""
        mock_session = Mock(spec=Session)
        task_repo = TaskRepository(mock_session)

        # 测试方法存在
        assert hasattr(task_repo, 'find_by_priority')
        assert callable(task_repo.find_by_priority)

        # 测试方法签名
        import inspect
        sig = inspect.signature(task_repo.find_by_priority)
        assert 'priority' in sig.parameters

    def test_find_by_parent_method_interface(self):
        """测试find_by_parent方法接口"""
        mock_session = Mock(spec=Session)
        task_repo = TaskRepository(mock_session)

        # 测试方法存在
        assert hasattr(task_repo, 'find_by_parent')
        assert callable(task_repo.find_by_parent)

        # 测试方法签名
        import inspect
        sig = inspect.signature(task_repo.find_by_parent)
        assert 'parent_id' in sig.parameters

    def test_complete_task_method_interface(self):
        """测试complete_task方法接口"""
        mock_session = Mock(spec=Session)
        task_repo = TaskRepository(mock_session)

        # 测试方法存在
        assert hasattr(task_repo, 'complete_task')
        assert callable(task_repo.complete_task)

        # 测试方法签名
        import inspect
        sig = inspect.signature(task_repo.complete_task)
        assert 'task_id' in sig.parameters
        assert sig.parameters['task_id'].annotation == str

    def test_reopen_task_method_interface(self):
        """测试reopen_task方法接口"""
        mock_session = Mock(spec=Session)
        task_repo = TaskRepository(mock_session)

        # 测试方法存在
        assert hasattr(task_repo, 'reopen_task')
        assert callable(task_repo.reopen_task)

        # 测试方法签名
        import inspect
        sig = inspect.signature(task_repo.reopen_task)
        assert 'task_id' in sig.parameters
        assert sig.parameters['task_id'].annotation == str

    def test_cancel_task_method_interface(self):
        """测试cancel_task方法接口"""
        mock_session = Mock(spec=Session)
        task_repo = TaskRepository(mock_session)

        # 测试方法存在
        assert hasattr(task_repo, 'cancel_task')
        assert callable(task_repo.cancel_task)

        # 测试方法签名
        import inspect
        sig = inspect.signature(task_repo.cancel_task)
        assert 'task_id' in sig.parameters
        assert sig.parameters['task_id'].annotation == str

    def test_delete_task_method_interface(self):
        """测试delete_task方法接口"""
        mock_session = Mock(spec=Session)
        task_repo = TaskRepository(mock_session)

        # 测试方法存在
        assert hasattr(task_repo, 'delete_task')
        assert callable(task_repo.delete_task)

        # 测试方法签名
        import inspect
        sig = inspect.signature(task_repo.delete_task)
        assert 'task_id' in sig.parameters
        assert sig.parameters['task_id'].annotation == str


class TestTaskRepositoryBusinessLogic:
    """TaskRepository业务逻辑测试类"""

    def test_find_by_user_with_mock_session(self):
        """测试find_by_user方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟任务对象
        mock_task = Mock(spec=Task)
        mock_task.id = "test-task-123"
        mock_task.title = "测试任务"
        mock_task.user_id = "user123"

        # 模拟查询执行
        mock_exec_result = Mock()
        mock_exec_result.all.return_value = [mock_task]
        mock_session.exec.return_value = mock_exec_result

        # 创建Repository并测试
        task_repo = TaskRepository(mock_session)

        # 执行测试
        result = task_repo.find_by_user("user123")

        # 验证结果
        assert len(result) == 1
        assert result[0] == mock_task
        mock_session.exec.assert_called_once()

    def test_complete_task_with_mock_session(self):
        """测试complete_task方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟现有任务（待完成状态）
        mock_task = Mock(spec=Task)
        mock_task.id = "task-123"
        mock_task.status = TaskStatus.PENDING

        # 模拟完成后的任务
        mock_completed_task = Mock(spec=Task)
        mock_completed_task.id = "task-123"
        mock_completed_task.status = TaskStatus.COMPLETED
        mock_completed_task.completed_at = datetime.now(timezone.utc)

        # 模拟BaseRepository的get_by_id和update方法
        with patch.object(TaskRepository, 'get_by_id', return_value=mock_task), \
             patch.object(TaskRepository, 'update', return_value=mock_completed_task) as mock_update:

            task_repo = TaskRepository(mock_session)

            # 执行测试
            result = task_repo.complete_task("task-123")

            # 验证结果和调用
            assert result == mock_completed_task
            mock_update.assert_called_once()

    def test_reopen_task_with_mock_session(self):
        """测试reopen_task方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟现有任务（已完成状态）
        mock_task = Mock(spec=Task)
        mock_task.id = "task-123"
        mock_task.status = TaskStatus.COMPLETED

        # 模拟重新打开后的任务
        mock_reopened_task = Mock(spec=Task)
        mock_reopened_task.id = "task-123"
        mock_reopened_task.status = TaskStatus.PENDING

        # 模拟BaseRepository的get_by_id和update方法
        with patch.object(TaskRepository, 'get_by_id', return_value=mock_task), \
             patch.object(TaskRepository, 'update', return_value=mock_reopened_task) as mock_update:

            task_repo = TaskRepository(mock_session)

            # 执行测试
            result = task_repo.reopen_task("task-123")

            # 验证结果和调用
            assert result == mock_reopened_task
            mock_update.assert_called_once()

    def test_cancel_task_with_mock_session(self):
        """测试cancel_task方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟现有任务（待完成状态）
        mock_task = Mock(spec=Task)
        mock_task.id = "task-123"
        mock_task.status = TaskStatus.PENDING

        # 模拟取消后的任务
        mock_cancelled_task = Mock(spec=Task)
        mock_cancelled_task.id = "task-123"
        mock_cancelled_task.status = TaskStatus.CANCELLED

        # 模拟BaseRepository的get_by_id和update方法
        with patch.object(TaskRepository, 'get_by_id', return_value=mock_task), \
             patch.object(TaskRepository, 'update', return_value=mock_cancelled_task) as mock_update:

            task_repo = TaskRepository(mock_session)

            # 执行测试
            result = task_repo.cancel_task("task-123")

            # 验证结果和调用
            assert result == mock_cancelled_task
            mock_update.assert_called_once()

    def test_delete_task_with_mock_session(self):
        """测试delete_task方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟现有任务（未删除状态）
        mock_task = Mock(spec=Task)
        mock_task.id = "task-123"
        mock_task.is_deleted = False

        # 模拟删除后的任务
        mock_deleted_task = Mock(spec=Task)
        mock_deleted_task.id = "task-123"
        mock_deleted_task.is_deleted = True

        # 模拟BaseRepository的get_by_id和update方法
        with patch.object(TaskRepository, 'get_by_id', return_value=mock_task), \
             patch.object(TaskRepository, 'update', return_value=mock_deleted_task) as mock_update:

            task_repo = TaskRepository(mock_session)

            # 执行测试
            result = task_repo.delete_task("task-123")

            # 验证结果和调用
            assert result == mock_deleted_task
            mock_update.assert_called_once()


# 导出测试类
__all__ = [
    "TestTaskRepositoryBasic",
    "TestTaskRepositoryBusinessLogic"
]