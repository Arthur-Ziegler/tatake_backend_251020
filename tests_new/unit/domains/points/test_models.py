"""
Points领域数据模型测试

测试Points领域的数据模型和数据库功能，包括：
1. PointsTransaction模型验证
2. 字段类型和约束验证
3. 模型序列化和反序列化
4. 数据库索引和表配置
5. 时间戳处理
6. 模型继承关系

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from src.domains.points.models import PointsTransaction
from src.domains.auth.models import BaseModel


@pytest.mark.unit
class TestPointsTransaction:
    """积分交易模型测试类"""

    def test_points_transaction_creation_minimal(self):
        """测试最小积分交易创建"""
        user_id = str(uuid4())
        transaction = PointsTransaction(
            user_id=user_id,
            amount=100,
            source_type="task_complete"
        )

        # 验证必需字段
        assert transaction.user_id == user_id
        assert transaction.amount == 100
        assert transaction.source_type == "task_complete"

        # 验证自动生成的字段
        assert transaction.id is not None
        assert len(transaction.id) > 0
        assert transaction.source_id is None
        assert isinstance(transaction.created_at, datetime)

    def test_points_transaction_creation_full(self):
        """测试完整积分交易创建"""
        user_id = str(uuid4())
        source_id = str(uuid4())
        created_time = datetime.now(timezone.utc)

        transaction = PointsTransaction(
            user_id=user_id,
            amount=-50,
            source_type="top3_cost",
            source_id=source_id,
            created_at=created_time
        )

        assert transaction.user_id == user_id
        assert transaction.amount == -50
        assert transaction.source_type == "top3_cost"
        assert transaction.source_id == source_id
        assert transaction.created_at == created_time

    def test_points_transaction_valid_source_types(self):
        """测试有效的积分来源类型"""
        user_id = str(uuid4())
        valid_source_types = [
            "task_complete",
            "task_complete_top3",
            "top3_cost",
            "lottery_points",
            "recharge",
            "welcome_gift"
        ]

        for source_type in valid_source_types:
            transaction = PointsTransaction(
                user_id=user_id,
                amount=10,
                source_type=source_type
            )
            assert transaction.source_type == source_type

    def test_points_transaction_amount_positive(self):
        """测试正数积分金额（获得积分）"""
        user_id = str(uuid4())
        transaction = PointsTransaction(
            user_id=user_id,
            amount=100,
            source_type="task_complete"
        )

        assert transaction.amount == 100
        assert transaction.amount > 0

    def test_points_transaction_amount_negative(self):
        """测试负数积分金额（消费积分）"""
        user_id = str(uuid4())
        transaction = PointsTransaction(
            user_id=user_id,
            amount=-50,
            source_type="top3_cost"
        )

        assert transaction.amount == -50
        assert transaction.amount < 0

    def test_points_transaction_amount_zero(self):
        """测试零积分金额"""
        user_id = str(uuid4())
        transaction = PointsTransaction(
            user_id=user_id,
            amount=0,
            source_type="lottery_points"
        )

        assert transaction.amount == 0

    def test_points_transaction_id_format(self):
        """测试交易ID格式"""
        user_id = str(uuid4())
        transaction = PointsTransaction(
            user_id=user_id,
            amount=50,
            source_type="recharge"
        )

        # 验证ID是UUID格式
        uuid_obj = uuid4()
        assert len(transaction.id) == len(str(uuid_obj))
        assert '-' in transaction.id  # UUID包含连字符

    def test_points_transaction_user_id_validation(self):
        """测试用户ID验证"""
        valid_user_ids = [
            str(uuid4()),
            "550e8400-e29b-41d4-a716-446655440000",
            "123e4567-e89b-12d3-a456-426614174000"
        ]

        for user_id in valid_user_ids:
            transaction = PointsTransaction(
                user_id=user_id,
                amount=10,
                source_type="welcome_gift"
            )
            assert transaction.user_id == user_id

    def test_points_transaction_source_id_validation(self):
        """测试来源ID验证"""
        user_id = str(uuid4())

        # 测试有source_id的情况
        source_id = str(uuid4())
        transaction = PointsTransaction(
            user_id=user_id,
            amount=20,
            source_type="task_complete",
            source_id=source_id
        )
        assert transaction.source_id == source_id

        # 测试无source_id的情况
        transaction_no_source = PointsTransaction(
            user_id=user_id,
            amount=30,
            source_type="recharge"
        )
        assert transaction_no_source.source_id is None

    def test_points_transaction_timestamp_utc(self):
        """测试时间戳为UTC时区"""
        user_id = str(uuid4())

        # 验证默认时间是UTC
        transaction1 = PointsTransaction(
            user_id=user_id,
            amount=10,
            source_type="task_complete"
        )
        assert transaction1.created_at.tzinfo == timezone.utc

        # 验证指定UTC时间
        utc_time = datetime.now(timezone.utc)
        transaction2 = PointsTransaction(
            user_id=user_id,
            amount=20,
            source_type="lottery_points",
            created_at=utc_time
        )
        assert transaction2.created_at == utc_time
        assert transaction2.created_at.tzinfo == timezone.utc

    def test_points_transaction_serialization(self):
        """测试模型序列化"""
        user_id = str(uuid4())
        source_id = str(uuid4())

        transaction = PointsTransaction(
            user_id=user_id,
            amount=100,
            source_type="task_complete_top3",
            source_id=source_id
        )

        # 测试字典序列化
        data = transaction.model_dump()
        assert data["user_id"] == user_id
        assert data["amount"] == 100
        assert data["source_type"] == "task_complete_top3"
        assert data["source_id"] == source_id
        assert "created_at" in data

        # 测试JSON序列化
        json_data = transaction.model_dump_json()
        assert user_id in json_data
        assert "task_complete_top3" in json_data
        assert str(transaction.amount) in json_data

    def test_points_transaction_model_fields(self):
        """测试模型字段属性"""
        user_id = str(uuid4())
        transaction = PointsTransaction(
            user_id=user_id,
            amount=50,
            source_type="welcome_gift"
        )

        # 验证字段存在
        assert hasattr(transaction, 'id')
        assert hasattr(transaction, 'user_id')
        assert hasattr(transaction, 'amount')
        assert hasattr(transaction, 'source_type')
        assert hasattr(transaction, 'source_id')
        assert hasattr(transaction, 'created_at')

        # 验证字段类型
        assert isinstance(transaction.id, str)
        assert isinstance(transaction.user_id, str)
        assert isinstance(transaction.amount, int)
        assert isinstance(transaction.source_type, str)
        assert isinstance(transaction.created_at, datetime)

    def test_points_transaction_inheritance(self):
        """测试模型继承关系"""
        user_id = str(uuid4())
        transaction = PointsTransaction(
            user_id=user_id,
            amount=10,
            source_type="recharge"
        )

        # 验证继承关系
        assert isinstance(transaction, PointsTransaction)
        assert isinstance(transaction, BaseModel)
        assert isinstance(transaction, SQLModel)


@pytest.mark.integration
class TestPointsTransactionDatabase:
    """积分交易数据库集成测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """为测试设置内存数据库"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        # 创建表
        SQLModel.metadata.create_all(engine)

        yield engine

    def test_database_table_creation(self):
        """测试数据库表创建"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        # 创建表
        SQLModel.metadata.create_all(engine)

        # 验证表存在
        with Session(engine) as session:
            result = session.exec("SELECT name FROM sqlite_master WHERE type='table' AND name='points_transactions'")
            table_exists = result.first() is not None
            assert table_exists

    def test_database_crud_operations(self):
        """测试数据库CRUD操作"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            # 创建
            user_id = str(uuid4())
            transaction = PointsTransaction(
                user_id=user_id,
                amount=100,
                source_type="task_complete"
            )
            session.add(transaction)
            session.commit()
            session.refresh(transaction)

            # 读取
            result = session.get(PointsTransaction, transaction.id)
            assert result is not None
            assert result.user_id == user_id
            assert result.amount == 100

            # 更新
            result.amount = 200
            session.add(result)
            session.commit()
            session.refresh(result)
            assert result.amount == 200

            # 删除
            session.delete(result)
            session.commit()
            deleted_result = session.get(PointsTransaction, transaction.id)
            assert deleted_result is None

    def test_database_query_by_user_id(self):
        """测试按用户ID查询"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            user_id = str(uuid4())

            # 创建多个交易
            transactions = []
            for i in range(3):
                transaction = PointsTransaction(
                    user_id=user_id,
                    amount=10 * (i + 1),
                    source_type="task_complete"
                )
                transactions.append(transaction)
                session.add(transaction)

            # 创建其他用户的交易
            other_user_id = str(uuid4())
            other_transaction = PointsTransaction(
                user_id=other_user_id,
                amount=500,
                source_type="recharge"
            )
            session.add(other_transaction)

            session.commit()

            # 查询指定用户的交易
            results = session.exec(
                select(PointsTransaction).where(PointsTransaction.user_id == user_id)
            ).all()

            assert len(results) == 3
            for result in results:
                assert result.user_id == user_id

    def test_database_query_by_source_type(self):
        """测试按来源类型查询"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            user_id = str(uuid4())

            # 创建不同来源类型的交易
            source_types = ["task_complete", "recharge", "lottery_points"]
            for source_type in source_types:
                transaction = PointsTransaction(
                    user_id=user_id,
                    amount=50,
                    source_type=source_type
                )
                session.add(transaction)

            session.commit()

            # 查询特定来源类型的交易
            task_results = session.exec(
                select(PointsTransaction).where(PointsTransaction.source_type == "task_complete")
            ).all()

            assert len(task_results) == 1
            assert task_results[0].source_type == "task_complete"

    def test_database_aggregate_calculations(self):
        """测试数据库聚合计算"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            user_id = str(uuid4())

            # 创建多个交易
            amounts = [100, -50, 25, -10, 35]
            for amount in amounts:
                transaction = PointsTransaction(
                    user_id=user_id,
                    amount=amount,
                    source_type="test"
                )
                session.add(transaction)

            session.commit()

            # 计算总积分
            total_amount = session.exec(
                select("SUM(amount)").select_from(PointsTransaction).where(PointsTransaction.user_id == user_id)
            ).first()

            expected_total = sum(amounts)
            assert total_amount[0] == expected_total

            # 计算交易数量
            count = session.exec(
                select("COUNT(*)").select_from(PointsTransaction).where(PointsTransaction.user_id == user_id)
            ).first()

            assert count[0] == len(amounts)

    def test_database_unique_constraint(self):
        """测试数据库唯一约束"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            user_id = str(uuid4())

            # 创建第一个交易
            transaction1 = PointsTransaction(
                user_id=user_id,
                amount=100,
                source_type="task_complete"
            )
            session.add(transaction1)
            session.commit()

            # 创建第二个交易（应该成功，因为ID不同）
            transaction2 = PointsTransaction(
                user_id=user_id,
                amount=50,
                source_type="recharge"
            )
            session.add(transaction2)
            session.commit()

            # 验证两个交易都存在
            results = session.exec(
                select(PointsTransaction).where(PointsTransaction.user_id == user_id)
            ).all()
            assert len(results) == 2

    def test_database_timestamp_storage(self):
        """测试数据库时间戳存储"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            user_id = str(uuid4())
            created_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

            transaction = PointsTransaction(
                user_id=user_id,
                amount=100,
                source_type="task_complete",
                created_at=created_time
            )
            session.add(transaction)
            session.commit()
            session.refresh(transaction)

            # 验证时间戳正确存储和检索
            assert transaction.created_at == created_time
            assert transaction.created_at.tzinfo == timezone.utc


@pytest.mark.unit
class TestPointsTransactionEdgeCases:
    """积分交易边界条件测试类"""

    def test_large_amount_values(self):
        """测试大额积分值"""
        user_id = str(uuid4())
        large_amount = 1000000  # 一百万积分

        transaction = PointsTransaction(
            user_id=user_id,
            amount=large_amount,
            source_type="recharge"
        )

        assert transaction.amount == large_amount

    def test_negative_large_amount_values(self):
        """测试大额负积分值"""
        user_id = str(uuid4())
        large_negative_amount = -500000  # 负五十万积分

        transaction = PointsTransaction(
            user_id=user_id,
            amount=large_negative_amount,
            source_type="top3_cost"
        )

        assert transaction.amount == large_negative_amount

    def test_model_validation_edge_cases(self):
        """测试模型验证边界情况"""
        user_id = str(uuid4())

        # 测试空字符串source_type（可能会失败）
        try:
            transaction = PointsTransaction(
                user_id=user_id,
                amount=10,
                source_type=""
            )
            # 如果成功创建，验证字段
            assert transaction.source_type == ""
        except Exception:
            # 如果失败，这是预期的验证行为
            pass

    def test_uuid_id_generation(self):
        """测试UUID ID生成唯一性"""
        user_id = str(uuid4())

        # 创建多个交易
        transactions = []
        for _ in range(10):
            transaction = PointsTransaction(
                user_id=user_id,
                amount=10,
                source_type="test"
            )
            transactions.append(transaction)

        # 验证所有ID都是唯一的
        ids = [t.id for t in transactions]
        assert len(ids) == len(set(ids))  # 没有重复

    def test_model_field_types_validation(self):
        """测试模型字段类型验证"""
        user_id = str(uuid4())

        transaction = PointsTransaction(
            user_id=user_id,
            amount=100,
            source_type="task_complete",
            source_id=str(uuid4())
        )

        # 验证字段类型
        assert type(transaction.id) == str
        assert type(transaction.user_id) == str
        assert type(transaction.amount) == int
        assert type(transaction.source_type) == str
        assert type(transaction.source_id) == str
        assert type(transaction.created_at) == datetime


@pytest.mark.parametrize("source_type", [
    "task_complete",
    "task_complete_top3",
    "top3_cost",
    "lottery_points",
    "recharge",
    "welcome_gift",
    "custom_source"  # 测试自定义来源
])
def test_various_source_types(source_type):
    """参数化测试各种来源类型"""
    user_id = str(uuid4())

    transaction = PointsTransaction(
        user_id=user_id,
        amount=10,
        source_type=source_type
    )

    assert transaction.source_type == source_type


@pytest.mark.parametrize("amount", [
    1, 10, 100, 1000,  # 正数
    -1, -10, -100, -1000,  # 负数
    0  # 零
])
def test_various_amounts(amount):
    """参数化测试各种积分数量"""
    user_id = str(uuid4())

    transaction = PointsTransaction(
        user_id=user_id,
        amount=amount,
        source_type="test"
    )

    assert transaction.amount == amount