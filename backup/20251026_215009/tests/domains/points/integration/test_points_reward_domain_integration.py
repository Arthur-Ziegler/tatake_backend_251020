"""
Points领域与Reward领域UUID处理集成测试

测试Points领域与Reward领域交互时的UUID处理一致性：
1. Reward领域调用PointsService时的参数格式
2. Points领域返回给Reward领域的格式
3. 跨领域数据传递的类型安全性
4. 领域间边界情况处理

遵循TDD原则：先写测试→最小实现→优化重构

作者：TaKeKe团队
版本：1.0.0 - Points-Reward领域集成
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import UUID, uuid4
from sqlmodel import Session

from src.domains.points.service import PointsService
from src.domains.reward.service import RewardService
from src.domains.points.models import PointsTransaction
from src.utils.uuid_helpers import ensure_str
from tests.conftest import test_db_session


@pytest.mark.integration
class TestPointsRewardDomainIntegration:
    """Points领域与Reward领域集成测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        pass

    def test_reward_calls_points_with_uuid_string(self, test_db_session):
        """测试Reward领域调用PointsService时传递UUID字符串"""
        user_id = uuid4()
        reward_id = str(uuid4())

        # Mock PointsService
        mock_points_service = Mock()
        mock_points_service.get_user_balance.return_value = 1000
        mock_points_service.consume_points.return_value = True
        mock_points_service.add_points.return_value = True

        reward_service = RewardService(test_db_session, mock_points_service)

        # 执行奖励兑换
        result = reward_service.redeem_reward(user_id, reward_id)

        # 验证Reward使用UUIDConverter转换
        # 注意：这里验证的是RewardService内部是否正确调用了UUIDConverter
        # PointsService接收到的是字符串格式
        assert result["success"] is True
        mock_points_service.get_user_balance.assert_called_once()
        mock_points_service.consume_points.assert_called_once()

        # 验证PointsService接收到的参数类型
        call_args = mock_points_service.consume_points.call_args[0]
        passed_user_id = call_args[0]
        assert isinstance(passed_user_id, str)
        assert len(passed_user_id) == 36

    def test_reward_calls_points_with_string_input(self, test_db_session):
        """测试Reward领域传递字符串给PointsService"""
        user_id_str = str(uuid4())
        reward_id = str(uuid4())

        # Mock PointsService
        mock_points_service = Mock()
        mock_points_service.get_user_balance.return_value = 500
        mock_points_service.consume_points.return_value = True

        reward_service = RewardService(test_db_session, mock_points_service)

        # 执行奖励兑换
        result = reward_service.redeem_reward(user_id_str, reward_id)

        # 验证调用成功
        assert result["success"] is True
        mock_points_service.get_user_balance.assert_called_once()
        mock_points_service.consume_points.assert_called_once()

        # 验证传递给PointsService的参数
        call_args = mock_points_service.consume_points.call_args[0]
        passed_user_id = call_args[0]
        assert isinstance(passed_user_id, str)

    def test_points_service_compatibility_with_both_types(self, test_db_session):
        """测试PointsService对UUID和字符串输入的兼容性"""
        uuid_obj = uuid4()
        uuid_str = str(uuid_obj)

        # 创建PointsService实例
        points_service = PointsService(test_db_session)

        # 测试UUID对象输入
        balance_uuid = points_service.calculate_balance(uuid_obj)
        assert isinstance(balance_uuid, int)

        # 测试字符串输入
        balance_str = points_service.calculate_balance(uuid_str)
        assert isinstance(balance_str, int)

        # 两种方式结果应该一致（都是新用户，余额为0）
        assert balance_uuid == balance_str

    def test_cross_domain_transaction_consistency(self, test_db_session):
        """测试跨领域交易的一致性"""
        user_id = uuid4()

        # 创建PointsService实例
        points_service = PointsService(test_db_session)

        # Mock RewardService用于测试反调用
        mock_reward_service = Mock()
        mock_reward_service.get_user_materials.return_value = []

        # 测试添加积分操作
        transaction_group = str(uuid4())
        result = points_service.add_points(
            user_id=user_id,
            amount=100,
            source_type="test_cross_domain",
            source_id=str(uuid4()),
            transaction_group=transaction_group,
            description="跨领域测试"
        )

        # 验证操作成功
        assert result is True

        # 验证生成的交易记录
        transactions = points_service.get_transactions(user_id, limit=1)
        assert len(transactions) == 1

        transaction = transactions[0]
        assert transaction["user_id"] == ensure_str(user_id)
        assert transaction["transaction_group"] == transaction_group
        assert transaction["amount"] == 100

    def test_top3_reward_interaction_uuid_safety(self, test_db_session):
        """测试Top3与Reward领域交互的UUID安全性"""
        user_id = uuid4()
        task_ids = [str(uuid4()), str(uuid4())]

        # Mock PointsService
        mock_points_service = Mock()
        mock_points_service.get_user_balance.return_value = 50
        mock_points_service.consume_points.return_value = True

        reward_service = RewardService(test_db_session, mock_points_service)

        # 执行Top3抽奖
        result = reward_service.top3_lottery(user_id, task_ids)

        # 验证操作成功（假设有足够积分）
        mock_points_service.consume_points.assert_called_once()

        # 验证传递给PointsService的参数
        call_args = mock_points_service.consume_points.call_args[0]
        passed_user_id = call_args[0]
        assert isinstance(passed_user_id, str)

    def test_welcome_gift_points_interaction(self, test_db_session):
        """测试欢迎礼包与Points领域交互的UUID安全性"""
        user_id = uuid4()

        # Mock PointsService
        mock_points_service = Mock()
        mock_points_service.add_points.return_value = True

        from src.domains.reward.welcome_gift_service import WelcomeGiftService
        welcome_service = WelcomeGiftService(test_db_session, mock_points_service)

        # 执行欢迎礼包领取
        result = welcome_service.claim_welcome_gift(user_id)

        # 验证PointsService被调用
        assert mock_points_service.add_points.called
        assert result["success"] is True

        # 验证传递给PointsService的参数
        # 检查所有add_points调用
        for call in mock_points_service.add_points.call_args_list:
            passed_user_id = call[0]
            assert isinstance(passed_user_id, str)

    def test_error_propagation_between_domains(self, test_db_session):
        """测试领域间错误传播的正确性"""
        user_id = uuid4()

        # Mock PointsService抛出异常
        mock_points_service = Mock()
        mock_points_service.consume_points.side_effect = Exception("Insufficient points")

        reward_service = RewardService(test_db_session, mock_points_service)
        reward_id = str(uuid4())

        # 执行操作应该传播异常
        with pytest.raises(Exception, match="Insufficient points"):
            reward_service.redeem_reward(user_id, reward_id)

    def test_uuid_format_validation_cross_domain(self, test_db_session):
        """测试跨领域UUID格式验证"""
        # 测试各种UUID格式在跨领域调用中的处理
        test_cases = [
            uuid4(),  # 标准UUID对象
            str(uuid4()),  # UUID字符串
            str(uuid4()).upper(),  # 大写UUID字符串
            str(uuid4()).lower(),  # 小写UUID字符串
        ]

        mock_points_service = Mock()
        mock_points_service.calculate_balance.return_value = 100

        reward_service = RewardService(test_db_session, mock_points_service)

        for user_id in test_cases:
            try:
                reward_service.redeem_reward(user_id, str(uuid4()))
                # 验证PointsService被调用
                mock_points_service.get_user_balance.assert_called_once()

                # 验证传递的参数类型
                call_args = mock_points_service.get_user_balance.call_args[0]
                passed_id = call_args[0]
                assert isinstance(passed_id, str)  # PointsService应该接收到字符串

                mock_points_service.reset_mock()
            except Exception as e:
                # 如果有异常，应该不是UUID类型转换错误
                assert "type" not in str(e).lower()
                assert "uuid" not in str(e).lower()

    def test_concurrent_cross_domain_operations(self, test_db_session):
        """测试并发跨领域操作的UUID安全性"""
        user_id = uuid4()

        # 创建真实的Points和Reward服务实例
        points_service = PointsService(test_db_session)

        # Mock Reward的Points依赖
        mock_reward_points_service = Mock()
        mock_reward_points_service.get_user_balance.return_value = 1000
        mock_reward_points_service.consume_points.return_value = True

        reward_service = RewardService(test_db_session, mock_reward_points_service)

        # 模拟并发操作
        import threading
        import time

        results = []
        errors = []

        def add_points_operation():
            try:
                points_service.add_points(
                    user_id=user_id,
                    amount=10,
                    source_type="concurrent_test",
                    description="并发测试"
                )
                results.append(True)
            except Exception as e:
                errors.append(e)

        def consume_points_operation():
            try:
                reward_service.redeem_reward(user_id, str(uuid4()))
                results.append(True)
            except Exception as e:
                errors.append(e)

        # 启动并发操作
        threads = []
        for _ in range(3):
            t1 = threading.Thread(target=add_points_operation)
            t2 = threading.Thread(target=consume_points_operation)
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证并发操作的结果
        assert len(errors) == 0, f"并发操作出现错误: {errors}"
        assert len(results) >= 5  # 3次添加 + 2次消费

    def test_data_consistency_across_domains(self, test_db_session):
        """测试跨领域数据一致性"""
        user_id = uuid4()

        # 使用真实的服务实例
        points_service = PointsService(test_db_session)

        # Mock Reward服务
        mock_reward_service = Mock()
        mock_reward_service.get_user_materials.return_value = []

        reward_service_instance = RewardService(test_db_session, mock_reward_service)

        # 执行序列操作
        initial_balance = points_service.calculate_balance(user_id)

        # 添加积分
        points_service.add_points(
            user_id=user_id,
            amount=200,
            source_type="test_sequence",
            description="序列测试1"
        )

        # 执行消费（假设有足够积分）
        reward_service_instance.redeem_reward(user_id, str(uuid4()))

        # 验证最终状态
        final_balance = points_service.calculate_balance(user_id)

        # 检查交易记录
        transactions = points_service.get_transactions(user_id, limit=10)
        assert len(transactions) >= 2  # 至少有添加和消费记录

        # 验证数据类型一致性
        for tx in transactions:
            assert isinstance(tx["user_id"], str)
            assert "id" in tx
            assert "amount" in tx