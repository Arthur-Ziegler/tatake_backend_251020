"""
Reward领域UUID重构测试

测试Reward领域UUID类型安全的重构，确保：
1. Service层正确处理UUID参数
2. Repository层统一使用UUIDConverter转换
3. 数据库存储格式一致
4. API返回值类型正确

遵循TDD原则：先写测试，再重构代码。

作者：TaKeKe团队
版本：1.0.0 - UUID类型安全重构
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlmodel import Session

from src.domains.reward.models import Reward, RewardTransaction, PointsTransaction
from src.domains.reward.service import RewardService
from src.domains.reward.repository import RewardRepository
from src.core.uuid_converter import UUIDConverter
from tests.conftest import test_db_session


@pytest.mark.unit
class TestRewardUUIDSafety:
    """Reward领域UUID类型安全测试"""

    def test_uuid_converter_to_string_safety(self, test_db_session):
        """测试UUIDConverter字符串转换安全性"""
        uuid_obj = uuid4()
        uuid_str = UUIDConverter.to_string(uuid_obj)

        # 验证转换结果
        assert isinstance(uuid_str, str)
        assert len(uuid_str) == 36
        assert UUIDConverter.is_valid_uuid_string(uuid_str)

        # 验证可逆性
        converted_back = UUIDConverter.to_uuid(uuid_str)
        assert converted_back == uuid_obj

    def test_uuid_converter_to_uuid_safety(self, test_db_session):
        """测试UUIDConverter对象转换安全性"""
        uuid_str = str(uuid4())
        uuid_obj = UUIDConverter.to_uuid(uuid_str)

        # 验证转换结果
        assert isinstance(uuid_obj, UUID)
        assert str(uuid_obj) == uuid_str

    def test_reward_service_accepts_uuid_objects(self, test_db_session):
        """测试RewardService正确接受UUID对象参数"""
        # 创建测试数据
        user_id = uuid4()
        reward = Reward(
            name="测试奖品",
            description="测试描述",
            points_value=100,
            cost_type="points",
            cost_value=100,
            category="测试"
        )
        test_db_session.add(reward)
        test_db_session.commit()

        # Mock PointsService
        class MockPointsService:
            def get_user_balance(self, user_id_str):
                return 1000  # 足够的积分

            def add_points(self, user_id_str, amount, source_type, transaction_group=None):
                return True

        points_service = MockPointsService()
        reward_service = RewardService(test_db_session, points_service)

        # 测试Service层方法正确处理UUID对象
        transactions = reward_service.get_reward_transactions(user_id)
        assert isinstance(transactions, list)

        # 验证没有抛出类型错误
        assert len(transactions) == 0  # 新用户应该没有记录

    def test_reward_repository_stores_strings_correctly(self, test_db_session):
        """测试RewardRepository正确存储字符串格式UUID"""
        user_id = uuid4()
        reward_id = uuid4()

        # 创建RewardTransaction记录
        transaction = RewardTransaction(
            user_id=UUIDConverter.to_string(user_id),  # 使用UUIDConverter转换
            reward_id=UUIDConverter.to_string(reward_id),
            source_type="lottery",
            quantity=1,
            transaction_group="test_group"
        )

        test_db_session.add(transaction)
        test_db_session.commit()
        test_db_session.refresh(transaction)

        # 验证数据库中存储的是字符串
        assert isinstance(transaction.user_id, str)
        assert isinstance(transaction.reward_id, str)
        assert len(transaction.user_id) == 36
        assert len(transaction.reward_id) == 36

    def test_reward_repository_query_with_uuid_conversion(self, test_db_session):
        """测试RewardRepository使用UUID转换进行查询"""
        user_id = uuid4()
        repository = RewardRepository(test_db_session)

        # 创建测试数据
        transaction = RewardTransaction(
            user_id=UUIDConverter.to_string(user_id),
            reward_id=str(uuid4()),
            source_type="lottery",
            quantity=1
        )
        test_db_session.add(transaction)
        test_db_session.commit()

        # 使用UUID对象查询
        transactions = repository.get_user_rewards(user_id)
        assert len(transactions) == 1
        assert transactions[0].user_id == UUIDConverter.to_string(user_id)

    def test_no_uuid_object_storage_in_database(self, test_db_session):
        """确保没有UUID对象直接存储到数据库"""
        user_id = uuid4()

        # 这个测试验证bug修复：确保所有UUID都被转换为字符串存储
        with pytest.raises(Exception) as exc_info:
            # 尝试直接存储UUID对象（应该失败）
            invalid_transaction = RewardTransaction(
                user_id=user_id,  # 直接使用UUID对象，不转换
                reward_id=str(uuid4()),
                source_type="lottery",
                quantity=1
            )
            test_db_session.add(invalid_transaction)
            test_db_session.commit()

        # 验证确实抛出了类型错误
        # 注意：这取决于具体的数据库配置和SQLModel行为

    def test_api_compatibility_uuid_response_format(self, test_db_session):
        """测试API响应格式的UUID兼容性"""
        user_id = uuid4()
        repository = RewardRepository(test_db_session)

        # 创建测试数据
        transaction = RewardTransaction(
            user_id=UUIDConverter.to_string(user_id),
            reward_id=str(uuid4()),
            source_type="lottery",
            quantity=1,
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(transaction)
        test_db_session.commit()

        # 测试Repository方法返回格式
        user_materials = repository.get_user_materials(UUIDConverter.to_string(user_id))
        assert isinstance(user_materials, list)

        if len(user_materials) > 0:
            material = user_materials[0]
            assert "reward_id" in material
            assert isinstance(material["reward_id"], str)
            assert len(material["reward_id"]) == 36

    def test_cross_domain_uuid_consistency(self, test_db_session):
        """测试跨领域UUID处理的一致性"""
        user_id = uuid4()

        # 模拟跨领域调用场景
        class MockTop3Service:
            def __init__(self, reward_service):
                self.reward_service = reward_service

            def participate_with_reward(self, user_uuid, task_ids):
                # 跨领域调用应该传递UUID对象
                result = self.reward_service.top3_lottery(user_uuid, task_ids)
                return result

        # Mock PointsService
        class MockPointsService:
            def get_user_balance(self, user_id_str):
                return 100

            def consume_points(self, user_id_str, amount, source_type):
                return True

        points_service = MockPointsService()
        reward_service = RewardService(test_db_session, points_service)
        top3_service = MockTop3Service(reward_service)

        # 测试跨领域调用
        task_ids = [str(uuid4()), str(uuid4())]
        result = top3_service.participate_with_reward(user_id, task_ids)

        # 验证结果
        assert "success" in result
        assert isinstance(result["success"], bool)


@pytest.mark.integration
class TestRewardUUIDIntegration:
    """Reward领域UUID集成测试"""

    def test_end_to_end_uuid_flow(self, test_db_session):
        """测试端到端UUID流转：API → Service → Repository → Database"""
        user_id = uuid4()

        # 创建奖品
        reward = Reward(
            name="集成测试奖品",
            description="端到端测试",
            points_value=50,
            cost_type="points",
            cost_value=50,
            category="集成测试"
        )
        test_db_session.add(reward)
        test_db_session.commit()

        # Mock完整的积分系统
        class MockPointsService:
            def get_user_balance(self, user_id_str):
                return 100

            def consume_points(self, user_id_str, amount, source_type):
                # 模拟积分扣减
                points_transaction = PointsTransaction(
                    user_id=user_id_str,
                    amount=-amount,
                    source_type=source_type,
                    description="奖品兑换"
                )
                test_db_session.add(points_transaction)
                test_db_session.commit()
                return True

        points_service = MockPointsService()
        reward_service = RewardService(test_db_session, points_service)

        # 执行完整的兑换流程
        result = reward_service.redeem_reward(user_id, str(reward.id))

        # 验证结果
        assert result["success"] is True

        # 验证数据库记录
        transactions = reward_service.get_reward_transactions(user_id)
        assert len(transactions) >= 1

        # 验证UUID存储格式一致
        for transaction in transactions:
            assert isinstance(transaction.user_id, str)
            assert isinstance(transaction.reward_id, str)
            assert len(transaction.user_id) == 36

    def test_uuid_transaction_group_consistency(self, test_db_session):
        """测试事务组中UUID的一致性"""
        user_id = uuid4()
        transaction_group = f"test_group_{uuid4()}"

        # 创建多个相关事务
        transaction1 = RewardTransaction(
            user_id=UUIDConverter.to_string(user_id),
            reward_id=str(uuid4()),
            source_type="lottery",
            quantity=1,
            transaction_group=transaction_group
        )

        transaction2 = RewardTransaction(
            user_id=UUIDConverter.to_string(user_id),
            reward_id=str(uuid4()),
            source_type="lottery",
            quantity=1,
            transaction_group=transaction_group
        )

        test_db_session.add_all([transaction1, transaction2])
        test_db_session.commit()

        # 验证事务组一致性
        repository = RewardRepository(test_db_session)
        user_transactions = repository.get_user_rewards(user_id)

        group_transactions = [
            t for t in user_transactions
            if t.transaction_group == transaction_group
        ]

        assert len(group_transactions) == 2
        for transaction in group_transactions:
            assert transaction.user_id == UUIDConverter.to_string(user_id)
            assert transaction.transaction_group == transaction_group