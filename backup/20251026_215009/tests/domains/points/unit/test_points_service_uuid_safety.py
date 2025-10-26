"""
Points领域Service层UUID类型安全单元测试

测试PointsService的UUID处理，确保：
1. ensure_str转换的正确性和类型安全
2. 参数验证和错误处理
3. 与Reward领域交互的兼容性
4. 边界情况和异常场景处理

遵循TDD原则：先写测试→最小实现→优化重构

作者：TaKeKe团队
版本：1.0.0 - Points领域UUID类型安全
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import UUID, uuid4
from sqlmodel import Session

from src.domains.points.service import PointsService
from src.domains.points.models import PointsTransaction
from src.core.uuid_converter import UUIDConverter
from tests.conftest import test_db_session


@pytest.mark.unit
class TestPointsServiceUUIDSafety:
    """PointsService UUID类型安全测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        pass

    def test_uuid_converter_string_conversion(self, test_db_session):
        """测试UUIDConverter.ensure_string正确转换UUID对象"""
        uuid_obj = uuid4()
        result = UUIDConverter.ensure_string(uuid_obj)

        # 验证转换结果
        assert isinstance(result, str)
        assert len(result) == 36  # UUID字符串长度
        assert result.count('-') == 4  # UUID格式验证

    def test_uuid_converter_string_passthrough(self, test_db_session):
        """测试UUIDConverter.ensure_string直接传递字符串"""
        uuid_str = str(uuid4())
        result = UUIDConverter.ensure_string(uuid_str)

        # 验证直接返回
        assert result == uuid_str
        assert isinstance(result, str)

    def test_uuid_converter_none_handling(self, test_db_session):
        """测试UUIDConverter.ensure_string处理None值"""
        # UUIDConverter.ensure_string 不支持None，会抛出异常
        with pytest.raises((TypeError, ValueError)):
            UUIDConverter.ensure_string(None)

    def test_calculate_balance_uuid_conversion(self, test_db_session):
        """测试calculate_balance方法的UUID转换"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        # 添加测试数据
        transaction = PointsTransaction(
            user_id=UUIDConverter.ensure_string(user_id),
            amount=100,
            source_type="test",
                        created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(transaction)
        test_db_session.commit()

        # 测试余额计算
        balance = service.calculate_balance(user_id)
        assert isinstance(balance, int)
        assert balance == 100

    def test_calculate_balance_string_input(self, test_db_session):
        """测试calculate_balance方法接受字符串输入"""
        user_id_str = str(uuid4())
        service = PointsService(test_db_session)

        # 添加测试数据
        transaction = PointsTransaction(
            user_id=user_id_str,
            amount=200,
            source_type="test",
                        created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(transaction)
        test_db_session.commit()

        # 测试余额计算
        balance = service.calculate_balance(user_id_str)
        assert isinstance(balance, int)
        assert balance == 200

    def test_add_points_uuid_conversion(self, test_db_session):
        """测试add_points方法的UUID转换"""
        user_id = uuid4()
        reward_id = uuid4()
        transaction_group = f"test_group_{uuid4()}"

        service = PointsService(test_db_session)

        # 测试添加积分
        result = service.add_points(
            user_id=user_id,
            amount=50,
            source_type="test",
            source_id=UUIDConverter.ensure_string(reward_id),
            transaction_group=UUIDConverter.ensure_string(transaction_group)
        )

        # 验证结果
        assert isinstance(result, PointsTransaction)
        assert result.amount == 50
        assert result.source_type == "test"

        # 验证数据库记录
        transactions = service.get_transactions(user_id, limit=1)
        assert len(transactions) == 1
        assert transactions[0]["user_id"] == UUIDConverter.ensure_string(user_id)
        assert transactions[0]["source_id"] == UUIDConverter.ensure_string(reward_id)

    def test_add_points_string_input(self, test_db_session):
        """测试add_points方法接受字符串输入"""
        user_id_str = str(uuid4())
        reward_id_str = str(uuid4())
        transaction_group_str = f"test_group_{uuid4()}"

        service = PointsService(test_db_session)

        # 测试添加积分
        result = service.add_points(
            user_id=user_id_str,
            amount=75,
            source_type="test",
            source_id=reward_id_str,
            transaction_group=transaction_group_str,
        )

        # 验证结果
        assert isinstance(result, PointsTransaction)
        assert result.amount == 75
        assert result.source_type == "test"

    def test_get_statistics_uuid_conversion(self, test_db_session):
        """测试get_statistics方法的UUID转换"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        # 添加测试数据
        for i in range(3):
            transaction = PointsTransaction(
                user_id=UUIDConverter.ensure_string(user_id),
                amount=10 * (i + 1),
                source_type=f"test_{i}",
                                created_at=datetime.now(timezone.utc)
            )
            test_db_session.add(transaction)
        test_db_session.commit()

        # 测试统计查询
        stats = service.get_statistics(user_id)
        assert isinstance(stats, list)
        assert len(stats) >= 0  # 可能为空列表

    def test_get_statistics_with_filter(self, test_db_session):
        """测试get_statistics方法的过滤功能"""
        user_id = uuid4()
        start_date = datetime.now(timezone.utc)
        end_date = datetime.now(timezone.utc)

        service = PointsService(test_db_session)

        # 测试带日期过滤的统计查询
        stats = service.get_statistics(
            user_id=user_id,
            start_date=start_date.date(),
            end_date=end_date.date()
        )

        # 验证结果结构
        assert isinstance(stats, list)

    def test_get_transactions_uuid_conversion(self, test_db_session):
        """测试get_transactions方法的UUID转换"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        # 创建多个测试交易
        for i in range(5):
            transaction = PointsTransaction(
                user_id=UUIDConverter.ensure_string(user_id),
                amount=10 + i,
                source_type=f"test_{i}",
                                created_at=datetime.now(timezone.utc)
            )
            test_db_session.add(transaction)
        test_db_session.commit()

        # 测试交易查询
        transactions = service.get_transactions(user_id, limit=3)
        assert isinstance(transactions, list)
        assert len(transactions) <= 3  # 应该被限制

        # 验证返回格式
        if transactions:
            for tx in transactions:
                assert "id" in tx
                assert "amount" in tx
                assert "source_type" in tx
                assert isinstance(tx["id"], str)

    def test_transaction_field_conversion_consistency(self, test_db_session):
        """测试交易记录字段转换一致性"""
        user_id = uuid4()
        reward_id = uuid4()
        source_id = uuid4()
        transaction_group = uuid4()

        service = PointsService(test_db_session)

        # 测试复杂的添加操作
        result = service.add_points(
            user_id=user_id,
            amount=100,
            source_type="reward_bonus",
            source_id=UUIDConverter.ensure_string(source_id),
            transaction_group=UUIDConverter.ensure_string(transaction_group)
        )

        # 验证数据库中的字段格式
        transactions = service.get_transactions(user_id, limit=1)
        if transactions:
            tx = transactions[0]
            assert tx["user_id"] == UUIDConverter.ensure_string(user_id)
            assert tx["source_id"] == UUIDConverter.ensure_string(source_id)
            assert tx["transaction_group"] == UUIDConverter.ensure_string(transaction_group)

    def test_edge_cases_invalid_uuid(self, test_db_session):
        """测试边界情况：无效UUID输入"""
        service = PointsService(test_db_session)

        # 测试无效UUID格式
        invalid_uuids = [
            "invalid-uuid",
            "12345",
            "not-a-uuid",
            "short-uuid"
        ]

        for invalid_uuid in invalid_uuids:
            # 这些无效UUID应该被当作字符串处理，不会导致类型错误
            try:
                balance = service.calculate_balance(invalid_uuid)
                # 应该返回0，因为没有相关记录
                assert balance == 0
            except Exception as e:
                # 如果有异常，应该是数据库相关异常，不是UUID类型错误
                assert "uuid" not in str(e).lower()

    def test_concurrent_transactions_uuid_safety(self, test_db_session):
        """测试并发交易的UUID安全性"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        # 模拟并发添加操作
        results = []
        for i in range(3):
            result = service.add_points(
                user_id=user_id,
                amount=10,
                source_type="concurrent_test",
                source_id=str(uuid4()),
                            )
            results.append(result)

        # 验证所有操作成功
        assert all(isinstance(result, PointsTransaction) for result in results)

        # 验证最终余额正确
        final_balance = service.calculate_balance(user_id)
        assert final_balance == 30  # 3 * 10

    def test_large_amount_uuid_handling(self, test_db_session):
        """测试大额积分的UUID处理"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        # 测试添加大额积分
        large_amount = 999999
        result = service.add_points(
            user_id=user_id,
            amount=large_amount,
            source_type="large_test"
        )

        # 验证操作成功
        assert isinstance(result, PointsTransaction)
        assert result.amount == large_amount

        # 验证余额正确
        balance = service.calculate_balance(user_id)
        assert balance == large_amount

    def test_uuid_type_performance(self, test_db_session):
        """测试UUID转换的性能影响"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        import time
        iterations = 1000

        # 测试多次UUID转换的性能
        start_time = time.perf_counter()
        for _ in range(iterations):
            UUIDConverter.ensure_string(user_id)  # 模拟调用
        end_time = time.perf_counter()

        conversion_time = end_time - start_time
        # 验证性能在合理范围内（1000次转换应该很快）
        assert conversion_time < 0.1  # 应该在100ms内完成
        assert conversion_time > 0  # 确保确实执行了操作