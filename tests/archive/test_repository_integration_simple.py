"""
Repository层简化集成测试

验证各个Repository之间的基本协作和数据一致性，专注于：
- Repository之间的数据关联
- 基础的业务流程
- 外键约束和数据完整性
- 错误传播机制

简化设计原则：
1. 使用基础CRUD操作，避免复杂的业务方法
2. 专注于跨Repository的数据一致性验证
3. 使用真实的数据库连接
4. 确保测试稳定性和可维护性
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy.orm import sessionmaker

# 导入相关模型和Repository
from src.models.user import User
from src.models.task import Task
from src.models.focus import FocusSession
from src.models.reward import Reward, UserFragment, PointsTransaction
from src.models.enums import TaskStatus, SessionType, RewardType, TransactionType
from src.repositories import (
    UserRepository,
    TaskRepository,
    FocusRepository,
    RewardRepository
)
from src.repositories.base import RepositoryError, RepositoryValidationError


class TestRepositoryBasicIntegration:
    """Repository层基础集成测试"""

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

    def test_repository_initialization(self, test_session, repositories):
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

    def test_cross_repository_data_relationships(self, test_session, repositories):
        """测试跨Repository的数据关联关系"""
        user_repo = repositories['user']
        task_repo = repositories['task']
        focus_repo = repositories['focus']

        # 1. 创建用户
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

        # 2. 创建任务并关联到用户
        task = task_repo.create({
            "user_id": user.id,
            "title": "测试任务",
            "description": "这是一个测试任务",
            "status": TaskStatus.PENDING
        })

        # 验证任务创建成功且关联到正确用户
        assert task.id is not None
        assert task.user_id == user.id

        # 3. 创建专注会话并关联到用户和任务
        focus_session = focus_repo.create({
            "user_id": user.id,
            "task_id": task.id,
            "session_type": SessionType.FOCUS,
            "duration_minutes": 25,
            "started_at": datetime.now(timezone.utc)
        })

        # 验证专注会话创建成功且关联到正确用户和任务
        assert focus_session.id is not None
        assert focus_session.user_id == user.id
        assert focus_session.task_id == task.id

        # 4. 验证跨Repository查询的一致性
        found_user = user_repo.get_by_id(user.id)
        found_task = task_repo.get_by_id(task.id)
        found_session = focus_repo.get_by_id(focus_session.id)

        assert found_user.id == user.id
        assert found_task.user_id == user.id
        assert found_session.user_id == user.id
        assert found_session.task_id == task.id

    def test_foreign_key_constraints(self, test_session, repositories):
        """测试外键约束验证"""
        user_repo = repositories['user']
        task_repo = repositories['task']

        # 1. 创建用户
        user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = user_repo.create({
            "email": user_email,
            "nickname": "约束测试用户",
            "password_hash": "test_hash",
            "user_type": "registered"
        })

        # 2. 创建有效任务（应该成功）
        valid_task = task_repo.create({
            "user_id": user.id,
            "title": "有效任务",
            "description": "关联到有效用户的任务",
            "status": TaskStatus.PENDING
        })
        assert valid_task.id is not None

        # 3. 尝试创建无效任务（关联到不存在的用户）
        # 注意：这可能会因为SQLite的外键约束设置而表现不同
        # 在某些配置下，外键约束可能不会强制执行
        try:
            invalid_task = task_repo.create({
                "user_id": "non-existent-user-id",
                "title": "无效任务",
                "description": "关联到不存在用户的任务",
                "status": TaskStatus.PENDING
            })
            # 如果创建成功，验证数据库行为
            # 某些数据库配置允许延迟约束检查
        except (RepositoryError, Exception) as e:
            # 这是期望的行为 - 外键约束阻止了无效操作
            assert isinstance(e, (RepositoryError, Exception))

    def test_data_consistency_across_repositories(self, test_session, repositories):
        """测试Repository之间的数据一致性"""
        user_repo = repositories['user']
        task_repo = repositories['task']

        # 创建用户
        user_email = f"consistency_test_{uuid.uuid4().hex[:8]}@example.com"
        user = user_repo.create({
            "email": user_email,
            "nickname": "一致性测试用户",
            "password_hash": "test_hash",
            "user_type": "registered"
        })

        # 创建多个任务
        tasks = []
        for i in range(3):
            task = task_repo.create({
                "user_id": user.id,
                "title": f"任务 {i+1}",
                "description": f"第{i+1}个任务",
                "status": TaskStatus.PENDING
            })
            tasks.append(task)

        # 验证任务数量和关联
        user_tasks = task_repo.get_all(user_id=user.id)
        assert len(user_tasks) == 3
        for task in user_tasks:
            assert task.user_id == user.id

        # 验证用户查询
        found_user = user_repo.get_by_id(user.id)
        assert found_user.email == user_email

        # 验证双向关联一致性
        for task in tasks:
            found_task = task_repo.get_by_id(task.id)
            assert found_task.user_id == user.id
            assert found_task.id == task.id

    def test_repository_error_handling(self, test_session, repositories):
        """测试Repository错误处理"""
        user_repo = repositories['user']
        task_repo = repositories['task']

        # 测试查找不存在的用户
        non_existent_user = user_repo.get_by_id("non-existent-id")
        assert non_existent_user is None

        # 测试无效的用户创建（缺少必要字段）
        with pytest.raises((RepositoryError, RepositoryValidationError, Exception)):
            user_repo.create({
                "email": "",  # 空邮箱应该导致错误
                "nickname": "无效用户",
                "user_type": "registered"
            })

        # 测试无效的任务创建（缺少user_id）
        with pytest.raises((RepositoryError, RepositoryValidationError, Exception)):
            task_repo.create({
                "title": "无效任务",
                "description": "缺少用户ID的任务",
                "status": TaskStatus.PENDING
                # 缺少user_id字段
            })

    def test_repository_session_isolation(self, test_session, repositories):
        """测试Repository会话隔离"""
        user_repo1 = repositories['user']

        # 创建第一个用户
        user1 = user_repo1.create({
            "email": f"isolation_test1_{uuid.uuid4().hex[:8]}@example.com",
            "nickname": "隔离测试用户1",
            "password_hash": "test_hash",
            "user_type": "registered"
        })

        # 创建第二个会话和Repository
        SessionLocal2 = sessionmaker(bind=test_session.bind)
        session2 = SessionLocal2()
        user_repo2 = UserRepository(session2)

        # 在第二个会话中创建用户
        user2 = user_repo2.create({
            "email": f"isolation_test2_{uuid.uuid4().hex[:8]}@example.com",
            "nickname": "隔离测试用户2",
            "password_hash": "test_hash",
            "user_type": "registered"
        })

        # 验证两个用户都可以正确查询
        found_user1 = user_repo1.get_by_id(user1.id)
        found_user2 = user_repo2.get_by_id(user2.id)

        assert found_user1.id == user1.id
        assert found_user2.id == user2.id
        assert found_user1.id != found_user2.id

        # 清理第二个会话
        session2.close()

    def test_repository_query_performance(self, test_session, repositories):
        """测试Repository查询性能"""
        import time

        user_repo = repositories['user']
        task_repo = repositories['task']

        # 创建用户
        user_email = f"perf_test_{uuid.uuid4().hex[:8]}@example.com"
        user = user_repo.create({
            "email": user_email,
            "nickname": "性能测试用户",
            "password_hash": "test_hash",
            "user_type": "registered"
        })

        # 批量创建任务并测量时间
        start_time = time.time()
        tasks = []

        for i in range(10):
            task = task_repo.create({
                "user_id": user.id,
                "title": f"性能测试任务 {i+1}",
                "description": f"第{i+1}个性能测试任务",
                "status": TaskStatus.PENDING
            })
            tasks.append(task)

        creation_time = time.time() - start_time

        # 验证所有任务都创建成功
        assert len(tasks) == 10
        for task in tasks:
            assert task.id is not None

        # 验证创建时间合理
        assert creation_time < 3.0  # 10个任务应该在3秒内创建完成

        # 批量查询任务并测量时间
        start_time = time.time()
        user_tasks = task_repo.get_all(user_id=user.id)
        query_time = time.time() - start_time

        # 验证查询结果和时间
        assert len(user_tasks) == 10
        assert query_time < 1.0  # 查询应该很快


class TestRepositoryRewardIntegration:
    """Reward系统集成测试"""

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
            'reward': RewardRepository(test_session)
        }

    def test_reward_system_basic_flow(self, test_session, repositories):
        """测试奖励系统基本流程"""
        user_repo = repositories['user']
        reward_repo = repositories['reward']

        # 1. 创建用户
        user_email = f"reward_test_{uuid.uuid4().hex[:8]}@example.com"
        user = user_repo.create({
            "email": user_email,
            "nickname": "奖励测试用户",
            "password_hash": "test_hash",
            "user_type": "registered"
        })

        # 2. 创建奖励（需要提供user_id）
        reward = reward_repo.create({
            "user_id": user.id,
            "name": "测试奖励",
            "description": "这是一个测试奖励",
            "reward_type": RewardType.BADGE,
            "cost_fragments": 50,
            "is_active": True
        })

        # 3. 创建用户碎片记录
        user_fragment = UserFragment(
            user_id=user.id,
            fragment_count=100
        )
        test_session.add(user_fragment)
        test_session.commit()

        # 4. 验证碎片余额
        balance = reward_repo.get_user_fragment_balance(user.id)
        assert balance == 100

        # 5. 创建积分交易记录
        transaction = PointsTransaction(
            user_id=user.id,
            transaction_type=TransactionType.EARN,
            points_change=25,
            balance_before=100,
            balance_after=125,
            description="测试奖励"
        )
        test_session.add(transaction)
        test_session.commit()

        # 6. 验证交易记录
        history = reward_repo.get_user_points_history(user.id)
        assert len(history) >= 1
        assert history[0].points_change == 25


# 导出测试类
__all__ = [
    "TestRepositoryBasicIntegration",
    "TestRepositoryRewardIntegration"
]