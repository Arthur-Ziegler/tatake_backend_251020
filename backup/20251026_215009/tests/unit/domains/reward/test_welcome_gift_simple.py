"""
欢迎礼包服务简化测试

专注于测试核心功能的正确性。

作者：TaKeKe团队
版本：1.0.0 - 简化测试
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import Mock, patch
from sqlmodel import Session

from src.domains.reward.welcome_gift_service import WelcomeGiftService
from src.domains.points.service import PointsService


@pytest.mark.unit
class TestWelcomeGiftServiceSimple:
    """欢迎礼包服务简化测试类"""

    def test_welcome_gift_constants(self):
        """测试欢迎礼包常量定义"""
        assert WelcomeGiftService.GIFT_POINTS == 1000
        assert len(WelcomeGiftService.GIFT_REWARDS) == 3

        # 验证奖品内容
        reward_names = [reward["name"] for reward in WelcomeGiftService.GIFT_REWARDS]
        assert "积分加成卡" in reward_names
        assert "专注道具" in reward_names
        assert "时间管理券" in reward_names

        # 验证奖品数量
        reward_quantities = {reward["name"]: reward["quantity"] for reward in WelcomeGiftService.GIFT_REWARDS}
        assert reward_quantities["积分加成卡"] == 3
        assert reward_quantities["专注道具"] == 10
        assert reward_quantities["时间管理券"] == 5

    def test_initialization(self):
        """测试欢迎礼包服务初始化"""
        mock_session = Mock(spec=Session)
        mock_points_service = Mock(spec=PointsService)

        service = WelcomeGiftService(mock_session, mock_points_service)

        assert service.session == mock_session
        assert service.points_service == mock_points_service
        assert hasattr(service, 'logger')

    def test_claim_welcome_gift_basic(self):
        """测试基本欢迎礼包发放功能"""
        mock_session = Mock(spec=Session)
        mock_points_service = Mock(spec=PointsService)

        # 模拟积分服务成功添加积分
        mock_points_service.add_points.return_value = Mock(id=uuid4())

        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        # 执行欢迎礼包发放
        result = service.claim_welcome_gift(user_id)

        # 验证基本结果结构
        assert "points_granted" in result
        assert "rewards_granted" in result
        assert "transaction_group" in result
        assert "granted_at" in result

        # 验证积分发放
        assert result["points_granted"] == 1000

        # 验证奖品发放
        assert len(result["rewards_granted"]) == 3

        # 验证事务组ID格式
        assert result["transaction_group"].startswith("welcome_gift_")
        assert user_id in result["transaction_group"]

        # 验证发放时间
        granted_at = result["granted_at"]
        assert isinstance(granted_at, datetime)
        assert granted_at.tzinfo == timezone.utc

    def test_generate_transaction_group_id(self):
        """测试事务组ID生成"""
        mock_session = Mock(spec=Session)
        mock_points_service = Mock(spec=PointsService)

        service = WelcomeGiftService(mock_session, mock_points_service)

        user_id = str(uuid4())

        # 调用生成方法
        with patch('src.domains.reward.welcome_gift_service.uuid4') as mock_uuid:
            test_uuid = str(uuid4())
            mock_uuid.return_value = UUID(test_uuid)

            transaction_group = service._generate_transaction_group_id(user_id)

        # 验证格式
        expected = f"welcome_gift_{user_id}_{test_uuid}"
        assert transaction_group == expected

    def test_get_reward_id_by_name_success(self):
        """测试根据名称获取奖品ID成功"""
        mock_session = Mock(spec=Session)
        mock_points_service = Mock(spec=PointsService)

        service = WelcomeGiftService(mock_session, mock_points_service)
        reward_name = "积分加成卡"
        reward_id = "points-bonus-card-001"

        # 模拟成功获取奖品
        mock_reward = Mock()
        mock_reward.id = reward_id

        with patch('src.domains.reward.welcome_gift_service.get_reward_by_name', return_value=mock_reward):
            result = service._get_reward_id_by_name(reward_name)

        assert result == reward_id

    def test_get_reward_id_by_name_failure(self):
        """测试根据名称获取奖品ID失败"""
        mock_session = Mock(spec=Session)
        mock_points_service = Mock(spec=PointsService)

        service = WelcomeGiftService(mock_session, mock_points_service)
        reward_name = "不存在的奖品"

        # 模拟奖品不存在
        with patch('src.domains.reward.welcome_gift_service.get_reward_by_name') as mock_get:
            mock_get.side_effect = ValueError("奖品不存在")

            with pytest.raises(ValueError, match="欢迎礼包奖品 '不存在的奖品' 不存在"):
                service._get_reward_id_by_name(reward_name)

    def test_claim_welcome_gift_with_uuid(self):
        """测试使用UUID对象调用欢迎礼包"""
        mock_session = Mock(spec=Session)
        mock_points_service = Mock(spec=PointsService)
        mock_points_service.add_points.return_value = Mock(id=uuid4())

        service = WelcomeGiftService(mock_session, mock_points_service)
        user_uuid = uuid4()

        # 执行欢迎礼包发放
        result = service.claim_welcome_gift(user_uuid)

        # 验证成功发放
        assert result["points_granted"] == 1000
        assert len(result["rewards_granted"]) == 3


@pytest.mark.integration
class TestWelcomeGiftServiceIntegration:
    """欢迎礼包服务集成测试"""

    def test_end_to_end_welcome_gift(self, test_db_session):
        """端到端测试欢迎礼包发放"""
        points_service = PointsService(test_db_session)
        welcome_gift_service = WelcomeGiftService(test_db_session, points_service)

        user_id = str(uuid4())

        # 验证初始余额为0
        initial_balance = points_service.calculate_balance(user_id)
        assert initial_balance == 0

        # 发放欢迎礼包
        result = welcome_gift_service.claim_welcome_gift(user_id)

        # 验证结果
        assert result["points_granted"] == 1000
        assert len(result["rewards_granted"]) == 3

        # 验证最终余额
        final_balance = points_service.calculate_balance(user_id)
        assert final_balance == 1000

        # 验证交易记录
        transactions = points_service.get_transactions(user_id, limit=10)
        assert len(transactions) >= 1

        # 验证历史记录
        history = welcome_gift_service.get_user_gift_history(user_id, limit=5)
        assert len(history) >= 1
        assert history[0]["points_granted"] == 1000