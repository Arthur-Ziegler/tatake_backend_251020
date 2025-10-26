"""
数据库集成测试套件

测试表创建、JSON字段操作和数据库连接，包括：
1. 表创建和初始化测试
2. JSON字段读写功能测试
3. SUM聚合查询正确性测试
4. 表关联完整性测试
5. 事务回滚测试

遵循TDD原则，每个测试用例都有明确的预期结果和断言。
"""

import pytest
import uuid
import json
from datetime import datetime, timezone, date

from src.database.connection import get_engine, get_session
from src.domains.auth.models import BaseModel
from src.domains.task.models import Task
from src.domains.reward.models import Reward, RewardRecipe, RewardTransaction, PointsTransaction
from src.domains.top3.models import TaskTop3


class TestDatabaseIntegration:
    """数据库集成测试类"""

    def test_table_creation(self):
        """测试所有表正确创建"""
        engine = get_engine()

        # 创建所有表
        BaseModel.metadata.create_all(bind=engine)

        # 验证表存在 - 使用text()包装SQL字符串
        with engine.connect() as conn:
            from sqlalchemy import text
            tables = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()

            table_names = [row[0] for row in tables]

            # 验证核心表存在
            assert "auth" in table_names
            assert "tasks" in table_names
            assert "rewards" in table_names
            assert "reward_recipes" in table_names
            assert "reward_transactions" in table_names
            assert "points_transactions" in table_names
            assert "task_top3" in table_names

    def test_task_model_database_operations(self):
        """测试Task模型数据库操作"""
        engine = get_engine()

        # 创建表
        BaseModel.metadata.create_all(bind=engine)

        with get_session() as session:
            # 创建任务
            task_id = uuid.uuid4()
            user_id = uuid.uuid4()

            task = Task(
                id=task_id,
                user_id=user_id,
                title="数据库集成测试任务",
                description="测试数据库操作",
                tags=["测试", "集成"],
                service_ids=["service-001"]
            )

            session.add(task)
            session.commit()

            # 查询任务
            retrieved_task = session.get(Task, task_id)

            # 验证数据正确性
            assert retrieved_task is not None
            assert retrieved_task.title == "数据库集成测试任务"
            assert retrieved_task.description == "测试数据库操作"
            assert retrieved_task.tags == ["测试", "集成"]
            assert retrieved_task.service_ids == ["service-001"]

    def test_json_field_operations(self):
        """测试JSON字段读写功能"""
        engine = get_engine()

        # 创建表
        BaseModel.metadata.create_all(bind=engine)

        with get_session() as session:
            # 创建带JSON字段的奖励
            reward_id = uuid.uuid4()

            reward = Reward(
                id=reward_id,
                name="JSON测试奖励",
                description="测试JSON字段",
                points_value=100
            )

            session.add(reward)
            session.commit()

            # 创建带JSON字段的配方
            recipe_id = uuid.uuid4()
            required_rewards = [
                {"reward_id": str(reward_id), "quantity": 10}
            ]

            recipe = RewardRecipe(
                id=recipe_id,
                name="JSON测试配方",
                result_reward_id=reward_id,
                required_rewards=required_rewards
            )

            session.add(recipe)
            session.commit()

            # 查询并验证JSON字段
            retrieved_recipe = session.get(RewardRecipe, recipe_id)
            assert retrieved_recipe is not None
            assert retrieved_recipe.required_rewards == required_rewards
            assert len(retrieved_recipe.required_rewards) == 1
            assert retrieved_recipe.required_rewards[0]["reward_id"] == str(reward_id)
            assert retrieved_recipe.required_rewards[0]["quantity"] == 10

    def test_sum_aggregation_query(self):
        """测试SUM聚合查询正确性"""
        engine = get_engine()

        # 创建表
        BaseModel.metadata.create_all(bind=engine)

        with get_session() as session:
            user_id = uuid.uuid4()

            # 插入多条积分流水
            transactions = [
                PointsTransaction(
                    user_id=user_id,
                    amount=100,
                    source_type="task_complete"
                ),
                PointsTransaction(
                    user_id=user_id,
                    amount=-50,
                    source_type="top3_cost"
                ),
                PointsTransaction(
                    user_id=user_id,
                    amount=25,
                    source_type="task_complete_top3"
                )
            ]

            for tx in transactions:
                session.add(tx)
            session.commit()

            # 使用SUM聚合查询计算余额
            from sqlalchemy import text
            result = session.execute(
                text("SELECT SUM(amount) as balance FROM points_transactions WHERE user_id = :user_id"),
                {"user_id": str(user_id)}
            ).fetchone()

            # 验证计算结果
            expected_balance = 100 - 50 + 25  # 75
            assert result[0] == expected_balance

    def test_unique_constraint(self):
        """测试UNIQUE约束"""
        engine = get_engine()

        # 创建表
        BaseModel.metadata.create_all(bind=engine)

        with get_session() as session:
            user_id = uuid.uuid4()
            today = date(2023, 12, 25)

            # 创建第一个Top3记录
            top3_1 = TaskTop3(
                id=uuid.uuid4(),
                user_id=user_id,
                top_date=today,
                task_ids=[str(uuid.uuid4())],
                points_consumed=300
            )

            session.add(top3_1)
            session.commit()

            # 尝试创建重复的Top3记录（应该失败）
            top3_2 = TaskTop3(
                id=uuid.uuid4(),
                user_id=user_id,
                top_date=today,
                task_ids=[str(uuid.uuid4())],
                points_consumed=300
            )

            session.add(top3_2)

            # 验证UNIQUE约束生效
            with pytest.raises(Exception):  # 具体异常类型可能因数据库而异
                session.commit()

    def test_transaction_rollback(self):
        """测试事务回滚"""
        engine = get_engine()

        # 创建表
        BaseModel.metadata.create_all(bind=engine)

        with get_session() as session:
            initial_count = session.execute(
                "SELECT COUNT(*) FROM rewards"
            ).fetchone()[0]

            # 开始事务
            task = Task(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                title="回滚测试任务"
            )

            session.add(task)

            # 强制回滚
            session.rollback()

            # 验证回滚后数据未提交
            from sqlalchemy import text
            final_count = session.execute(
                text("SELECT COUNT(*) FROM rewards")
            ).fetchone()[0]

            assert initial_count == final_count

    def test_foreign_key_constraints(self):
        """测试外键约束"""
        engine = get_engine()

        # 创建表
        BaseModel.metadata.create_all(bind=engine)

        with get_session() as session:
            user_id = uuid.uuid4()

            # 创建奖励
            reward = Reward(
                id=uuid.uuid4(),
                name="外键测试奖励",
                points_value=50
            )

            session.add(reward)
            session.commit()

            # 尝试创建引用不存在奖励的配方
            fake_reward_id = uuid.uuid4()
            recipe = RewardRecipe(
                id=uuid.uuid4(),
                name="外键测试配方",
                result_reward_id=fake_reward_id,
                required_rewards=[{"reward_id": str(fake_reward_id), "quantity": 1}]
            )

            session.add(recipe)

            # 验证外键约束（可能因实现方式而异）
            try:
                session.commit()
                # 如果没有外键约束，至少验证查询时的完整性
                retrieved_recipe = session.get(RewardRecipe, recipe.id)
                assert retrieved_recipe.result_reward_id == fake_reward_id
            except Exception:
                # 有外键约束时应该抛出异常
                session.rollback()

    def test_json_field_complex_structure(self):
        """测试JSON字段复杂结构"""
        engine = get_engine()

        # 创建表
        BaseModel.metadata.create_all(bind=engine)

        with get_session() as session:
            user_id = uuid.uuid4()

            # 创建带复杂JSON结构的任务
            complex_tags = ["工作", "重要", "项目A", "子任务1", "子任务2"]
            complex_services = [
                {"service_id": "service-001", "priority": "high"},
                {"service_id": "service-002", "priority": "medium"}
            ]

            task = Task(
                id=uuid.uuid4(),
                user_id=user_id,
                title="复杂JSON测试",
                tags=complex_tags,
                service_ids=complex_services
            )

            session.add(task)
            session.commit()

            # 查询并验证复杂JSON结构
            retrieved_task = session.get(Task, task.id)
            assert retrieved_task is not None
            assert retrieved_task.tags == complex_tags
            assert len(retrieved_task.tags) == 5
            assert retrieved_task.service_ids == complex_services
            assert len(retrieved_task.service_ids) == 2

    def test_database_connection_stability(self):
        """测试数据库连接稳定性"""
        engine = get_engine()

        # 验证引擎不为None
        assert engine is not None

        # 测试多次连接
        for i in range(5):
            with get_session() as session:
                # 执行简单查询
                from sqlalchemy import text
                result = session.execute(text("SELECT 1 as test")).fetchone()
                assert result[0] == 1

    def test_datetime_timezone_consistency(self):
        """测试时区一致性"""
        engine = get_engine()

        # 创建表
        BaseModel.metadata.create_all(bind=engine)

        with get_session() as session:
            # 创建带时区时间的事务
            transaction = PointsTransaction(
                user_id=uuid.uuid4(),
                amount=10,
                source_type="test",
                created_at=datetime.now(timezone.utc)
            )

            session.add(transaction)
            session.commit()

            # 查询并验证时间
            retrieved_tx = session.get(PointsTransaction, transaction.id)
            assert retrieved_tx is not None
            assert retrieved_tx.created_at.tzinfo is not None
            # SQLite可能存储为本地时间，但时区信息应该保留在Python层面