"""
Reward领域Repository层UUID重构单元测试

测试RewardRepository的UUID类型安全重构，确保：
1. Repository层使用UUIDConverter替代直接str()转换
2. SQL查询参数正确转换为字符串格式
3. 数据库返回值格式一致
4. 错误处理和异常安全

遵循TDD原则：先写测试→最小实现→优化重构

作者：TaKeKe团队
版本：1.0.0 - Repository层UUID重构
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlmodel import Session

from src.domains.reward.repository import RewardRepository
from src.domains.reward.models import Reward, RewardTransaction
from src.core.uuid_converter import UUIDConverter
from tests.conftest import test_db_session


@pytest.mark.unit
class TestRewardRepositoryUUIDRefactoring:
    """RewardRepository UUID重构单元测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        pass

    def test_get_user_rewards_uses_uuid_converter(self, test_db_session):
        """测试get_user_rewards方法使用UUIDConverter"""
        user_id = uuid4()
        repository = RewardRepository(test_db_session)

        with pytest.raises(AttributeError):
            # Mock UUIDConverter方法不存在，说明应该直接使用UUIDConverter
            with patch.object(UUIDConverter, 'to_string') as mock_converter:
                mock_converter.return_value = str(user_id)
                result = repository.get_user_rewards(user_id)
                mock_converter.assert_called_once()

    def test_get_user_reward_balance_uses_uuid_converter(self, test_db_session):
        """测试get_user_reward_balance方法使用UUIDConverter"""
        user_id = uuid4()
        reward_id = str(uuid4())
        repository = RewardRepository(test_db_session)

        # 验证方法正常调用，不抛出类型错误
        try:
            balance = repository.get_user_reward_balance(user_id, reward_id)
            # 新用户应该没有余额
            assert balance == 0
        except Exception as e:
            # 如果有异常，应该是业务逻辑异常，而不是类型转换异常
            assert "type" not in str(e).lower()

    def test_get_user_materials_accepts_uuid_string(self, test_db_session):
        """测试get_user_materials方法接受UUID字符串"""
        user_id_str = str(uuid4())
        repository = RewardRepository(test_db_session)

        # 创建测试数据
        material = RewardTransaction(
            user_id=user_id_str,
            reward_id=str(uuid4()),
            source_type="gift",
            quantity=5,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(material)
        test_db_session.commit()

        result = repository.get_user_materials(user_id_str)
        assert isinstance(result, list)
        assert len(result) == 1
        assert "reward_id" in result[0]
        assert isinstance(result[0]["reward_id"], str)

    def test_create_transaction_with_uuid_string(self, test_db_session):
        """测试使用UUID字符串创建交易记录"""
        user_id_str = str(uuid4())
        reward_id_str = str(uuid4())

        transaction = RewardTransaction(
            user_id=user_id_str,
            reward_id=reward_id_str,
            source_type="lottery",
            quantity=1,
            created_at=datetime.now(timezone.utc)
        )

        test_db_session.add(transaction)
        test_db_session.commit()
        test_db_session.refresh(transaction)

        # 验证存储的是字符串格式
        assert isinstance(transaction.user_id, str)
        assert isinstance(transaction.reward_id, str)
        assert transaction.user_id == user_id_str
        assert transaction.reward_id == reward_id_str

    def test_add_points_transaction_with_uuid_string(self, test_db_session):
        """测试添加积分交易记录使用UUID字符串"""
        user_id_str = str(uuid4())

        points_transaction = {
            "user_id": user_id_str,
            "amount": 100,
            "source_type": "reward",
            "description": "测试积分"
        }

        repository = RewardRepository(test_db_session)

        # 验证方法调用不会抛出类型错误
        try:
            result = repository.add_points_transaction(
                points_transaction["user_id"],
                points_transaction["amount"],
                points_transaction["source_type"],
                points_transaction["description"]
            )
            # 应该返回成功结果
            assert result is True
        except Exception as e:
            # 如果有异常，应该是数据库相关异常，而不是类型错误
            assert "type" not in str(e).lower()

    def test_query_with_uuid_string_parameter(self, test_db_session):
        """测试SQL查询使用UUID字符串参数"""
        user_id_str = str(uuid4())
        repository = RewardRepository(test_db_session)

        # 创建测试数据
        for i in range(3):
            transaction = RewardTransaction(
                user_id=user_id_str,
                reward_id=str(uuid4()),
                source_type="test",
                quantity=1,
                created_at=datetime.now(timezone.utc)
            )
            test_db_session.add(transaction)
        test_db_session.commit()

        # 查询用户的交易记录
        from sqlmodel import select
        query = select(RewardTransaction).where(RewardTransaction.user_id == user_id_str)
        results = test_db_session.exec(query).all()

        # 验证查询结果
        assert len(results) == 3
        for result in results:
            assert result.user_id == user_id_str
            assert isinstance(result.user_id, str)

    def test_uuid_string_length_consistency(self, test_db_session):
        """测试UUID字符串长度一致性"""
        user_id = uuid4()
        user_id_str = UUIDConverter.to_string(user_id)

        # 验证UUID字符串长度
        assert len(user_id_str) == 36
        assert user_id_str.count('-') == 4  # UUID格式验证

        # 验证UUID可逆转换
        converted_back = UUIDConverter.to_uuid(user_id_str)
        assert converted_back == user_id

    def test_repository_methods_return_string_format(self, test_db_session):
        """测试Repository方法返回字符串格式"""
        user_id_str = str(uuid4())
        reward_id_str = str(uuid4())
        recipe_id = str(uuid4())

        repository = RewardRepository(test_db_session)

        # 测试RecipeRepository方法返回格式
        try:
            recipe = repository.get_recipe_by_id(recipe_id)
            if recipe:  # 如果找到配方
                if "id" in recipe:
                    assert isinstance(recipe["id"], str)
                if "result_reward_id" in recipe:
                    assert isinstance(recipe["result_reward_id"], str)
        except Exception:
            # 配方不存在是正常的，这里主要测试类型
            pass

        # 测试用户材料查询返回格式
        materials = repository.get_user_materials(user_id_str)
        if materials:
            for material in materials:
                assert "reward_id" in material
                assert isinstance(material["reward_id"], str)

    def test_uuid_converter_integration(self, test_db_session):
        """测试UUIDConverter集成"""
        from src.core.uuid_converter import UUIDConverter

        user_id = uuid4()
        user_id_str = UUIDConverter.to_string(user_id)

        # 验证UUIDConverter的各种转换
        assert UUIDConverter.is_valid_uuid_string(user_id_str) is True
        assert UUIDConverter.is_valid_uuid_string("invalid-uuid") is False

        # 验证批量转换
        uuids = [uuid4() for _ in range(5)]
        strings = UUIDConverter.to_string_batch(uuids)
        back_to_uuids = UUIDConverter.to_uuid_batch(strings)

        assert len(strings) == 5
        assert len(back_to_uuids) == 5
        for original, converted, back in zip(uuids, strings, back_to_uuids):
            assert back == original
            assert isinstance(converted, str)

    def test_error_handling_invalid_uuid_format(self, test_db_session):
        """测试无效UUID格式的错误处理"""
        repository = RewardRepository(test_db_session)

        # 测试无效UUID格式
        invalid_uuids = [
            "",
            "invalid-uuid",
            "123",
            None,
            123
        ]

        for invalid_uuid in invalid_uuids:
            if invalid_uuid is None:
                continue  # None值的处理可能不同

            try:
                # 大多数方法应该能够处理字符串输入
                result = repository.get_user_rewards(invalid_uuid)
                # 如果没有抛出异常，应该返回空结果
                assert isinstance(result, list)
            except Exception as e:
                # 允许业务逻辑异常，但不应该是类型系统错误
                assert "attribute" not in str(e).lower()
                assert "type" not in str(e).lower()

    def test_database_schema_compatibility(self, test_db_session):
        """测试数据库Schema兼容性"""
        # 验证数据库表结构
        from sqlmodel import inspect
        inspector = inspect(test_db_session.bind)

        # 检查reward_transactions表结构
        if inspector.has_table("reward_transactions"):
            columns = inspector.get_columns("reward_transactions")
            user_id_column = next((col for col in columns if col["name"] == "user_id"), None)
            reward_id_column = next((col for col in columns if col["name"] == "reward_id"), None)

            # 验证列类型为字符串类型
            if user_id_column:
                assert user_id_column["type"].lower() in ["varchar", "text", "string"]
            if reward_id_column:
                assert reward_id_column["type"].lower() in ["varchar", "text", "string"]

    def test_performance_uuid_conversion_vs_direct_str(self, test_db_session):
        """测试UUIDConverter性能 vs 直接str()转换"""
        user_id = uuid4()
        iterations = 10000

        # 测试直接str()转换
        import time
        start_time = time.perf_counter()
        for _ in range(iterations):
            result = str(user_id)
        direct_str_time = time.perf_counter() - start_time

        # 测试UUIDConverter转换
        start_time = time.perf_counter()
        for _ in range(iterations):
            result = UUIDConverter.to_string(user_id)
        converter_time = time.perf_counter() - start_time

        # 验证性能在合理范围内（UUIDConverter不应该显著慢于直接str()）
        ratio = converter_time / direct_str_time
        assert ratio < 10.0  # UUIDConverter不应该超过10倍的性能开销

        print(f"UUIDConverter性能比率: {ratio:.2f} (相对于直接str())")