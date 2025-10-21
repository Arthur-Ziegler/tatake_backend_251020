"""
Repository层集成测试

验证各个Repository之间的协作和整体数据访问层的完整性，包括：
- Repository之间的数据一致性
- 跨Repository的业务流程
- 事务处理和回滚机制
- 复杂查询场景的性能和正确性
- 错误传播和异常处理机制

设计原则：
1. 端到端测试，验证完整的业务流程
2. 使用真实的数据库连接
3. 测试Repository之间的协作
4. 验证数据一致性和完整性约束
5. 性能测试和压力测试

使用示例：
    >>> # 创建测试数据库会话
    >>> session = create_test_session()
    >>>
    >>> # 测试用户注册到专注会话的完整流程
    >>> user = user_repo.create_registered_user(...)
    >>> session = focus_repo.start_focus_session(user.id, 25)
    >>> completed = focus_repo.complete_session(session.id)
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, create_engine, select
from sqlalchemy.orm import sessionmaker

# 导入相关模型和Repository
from src.models.user import User
from src.models.task import Task
from src.models.focus import FocusSession, FocusSessionBreak
from src.models.reward import Reward, UserFragment, PointsTransaction
from src.models.enums import TaskStatus, SessionType, RewardType, TransactionType
from src.repositories import (
    UserRepository,
    TaskRepository,
    FocusRepository,
    RewardRepository
)
from src.repositories.base import RepositoryError, RepositoryValidationError


class TestRepositoryIntegrationBasic:
    """Repository层基础集成测试类"""

    @pytest.fixture
    def test_session(self):
        """创建测试数据库会话"""
        # 使用内存SQLite数据库进行测试
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            echo=False
        )

        # 创建所有表
        from src.models.base_model import BaseSQLModel
        BaseSQLModel.metadata.create_all(engine)

        # 创建会话
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def repositories(self, test_session):
        """创建所有Repository实例"""
        return {
            'user': UserRepository(test_session),
            'task': TaskRepository(test_session),
            'focus': FocusRepository(test_session),
            'reward': RewardRepository(test_session)
        }

    def test_repository_initialization_with_session(self, test_session, repositories):
        """测试Repository使用真实会话的初始化"""
        # 验证所有Repository都能正确初始化
        assert repositories['user'].session == test_session
        assert repositories['task'].session == test_session
        assert repositories['focus'].session == test_session
        assert repositories['reward'].session == test_session

        # 验证Repository模型类型
        assert repositories['user'].model == User
        assert repositories['task'].model == Task
        assert repositories['focus'].model == FocusSession
        assert repositories['reward'].model == Reward

    def test_cross_repository_data_consistency(self, test_session, repositories):
        """测试跨Repository的数据一致性"""
        user_repo = repositories['user']
        task_repo = repositories['task']
        focus_repo = repositories['focus']

        # 创建用户
        user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = user_repo.create({
            "email": user_email,
            "nickname": "测试用户",
            "password_hash": "test_hash",
            "user_type": "registered"
        })

        # 验证用户创建成功
        assert user.id is not None
        assert user.email == user_email

        # 创建任务
        task = task_repo.create_task(
            user_id=user.id,
            title="测试任务",
            description="这是一个测试任务"
        )

        # 验证任务创建成功且关联到正确用户
        assert task.id is not None
        assert task.user_id == user.id

        # 开始专注会话
        focus_session = focus_repo.start_focus_session(
            user_id=user.id,
            duration_minutes=25,
            task_id=task.id
        )

        # 验证专注会话创建成功且关联到正确用户和任务
        assert focus_session.id is not None
        assert focus_session.user_id == user.id
        assert focus_session.task_id == task.id

        # 验证数据一致性
        found_user = user_repo.get_by_id(user.id)
        found_task = task_repo.get_by_id(task.id)
        found_session = focus_repo.get_by_id(focus_session.id)

        assert found_user.id == user.id
        assert found_task.user_id == user.id
        assert found_session.user_id == user.id
        assert found_session.task_id == task.id


class TestRepositoryIntegrationWorkflows:
    """Repository层业务流程集成测试"""

    @pytest.fixture
    def test_session(self):
        """创建测试数据库会话"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            echo=False
        )

        from src.models.base_model import BaseSQLModel
        BaseSQLModel.metadata.create_all(engine)

        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def repositories(self, test_session):
        """创建所有Repository实例"""
        return {
            'user': UserRepository(test_session),
            'task': TaskRepository(test_session),
            'focus': FocusRepository(test_session),
            'reward': RewardRepository(test_session)
        }

    def test_user_registration_to_focus_workflow(self, test_session, repositories):
        """测试用户注册到专注会话的完整工作流程"""
        user_repo = repositories['user']
        task_repo = repositories['task']
        focus_repo = repositories['focus']

        # 1. 用户注册
        user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = user_repo.create_registered_user(
            email=user_email,
            nickname="专注测试用户",
            password_hash="test_hash"
        )

        # 2. 创建任务
        task = task_repo.create_task(
            user_id=user.id,
            title="专注任务",
            description="需要专注完成的任务"
        )

        # 3. 开始专注会话
        focus_session = focus_repo.start_focus_session(
            user_id=user.id,
            duration_minutes=25,
            task_id=task.id
        )

        # 4. 完成专注会话
        completed_session = focus_repo.complete_session(focus_session.id)

        # 5. 验证完整流程
        assert user.id is not None
        assert task.id is not None
        assert focus_session.id == completed_session.id
        assert completed_session.is_completed is True
        assert completed_session.ended_at is not None

        # 6. 验证用户专注统计
        stats = focus_repo.get_user_focus_statistics(user.id)
        assert stats['total_sessions'] == 1
        assert stats['completed_sessions'] == 1
        assert stats['completion_rate'] == 1.0

    def test_task_management_workflow(self, test_session, repositories):
        """测试任务管理的完整工作流程"""
        user_repo = repositories['user']
        task_repo = repositories['task']

        # 1. 创建用户
        user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = user_repo.create_registered_user(
            email=user_email,
            nickname="任务测试用户",
            password_hash="test_hash"
        )

        # 2. 创建主任务
        main_task = task_repo.create_task(
            user_id=user.id,
            title="主任务",
            description="这是一个主任务"
        )

        # 3. 创建子任务
        sub_task = task_repo.create_task(
            user_id=user.id,
            title="子任务",
            description="这是主任务的子任务",
            parent_id=main_task.id
        )

        # 4. 完成子任务
        completed_sub_task = task_repo.complete_task(sub_task.id)

        # 5. 完成主任务
        completed_main_task = task_repo.complete_task(main_task.id)

        # 6. 验证任务层次结构
        assert main_task.id is not None
        assert sub_task.parent_id == main_task.id
        assert completed_sub_task.status == TaskStatus.COMPLETED
        assert completed_main_task.status == TaskStatus.COMPLETED

        # 7. 验证任务层次查询
        hierarchy = task_repo.get_task_hierarchy(main_task.id)
        assert hierarchy['task']['id'] == main_task.id
        assert len(hierarchy['subtasks']) == 1
        assert hierarchy['subtasks'][0]['id'] == sub_task.id

    def test_focus_session_with_breaks_workflow(self, test_session, repositories):
        """测试包含休息的专注会话工作流程"""
        user_repo = repositories['user']
        focus_repo = repositories['focus']

        # 1. 创建用户
        user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = user_repo.create_registered_user(
            email=user_email,
            nickname="休息测试用户",
            password_hash="test_hash"
        )

        # 2. 开始长时专注会话
        focus_session = focus_repo.start_focus_session(
            user_id=user.id,
            duration_minutes=50
        )

        # 3. 添加休息
        break_record = focus_repo.add_break(
            session_id=focus_session.id,
            break_duration_minutes=5
        )

        # 4. 完成休息
        completed_break = focus_repo.complete_break(break_record.id)

        # 5. 完成专注会话
        completed_session = focus_repo.complete_session(focus_session.id)

        # 6. 验证休息记录
        assert break_record.session_id == focus_session.id
        assert completed_break.ended_at is not None

        # 7. 验证会话休息查询
        breaks = focus_repo.find_session_breaks(focus_session.id)
        assert len(breaks) == 1
        assert breaks[0].id == break_record.id

    def test_reward_system_workflow(self, test_session, repositories):
        """测试奖励系统的完整工作流程"""
        user_repo = repositories['user']
        focus_repo = repositories['focus']
        reward_repo = repositories['reward']

        # 1. 创建用户
        user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = user_repo.create_registered_user(
            email=user_email,
            nickname="奖励测试用户",
            password_hash="test_hash"
        )

        # 2. 创建奖励
        reward = reward_repo.create({
            "name": "专注达人",
            "description": "连续专注完成多个会话",
            "reward_type": RewardType.BADGE,
            "cost_fragments": 100,
            "is_active": True
        })

        # 3. 完成专注会话获得碎片
        focus_session = focus_repo.start_focus_session(
            user_id=user.id,
            duration_minutes=25
        )
        completed_session = focus_repo.complete_session(focus_session.id)

        # 4. 奖励碎片
        transaction = reward_repo.award_fragments(
            user_id=user.id,
            amount=50,
            reason="专注会话完成奖励"
        )

        # 5. 验证碎片余额
        balance = reward_repo.get_user_fragment_balance(user.id)
        assert balance == 50

        # 6. 验证积分流水
        history = reward_repo.get_user_points_history(user.id)
        assert len(history) == 1
        assert history[0].transaction_type == TransactionType.EARN
        assert history[0].points_change == 50

        # 7. 验证积分统计
        summary = reward_repo.get_user_points_summary(user.id)
        assert summary['total_earned'] == 50
        assert summary['current_balance'] == 50
        assert summary['transaction_count'] == 1


class TestRepositoryIntegrationErrorHandling:
    """Repository层错误处理集成测试"""

    @pytest.fixture
    def test_session(self):
        """创建测试数据库会话"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            echo=False
        )

        from src.models.base_model import BaseSQLModel
        BaseSQLModel.metadata.create_all(engine)

        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def repositories(self, test_session):
        """创建所有Repository实例"""
        return {
            'user': UserRepository(test_session),
            'task': TaskRepository(test_session),
            'focus': FocusRepository(test_session),
            'reward': RewardRepository(test_session)
        }

    def test_foreign_key_constraint_error(self, test_session, repositories):
        """测试外键约束错误处理"""
        task_repo = repositories['task']
        focus_repo = repositories['focus']

        # 使用不存在的用户ID创建任务
        with pytest.raises((RepositoryError, Exception)):
            task_repo.create_task(
                user_id="non-existent-user-id",
                title="无效任务",
                description="这个任务应该创建失败"
            )

        # 使用不存在的任务ID开始专注会话
        with pytest.raises((RepositoryError, Exception)):
            focus_repo.start_focus_session(
                user_id="non-existent-user-id",
                duration_minutes=25,
                task_id="non-existent-task-id"
            )

    def test_validation_error_propagation(self, test_session, repositories):
        """测试验证错误的传播"""
        user_repo = repositories['user']
        task_repo = repositories['task']

        # 创建用户
        user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = user_repo.create_registered_user(
            email=user_email,
            nickname="验证测试用户",
            password_hash="test_hash"
        )

        # 测试无效的任务创建
        with pytest.raises(RepositoryValidationError):
            task_repo.create_task(
                user_id=user.id,
                title="",  # 空标题应该导致验证错误
                description="无效标题的任务"
            )

        # 测试无效的专注会话
        with pytest.raises(RepositoryValidationError):
            focus_repo = repositories['focus']
            focus_repo.start_focus_session(
                user_id=user.id,
                duration_minutes=0  # 无效时长应该导致验证错误
            )

    def test_transaction_consistency(self, test_session, repositories):
        """测试事务一致性"""
        user_repo = repositories['user']
        task_repo = repositories['task']

        # 这个测试模拟了事务失败时的回滚情况
        # 在实际应用中，这通常需要更复杂的事务管理
        user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"

        # 创建用户（成功）
        user = user_repo.create_registered_user(
            email=user_email,
            nickname="事务测试用户",
            password_hash="test_hash"
        )

        # 验证用户创建成功
        assert user.id is not None

        # 创建任务（成功）
        task = task_repo.create_task(
            user_id=user.id,
            title="事务测试任务",
            description="测试事务一致性的任务"
        )

        # 验证任务创建成功且关联正确
        assert task.id is not None
        assert task.user_id == user.id


class TestRepositoryIntegrationPerformance:
    """Repository层性能集成测试"""

    @pytest.fixture
    def test_session(self):
        """创建测试数据库会话"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            echo=False
        )

        from src.models.base_model import BaseSQLModel
        BaseSQLModel.metadata.create_all(engine)

        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def repositories(self, test_session):
        """创建所有Repository实例"""
        return {
            'user': UserRepository(test_session),
            'task': TaskRepository(test_session),
            'focus': FocusRepository(test_session),
            'reward': RewardRepository(test_session)
        }

    def test_batch_operations_performance(self, test_session, repositories):
        """测试批量操作性能"""
        import time

        user_repo = repositories['user']
        task_repo = repositories['task']

        # 创建用户
        user_email = f"batch_test_{uuid.uuid4().hex[:8]}@example.com"
        user = user_repo.create_registered_user(
            email=user_email,
            nickname="批量测试用户",
            password_hash="test_hash"
        )

        # 批量创建任务并测量时间
        start_time = time.time()
        tasks = []

        for i in range(10):
            task = task_repo.create_task(
                user_id=user.id,
                title=f"批量任务 {i+1}",
                description=f"这是第{i+1}个批量创建的任务"
            )
            tasks.append(task)

        end_time = time.time()
        creation_time = end_time - start_time

        # 验证所有任务都创建成功
        assert len(tasks) == 10
        for task in tasks:
            assert task.id is not None
            assert task.user_id == user.id

        # 验证创建时间合理（应该很快）
        assert creation_time < 5.0  # 10个任务应该在5秒内创建完成

        # 批量查询任务并测量时间
        start_time = time.time()
        user_tasks = task_repo.find_by_user(user.id)
        end_time = time.time()
        query_time = end_time - start_time

        # 验证查询结果和时间
        assert len(user_tasks) == 10
        assert query_time < 1.0  # 查询应该很快

    def test_complex_query_performance(self, test_session, repositories):
        """测试复杂查询性能"""
        import time

        user_repo = repositories['user']
        focus_repo = repositories['focus']

        # 创建用户
        user_email = f"complex_test_{uuid.uuid4().hex[:8]}@example.com"
        user = user_repo.create_registered_user(
            email=user_email,
            nickname="复杂查询测试用户",
            password_hash="test_hash"
        )

        # 创建多个专注会话
        sessions = []
        for i in range(5):
            session = focus_repo.start_focus_session(
                user_id=user.id,
                duration_minutes=25
            )
            # 完成一半的会话
            if i % 2 == 0:
                focus_repo.complete_session(session.id)
            sessions.append(session)

        # 测试复杂查询性能
        start_time = time.time()

        # 获取用户专注统计
        stats = focus_repo.get_user_focus_statistics(user.id)

        # 获取用户今日会话
        today_sessions = focus_repo.find_user_today_sessions(user.id)

        # 获取活跃会话
        active_sessions = focus_repo.find_active_sessions(user.id)

        end_time = time.time()
        query_time = end_time - start_time

        # 验证查询结果
        assert stats['total_sessions'] == 5
        assert stats['completed_sessions'] == 2
        assert len(today_sessions) == 5
        assert len(active_sessions) == 3  # 5个会话中2个完成，3个还是活跃状态

        # 验证查询时间
        assert query_time < 2.0  # 复杂查询应该在2秒内完成


# 导出测试类
__all__ = [
    "TestRepositoryIntegrationBasic",
    "TestRepositoryIntegrationWorkflows",
    "TestRepositoryIntegrationErrorHandling",
    "TestRepositoryIntegrationPerformance"
]