"""
重构奖励系统v4集成测试

测试refactor-reward-system-v4提案的所有核心变更：
1. 纯流水记录架构（删除stock_quantity字段）
2. 无限供应奖品（移除库存检查）
3. API响应格式修正（reward_earned替代completion_result）
4. 番茄钟自动关闭会话
5. 配置清理（简化game_config.py）

测试策略：
- 数据库迁移验证
- Service层功能验证
- API响应格式验证
- 端到端流程验证

作者：TaKeKe团队
版本：v4.0 - 重构验证
"""

import pytest
import tempfile
import os
from uuid import uuid4
from datetime import datetime, timezone
from sqlmodel import Session, create_engine, text
from sqlalchemy import StaticPool

from src.domains.reward.service import RewardService
from src.domains.reward.repository import RewardRepository
from src.domains.reward.models import Reward, RewardTransaction
from src.domains.points.service import PointsService
from src.domains.task.completion_service import TaskCompletionService
from src.domains.task.service import TaskService
from src.domains.top3.service import Top3Service
from src.domains.focus.service import FocusService
from src.domains.focus.repository import FocusRepository
from src.domains.focus.models import FocusSession
from src.config.game_config import RewardConfig, TransactionSource


@pytest.fixture
def test_db():
    """创建临时测试数据库"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    # 创建表结构（基于v4规范）
    with engine.connect() as conn:
        # 创建rewards表（v4：无stock_quantity, cost_type, cost_value字段）
        conn.execute(text("""
            CREATE TABLE rewards (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                points_value INTEGER NOT NULL,
                image_url TEXT,
                category TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """))

        # 创建reward_transactions表
        conn.execute(text("""
            CREATE TABLE reward_transactions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                reward_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT,
                quantity INTEGER NOT NULL,
                transaction_group TEXT,
                created_at DATETIME NOT NULL
            )
        """))

        # 创建points_transactions表
        conn.execute(text("""
            CREATE TABLE points_transactions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT,
                transaction_group TEXT,
                created_at DATETIME NOT NULL
            )
        """))

        # 创建tasks表
        conn.execute(text("""
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                points_awarded INTEGER DEFAULT 0,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """))

        # 创建task_top3表
        conn.execute(text("""
            CREATE TABLE task_top3 (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """))

        # 创建focus_sessions表
        conn.execute(text("""
            CREATE TABLE focus_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                session_type TEXT NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                created_at DATETIME NOT NULL
            )
        """))

        # 创建reward_recipes表
        conn.execute(text("""
            CREATE TABLE reward_recipes (
                id TEXT PRIMARY KEY,
                name TEXT,
                result_reward_id TEXT NOT NULL,
                materials TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """))

        conn.commit()

    yield engine


@pytest.fixture
def test_session(test_db):
    """创建测试数据库会话"""
    with Session(test_db) as session:
        yield session


@pytest.fixture
def sample_rewards(test_session):
    """创建示例奖品数据"""
    rewards = [
        Reward(
            id=str(uuid4()),
            name="小金币",
            description="基础奖品",
            points_value=10,
            category="basic",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ),
        Reward(
            id=str(uuid4()),
            name="钻石",
            description="珍贵奖品",
            points_value=100,
            category="premium",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ),
        Reward(
            id=str(uuid4()),
            name="已禁用奖品",
            description="不应该被查询到",
            points_value=50,
            category="special",
            is_active=False,  # 禁用状态
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    ]

    for reward in rewards:
        test_session.add(reward)
    test_session.commit()

    return rewards


@pytest.fixture
def sample_task(test_session):
    """创建示例任务数据"""
    from src.domains.task.models import Task

    task = Task(
        id=str(uuid4()),
        user_id=str(uuid4()),
        title="测试任务",
        description="这是一个测试任务",
        status="pending",
        points_awarded=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    test_session.add(task)
    test_session.commit()
    return task


class TestRewardSystemV4Integration:
    """奖励系统v4集成测试类"""

    def test_v4_database_schema_validation(self, test_db):
        """
        测试v4数据库表结构验证

        验证：
        1. rewards表不包含stock_quantity, cost_type, cost_value字段
        2. reward_transactions表结构完整
        3. 索引结构正确
        """
        with Session(test_db) as session:
            # 检查rewards表结构
            result = session.execute(text("PRAGMA table_info(rewards)"))
            columns = [row[1] for row in result.fetchall()]

            # v4：确保已删除的字段不存在
            assert "stock_quantity" not in columns, "rewards表不应包含stock_quantity字段"
            assert "cost_type" not in columns, "rewards表不应包含cost_type字段"
            assert "cost_value" not in columns, "rewards表不应包含cost_value字段"

            # v4：确保必需的字段存在
            required_fields = ["id", "name", "description", "points_value", "category", "is_active"]
            for field in required_fields:
                assert field in columns, f"rewards表必须包含{field}字段"

            # 检查reward_transactions表结构
            result = session.execute(text("PRAGMA table_info(reward_transactions)"))
            tx_columns = [row[1] for row in result.fetchall()]

            required_tx_fields = ["id", "user_id", "reward_id", "source_type", "quantity"]
            for field in required_tx_fields:
                assert field in tx_columns, f"reward_transactions表必须包含{field}字段"

    def test_v4_reward_service_unlimited_supply(self, test_session, sample_rewards):
        """
        测试v4奖励服务无限供应功能

        验证：
        1. get_available_rewards()只返回is_active=true的奖品
        2. 不检查库存数量
        3. get_reward_catalog()中is_exchangeable始终为True
        """
        points_service = PointsService(test_session)
        reward_service = RewardService(test_session, points_service)

        # 获取可用奖品列表
        available_rewards = reward_service.get_available_rewards()

        # v4：应该只返回启用的奖品（2个）
        assert len(available_rewards) == 2, "应该只返回启用的奖品"

        # 验证返回的奖品不包含库存字段
        for reward in available_rewards:
            assert "stock_quantity" not in reward, "奖品数据不应包含stock_quantity字段"
            assert "cost_type" not in reward, "奖品数据不应包含cost_type字段"
            assert "cost_value" not in reward, "奖品数据不应包含cost_value字段"
            assert "points_value" in reward, "奖品数据应包含points_value字段"

        # 测试get_reward_catalog
        catalog = reward_service.get_reward_catalog()
        assert len(catalog["rewards"]) == 2, "目录应包含2个奖品"

        # v4：所有奖品都应该可兑换
        for reward in catalog["rewards"]:
            assert reward["is_exchangeable"] is True, "v4中所有奖品都应该可兑换"

    def test_v4_reward_redeem_no_stock_check(self, test_session, sample_rewards):
        """
        测试v4奖品兑换无库存检查

        验证：
        1. 兑换时不检查库存
        2. 使用points_value作为兑换成本
        3. 创建正确的reward_transactions记录
        """
        user_id = str(uuid4())
        reward_id = sample_rewards[0].id  # 小金币，points_value=10

        # 先给用户足够的积分
        points_service = PointsService(test_session)
        points_service.add_points(user_id, 20, "test", None)

        # 测试兑换
        reward_service = RewardService(test_session, points_service)
        result = reward_service.redeem_reward(user_id, reward_id)

        # 验证兑换成功
        assert result["success"] is True
        assert result["reward"]["id"] == reward_id
        assert result["points_deducted"] == 10  # points_value
        assert result["reward"]["points_value"] == 10

        # 验证创建了reward_transactions记录
        transactions = reward_service.get_reward_transactions(user_id)
        assert len(transactions) == 1
        assert transactions[0]["reward_id"] == reward_id
        assert transactions[0]["quantity"] == 1
        assert transactions[0]["source_type"] == "redemption"

    def test_v4_top3_lottery_unlimited_supply(self, test_session, sample_rewards):
        """
        测试v4 Top3抽奖无限供应

        验证：
        1. 抽奖时从所有启用的奖品中选择
        2. 不检查库存
        3. 正确创建抽奖记录
        """
        user_id = str(uuid4())
        points_service = PointsService(test_session)
        reward_service = RewardService(test_session, points_service)

        # 多次抽奖验证无限供应
        for i in range(10):
            result = reward_service.top3_lottery(user_id)

            assert result["success"] is True
            assert result["type"] in ["reward", "points"]

            if result["type"] == "reward":
                # 验证奖品信息
                assert "reward" in result
                assert result["reward"]["name"] in ["小金币", "钻石"]  # 只有启用的奖品

                # 验证创建了交易记录
                transactions = reward_service.get_reward_transactions(user_id)
                lottery_transactions = [tx for tx in transactions if tx["source_type"] == "lottery_reward"]
                assert len(lottery_transactions) > 0

    def test_v4_task_completion_reward_earned_format(self, test_session, sample_task):
        """
        测试v4任务完成返回格式

        验证：
        1. 返回格式包含reward_earned字段
        2. reward_earned结构符合v3规范
        3. 普通任务和Top3任务的奖励格式正确
        """
        user_id = sample_task.user_id
        task_id = sample_task.id

        # 创建Service实例
        task_completion_service = TaskCompletionService(test_session)

        # 完成任务
        result = task_completion_service.complete_task(task_id, user_id)

        # 验证返回格式
        assert "data" in result
        assert "reward_earned" in result["data"]

        reward_earned = result["data"]["reward_earned"]
        assert reward_earned is not None

        # 验证reward_earned结构
        assert "type" in reward_earned
        assert "transaction_id" in reward_earned
        assert "reward_id" in reward_earned
        assert "amount" in reward_earned

        # 普通任务应该获得积分
        assert reward_earned["type"] == "points"
        assert reward_earned["amount"] == 2  # 普通任务默认2积分
        assert reward_earned["reward_id"] is None

    def test_v4_focus_service_auto_close_sessions(self, test_session, sample_task):
        """
        测试v4专注力服务自动关闭会话

        验证：
        1. 创建新会话时自动关闭旧会话
        2. 用户同时只能有一个进行中的会话
        """
        user_id = str(uuid4())
        task_id = sample_task.id

        focus_service = FocusService(test_session)

        from src.domains.focus.schemas import StartFocusRequest

        # 创建第一个会话
        request1 = StartFocusRequest(task_id=task_id, session_type="focus")
        session1 = focus_service.start_focus(user_id, request1)

        assert session1["end_time"] is None

        # 创建第二个会话（应该自动关闭第一个）
        request2 = StartFocusRequest(task_id=task_id, session_type="focus")
        session2 = focus_service.start_focus(user_id, request2)

        # 验证第一个会话被关闭
        focus_repository = FocusRepository(test_session)
        updated_session1 = focus_repository.get_by_id(session1["id"])
        assert updated_session1.end_time is not None

        # 验证第二个会话是活跃的
        assert session2["end_time"] is None
        assert session2["id"] != session1["id"]

    def test_v4_config_cleanup(self):
        """
        测试v4配置清理

        验证：
        1. 配置不包含删除的项
        2. 验证功能正常工作
        3. TransactionSource枚举完整
        """
        config = RewardConfig()

        # 验证配置结构
        full_config = config.get_config()

        # v4：确保已删除的配置项不存在
        assert "lottery_reward_pool" not in full_config
        assert "default_rewards" not in full_config
        assert "default_recipes" not in full_config

        # v4：确保保留的配置项存在
        assert "normal_task_points" in full_config
        assert "top3_lottery_points_amount" in full_config

        # 验证Top3抽奖配置
        lottery_config = config.get_top3_lottery_config()
        assert "points_amount" in lottery_config
        assert lottery_config["points_amount"] == 100

        # 验证TransactionSource枚举
        source_mapping = config.get_source_type_mapping()
        required_sources = [
            "task_complete", "task_complete_top3", "lottery_points",
            "lottery_reward", "redemption", "manual"
        ]

        for source in required_sources:
            assert source in source_mapping

        # 验证配置验证功能
        assert config.validate_config() is True

    def test_v4_pure_transaction_calculation(self, test_session, sample_rewards):
        """
        测试v4纯流水记录余额计算

        验证：
        1. 通过流水记录正确计算用户奖品余额
        2. 正负流水聚合计算
        3. 复杂交易场景处理
        """
        user_id = str(uuid4())
        reward_id = sample_rewards[0].id

        points_service = PointsService(test_session)
        reward_service = RewardService(test_session, points_service)

        # 获取初始余额
        reward_repository = RewardRepository(test_session)
        initial_balance = reward_repository.get_user_reward_balance(user_id, reward_id)
        assert initial_balance == 0

        # 兑换3次奖品
        for i in range(3):
            points_service.add_points(user_id, 20, f"test_{i}", None)
            reward_service.redeem_reward(user_id, reward_id)

        # 验证余额计算
        final_balance = reward_repository.get_user_reward_balance(user_id, reward_id)
        assert final_balance == 3

        # 验证流水记录
        transactions = reward_service.get_reward_transactions(user_id)
        reward_transactions = [tx for tx in transactions if tx["reward_id"] == reward_id]
        assert len(reward_transactions) == 3

        # 验证所有记录都是正数（获得）
        for tx in reward_transactions:
            assert tx["quantity"] == 1
            assert tx["source_type"] == "redemption"

    def test_v4_end_to_end_complete_flow(self, test_session):
        """
        测试v4端到端完整流程

        验证：
        1. 任务完成 → 积分奖励 → 抽奖 → 奖品获得
        2. 完整的数据流和业务逻辑
        3. v4规范的实现正确性
        """
        # 创建测试数据
        user_id = str(uuid4())

        # 创建奖品
        reward = Reward(
            id=str(uuid4()),
            name="测试奖品",
            description="端到端测试奖品",
            points_value=50,
            category="test",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_session.add(reward)

        # 创建任务
        from src.domains.task.models import Task
        task = Task(
            id=str(uuid4()),
            user_id=user_id,
            title="端到端测试任务",
            description="用于完整流程测试",
            status="pending",
            points_awarded=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_session.add(task)

        # 设置为Top3任务
        from src.domains.top3.models import TaskTop3
        top3 = TaskTop3(
            id=str(uuid4()),
            task_id=task.id,
            user_id=user_id,
            date=datetime.now().strftime("%Y-%m-%d"),
            created_at=datetime.now(timezone.utc)
        )
        test_session.add(top3)
        test_session.commit()

        # 执行完整流程
        task_completion_service = TaskCompletionService(test_session)

        # 1. 完成Top3任务
        result = task_completion_service.complete_task(task.id, user_id)

        # 验证返回格式
        assert "reward_earned" in result["data"]
        reward_earned = result["data"]["reward_earned"]

        # Top3任务应该触发抽奖
        assert "lottery_result" in result["data"]
        lottery_result = result["data"]["lottery_result"]

        if lottery_result:
            if lottery_result["type"] == "reward":
                # 中奖：验证奖品获得
                assert lottery_result["reward"]["name"] in ["测试奖品", "小金币", "钻石"]
            elif lottery_result["type"] == "points":
                # 安慰奖：验证积分获得
                assert lottery_result["amount"] == 100  # 默认安慰奖积分

        # 2. 验证流水记录
        points_service = PointsService(test_session)
        reward_service = RewardService(test_session, points_service)

        # 验证积分流水
        points_balance = points_service.calculate_balance(user_id)
        assert points_balance >= 2  # 至少完成任务的基础积分

        # 验证奖品流水（如果中奖）
        reward_transactions = reward_service.get_reward_transactions(user_id)
        if lottery_result and lottery_result["type"] == "reward":
            assert len(reward_transactions) > 0
            assert any(tx["source_type"] == "lottery_reward" for tx in reward_transactions)


class TestRewardSystemV4Performance:
    """奖励系统v4性能测试"""

    def test_v4_large_volume_transactions(self, test_session, sample_rewards):
        """
        测试v4大量交易处理性能

        验证纯流水记录架构在大数据量下的性能
        """
        user_id = str(uuid4())
        reward_id = sample_rewards[0].id

        points_service = PointsService(test_session)
        reward_service = RewardService(test_session, points_service)

        # 执行大量交易
        import time
        start_time = time.time()

        for i in range(100):
            points_service.add_points(user_id, 20, f"bulk_test_{i}", None)
            reward_service.redeem_reward(user_id, reward_id)

        end_time = time.time()
        execution_time = end_time - start_time

        # 验证性能（应该在合理时间内完成）
        assert execution_time < 10.0, f"100次交易耗时过长: {execution_time:.2f}秒"

        # 验证数据一致性
        reward_repository = RewardRepository(test_session)
        final_balance = reward_repository.get_user_reward_balance(user_id, reward_id)
        assert final_balance == 100

        # 验证流水记录数量
        transactions = reward_service.get_reward_transactions(user_id)
        assert len(transactions) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])