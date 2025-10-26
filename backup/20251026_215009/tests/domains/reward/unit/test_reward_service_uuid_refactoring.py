"""
Reward领域Service层UUID重构单元测试

测试RewardService的UUID类型安全重构，确保：
1. Service层正确使用UUIDConverter替代ensure_str
2. 方法签名保持一致，内部UUID处理统一
3. 与PointsService交互时传递正确格式
4. 错误处理和日志记录正确

遵循TDD原则：先写测试→最小实现→优化重构

作者：TaKeKe团队
版本：1.0.0 - Service层UUID重构
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import UUID, uuid4
from sqlmodel import Session

from src.domains.reward.service import RewardService
from src.domains.reward.models import Reward, RewardTransaction
from src.core.uuid_converter import UUIDConverter
from tests.conftest import test_db_session


@pytest.mark.unit
class TestRewardServiceUUIDRefactoring:
    """RewardService UUID重构单元测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # Mock PointsService
        self.mock_points_service = Mock()
        self.mock_points_service.get_user_balance.return_value = 1000
        self.mock_points_service.consume_points.return_value = True
        self.mock_points_service.add_points.return_value = True

    def test_redeem_reward_uses_uuid_converter(self, test_db_session):
        """测试redeem_reward方法使用UUIDConverter"""
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

        service = RewardService(test_db_session, self.mock_points_service)

        # Mock UUIDConverter to track calls
        with patch.object(UUIDConverter, 'to_string') as mock_converter:
            mock_converter.return_value = str(user_id)

            result = service.redeem_reward(user_id, str(reward.id))

            # 验证UUIDConverter被调用
            mock_converter.assert_called_once_with(user_id)

        # 验证PointsService接收到字符串格式
        self.mock_points_service.get_user_balance.assert_called_once()
        call_args = self.mock_points_service.get_user_balance.call_args[0][0]
        assert isinstance(call_args, str)
        assert len(call_args) == 36  # UUID字符串长度

    def test_top3_lottery_uses_uuid_converter(self, test_db_session):
        """测试top3_lottery方法使用UUIDConverter"""
        user_id = uuid4()
        task_ids = [str(uuid4()), str(uuid4())]

        service = RewardService(test_db_session, self.mock_points_service)

        with patch.object(UUIDConverter, 'to_string') as mock_converter:
            mock_converter.return_value = str(user_id)

            result = service.top3_lottery(user_id, task_ids)

            # 验证UUIDConverter被调用
            mock_converter.assert_called_once_with(user_id)

        # 验证PointsService接收到字符串格式
        self.mock_points_service.consume_points.assert_called_once()
        call_args = self.mock_points_service.consume_points.call_args[0][0]
        assert isinstance(call_args, str)

    def test_get_reward_transactions_uses_uuid_converter(self, test_db_session):
        """测试get_reward_transactions方法使用UUIDConverter"""
        user_id = uuid4()

        service = RewardService(test_db_session, self.mock_points_service)

        with patch.object(UUIDConverter, 'to_string') as mock_converter:
            mock_converter.return_value = str(user_id)

            result = service.get_reward_transactions(user_id, limit=10)

            # 验证UUIDConverter被调用
            mock_converter.assert_called_once_with(user_id)

        # 验证返回结果格式正确
        assert isinstance(result, dict)
        assert "transactions" in result
        assert isinstance(result["transactions"], list)

    def test_compose_rewards_uses_uuid_converter(self, test_db_session):
        """测试compose_rewards方法使用UUIDConverter"""
        user_id = uuid4()
        recipe_id = str(uuid4())

        service = RewardService(test_db_session, self.mock_points_service)

        # Mock RecipeRepository
        mock_recipe_repository = Mock()
        mock_recipe_repository.get_recipe_by_id.return_value = {
            "id": recipe_id,
            "name": "测试配方",
            "materials_required": [],
            "result_reward": {"id": str(uuid4()), "name": "测试结果"}
        }
        service.recipe_repository = mock_recipe_repository

        with patch.object(UUIDConverter, 'to_string') as mock_converter:
            mock_converter.return_value = str(user_id)

            try:
                result = service.compose_rewards(user_id, recipe_id)
            except Exception:
                # 可能因为材料不足而失败，这是正常的
                pass

            # 验证UUIDConverter被调用
            mock_converter.assert_called_once_with(user_id)

    def test_get_user_materials_uses_uuid_converter(self, test_db_session):
        """测试get_user_materials方法使用UUIDConverter"""
        user_id = uuid4()

        service = RewardService(test_db_session, self.mock_points_service)

        with patch.object(UUIDConverter, 'to_string') as mock_converter:
            mock_converter.return_value = str(user_id)

            result = service.get_user_materials(user_id)

            # 验证UUIDConverter被调用
            mock_converter.assert_called_once_with(user_id)

        # 验证返回结果格式正确
        assert isinstance(result, list)

    def test_get_my_rewards_uses_uuid_converter(self, test_db_session):
        """测试get_my_rewards方法使用UUIDConverter"""
        user_id = uuid4()

        service = RewardService(test_db_session, self.mock_points_service)

        with patch.object(UUIDConverter, 'to_string') as mock_converter:
            mock_converter.return_value = str(user_id)

            result = service.get_my_rewards(user_id)

            # 验证UUIDConverter被调用
            mock_converter.assert_called_once_with(user_id)

        # 验证返回结果格式正确
        assert isinstance(result, dict)
        assert "materials" in result
        assert "total_types" in result

    def test_uuid_converter_error_handling(self, test_db_session):
        """测试UUIDConverter错误处理"""
        user_id = uuid4()

        service = RewardService(test_db_session, self.mock_points_service)

        # Mock UUIDConverter抛出异常
        with patch.object(UUIDConverter, 'to_string') as mock_converter:
            mock_converter.side_effect = ValueError("Invalid UUID")

            # 验证异常被正确传播
            with pytest.raises(ValueError, match="Invalid UUID"):
                service.get_reward_transactions(user_id)

    def test_logging_uuid_conversion(self, test_db_session):
        """测试UUID转换的日志记录"""
        user_id = uuid4()

        service = RewardService(test_db_session, self.mock_points_service)

        with patch.object(service.logger, 'info') as mock_logger:
            with patch.object(UUIDConverter, 'to_string') as mock_converter:
                mock_converter.return_value = str(user_id)

                result = service.get_reward_transactions(user_id)

                # 验证日志记录包含UUID字符串
                mock_logger.assert_called()
                log_message = mock_logger.call_args[0][0]
                assert str(user_id) in log_message

    def test_performance_uuid_conversion_overhead(self, test_db_session):
        """测试UUID转换的性能开销"""
        user_id = uuid4()

        service = RewardService(test_db_session, self.mock_points_service)

        # 测试多次调用的性能
        import time

        with patch.object(UUIDConverter, 'to_string') as mock_converter:
            mock_converter.return_value = str(user_id)

            start_time = time.perf_counter()

            # 执行多次UUID转换
            for _ in range(1000):
                service.get_reward_transactions(user_id)

            end_time = time.perf_counter()
            total_time = end_time - start_time

            # 验证性能合理（1000次调用应该在1秒内完成）
            assert total_time < 1.0
            # 验证UUIDConverter被调用正确次数
            assert mock_converter.call_count == 1000

    def test_uuid_type_safety_edge_cases(self, test_db_session):
        """测试UUID类型安全的边界情况"""
        # 测试各种UUID输入类型
        test_cases = [
            uuid4(),  # 标准UUID对象
            str(uuid4()),  # UUID字符串
        ]

        service = RewardService(test_db_session, self.mock_points_service)

        for user_id in test_cases:
            with patch.object(UUIDConverter, 'to_string') as mock_converter:
                mock_converter.return_value = str(user_id) if isinstance(user_id, UUID) else user_id

                result = service.get_reward_transactions(user_id)

                # 验证UUIDConverter被调用
                mock_converter.assert_called_once()
                mock_converter.reset_mock()