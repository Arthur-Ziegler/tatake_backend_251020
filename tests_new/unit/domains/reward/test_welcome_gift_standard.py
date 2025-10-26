"""
欢迎礼包服务标准测试

使用标准conftest进行测试，重点关注核心功能验证。

作者：TaKeKe团队
版本：1.0.0 - 标准化测试
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from unittest.mock import Mock, patch

from src.domains.reward.welcome_gift_service import WelcomeGiftService
from src.domains.reward.database import get_reward_by_name


@pytest.mark.unit
class TestWelcomeGiftServiceStandard:
    """欢迎礼包服务标准测试类"""

    def test_service_initialization(self, mock_points_service, mock_session):
        """测试服务初始化"""
        service = WelcomeGiftService(mock_session, mock_points_service)

        assert service.session == mock_session
        assert service.points_service == mock_points_service
        assert hasattr(service, 'logger')

    def test_gift_constants(self):
        """测试欢迎礼包常量定义"""
        assert WelcomeGiftService.GIFT_POINTS == 1000
        assert len(WelcomeGiftService.GIFT_REWARDS) == 3

        # 验证奖品配置
        reward_names = [r["name"] for r in WelcomeGiftService.GIFT_REWARDS]
        assert "积分加成卡" in reward_names
        assert "专注道具" in reward_names
        assert "时间管理券" in reward_names

        # 验证数量配置
        reward_quantities = {r["name"]: r["quantity"] for r in WelcomeGiftService.GIFT_REWARDS}
        assert reward_quantities["积分加成卡"] == 3
        assert reward_quantities["专注道具"] == 10
        assert reward_quantities["时间管理券"] == 5

    def test_claim_welcome_gift_success(self, mock_points_service, mock_session):
        """测试成功领取欢迎礼包"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        # 模拟积分服务
        mock_points_service.add_points.return_value = Mock(id=uuid4())

        # 执行欢迎礼包发放
        result = service.claim_welcome_gift(user_id)

        # 验证结果结构
        assert "points_granted" in result
        assert "rewards_granted" in result
        assert "transaction_group" in result
        assert "granted_at" in result

        # 验证数值
        assert result["points_granted"] == 1000
        assert len(result["rewards_granted"]) == 3

        # 验证事务组ID
        transaction_group = result["transaction_group"]
        assert transaction_group.startswith("welcome_gift_")
        assert user_id in transaction_group

        # 验证时间戳
        granted_at = result["granted_at"]
        assert isinstance(granted_at, str)  # 服务返回字符串格式的ISO时间

    def test_generate_transaction_group_id(self, mock_points_service, mock_session):
        """测试事务组ID生成"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        with patch('src.domains.reward.welcome_gift_service.uuid4') as mock_uuid:
            test_uuid = str(uuid4())
            mock_uuid.return_value = UUID(test_uuid)

            result = service._generate_transaction_group_id(user_id)

        expected = f"welcome_gift_{user_id}_{test_uuid}"
        assert result == expected

    @patch('src.domains.reward.welcome_gift_service.get_reward_by_name')
    def test_get_reward_id_by_name_success(self, mock_get_reward, mock_points_service, mock_session):
        """测试根据名称获取奖品ID成功"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        reward_name = "积分加成卡"
        reward_id = "points-bonus-card-001"

        # 模拟成功获取奖品
        mock_reward = Mock()
        mock_reward.id = reward_id
        mock_get_reward.return_value = mock_reward

        result = service._get_reward_id_by_name(reward_name)

        assert result == reward_id
        mock_get_reward.assert_called_once_with(mock_session, reward_name)

    @patch('src.domains.reward.welcome_gift_service.get_reward_by_name')
    def test_get_reward_id_by_name_failure(self, mock_get_reward, mock_points_service, mock_session):
        """测试根据名称获取奖品ID失败"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        reward_name = "不存在的奖品"

        # 模拟奖品不存在
        mock_get_reward.side_effect = ValueError("奖品不存在")

        with pytest.raises(ValueError, match="欢迎礼包奖品 '不存在的奖品' 不存在"):
            service._get_reward_id_by_name(reward_name)

        mock_get_reward.assert_called_once_with(mock_session, reward_name)

    def test_claim_welcome_gift_with_uuid_object(self, mock_points_service, mock_session):
        """测试使用UUID对象调用欢迎礼包"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        user_uuid = uuid4()

        # 模拟积分服务
        mock_points_service.add_points.return_value = Mock(id=uuid4())

        result = service.claim_welcome_gift(user_uuid)

        # 验证成功发放
        assert result["points_granted"] == 1000
        assert len(result["rewards_granted"]) == 3

        # 验证事务组包含UUID字符串
        transaction_group = result["transaction_group"]
        assert str(user_uuid) in transaction_group

    def test_claim_welcome_gift_points_service_calls(self, mock_points_service, mock_session):
        """测试欢迎礼包对积分服务的调用"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        # 模拟积分服务
        mock_points_service.add_points.return_value = Mock(id=uuid4())

        service.claim_welcome_gift(user_id)

        # 验证调用次数：1000积分 + 3个奖品
        assert mock_points_service.add_points.call_count == 4

        # 验证积分发放调用
        points_call = mock_points_service.add_points.call_args_list[0]
        assert points_call[1] == 1000  # amount
        assert points_call[2] == "welcome_gift"  # source_type

    def test_get_user_gift_history_empty(self, mock_points_service, mock_session):
        """测试获取用户礼包历史 - 空结果"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        # 模拟无交易记录
        with patch.object(service, 'session') as mock_db_session:
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db_session.exec.return_value = mock_result

            history = service.get_user_gift_history(user_id, limit=5)

        # 验证空结果
        assert history == []

    def test_get_user_gift_history_with_data(self, mock_points_service, mock_session):
        """测试获取用户礼包历史 - 有数据"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        # 模拟积分交易记录
        mock_transaction = Mock()
        mock_transaction.id = uuid4()
        mock_transaction.amount = 1000
        mock_transaction.source_type = "welcome_gift"
        mock_transaction.transaction_group = f"welcome_gift_{user_id}_test_group"
        mock_transaction.created_at = datetime.now(timezone.utc)

        with patch.object(service, 'session') as mock_db_session:
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [mock_transaction]
            mock_db_session.exec.return_value = mock_result

            history = service.get_user_gift_history(user_id, limit=5)

        # 验证结果
        assert len(history) == 1
        assert history[0]["transaction_group"] == f"welcome_gift_{user_id}_test_group"
        assert history[0]["points_granted"] == 1000
        assert history[0]["rewards_count"] == 3

    def test_claim_welcome_gift_error_handling(self, mock_points_service, mock_session):
        """测试欢迎礼包发放错误处理"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        # 模拟积分服务错误
        mock_points_service.add_points.side_effect = Exception("数据库错误")

        # 验证异常传播
        with pytest.raises(Exception, match="数据库错误"):
            service.claim_welcome_gift(user_id)

    @patch('src.domains.reward.welcome_gift_service.get_reward_by_name')
    def test_claim_welcome_gift_reward_not_found(self, mock_get_reward, mock_points_service, mock_session):
        """测试欢迎礼包奖品不存在的情况"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        # 模拟第一个奖品存在，第二个不存在
        def side_effect_func(session, name):
            if name == "积分加成卡":
                mock_reward = Mock()
                mock_reward.id = "points-bonus-card-001"
                return mock_reward
            else:
                raise ValueError(f"奖品不存在: {name}")

        mock_get_reward.side_effect = side_effect_func
        mock_points_service.add_points.return_value = Mock(id=uuid4())

        # 执行并验证异常
        with pytest.raises(ValueError, match="欢迎礼包奖品.*不存在"):
            service.claim_welcome_gift(user_id)


@pytest.mark.integration
class TestWelcomeGiftServiceIntegrationStandard:
    """欢迎礼包服务集成测试"""

    def test_end_to_end_welcome_gift(self, test_db_session_with_data):
        """端到端测试欢迎礼包发放"""
        points_service = PointsService(test_db_session_with_data)
        welcome_gift_service = WelcomeGiftService(test_db_session_with_data, points_service)
        user_id = str(uuid4())

        # 验证初始状态
        initial_balance = points_service.calculate_balance(user_id)
        assert initial_balance == 0

        # 执行欢迎礼包发放
        result = welcome_gift_service.claim_welcome_gift(user_id)

        # 验证发放结果
        assert result["points_granted"] == 1000
        assert len(result["rewards_granted"]) == 3

        # 验证积分余额更新
        final_balance = points_service.calculate_balance(user_id)
        assert final_balance == 1000

        # 验证交易记录
        transactions = points_service.get_transactions(user_id, limit=10)
        assert len(transactions) >= 1

        # 验证历史记录
        history = welcome_gift_service.get_user_gift_history(user_id, limit=5)
        assert len(history) >= 1

        # 验证奖品列表
        rewards_granted = result["rewards_granted"]
        reward_names = [reward["name"] for reward in rewards_granted]
        assert "积分加成卡" in reward_names
        assert "专注道具" in reward_names
        assert "时间管理券" in reward_names

    def test_multiple_claims_no_limit(self, test_db_session_with_data):
        """测试多次领取（无防刷限制）"""
        points_service = PointsService(test_db_session_with_data)
        welcome_gift_service = WelcomeGiftService(test_db_session_with_data, points_service)
        user_id = str(uuid4())

        # 第一次领取
        result1 = welcome_gift_service.claim_welcome_gift(user_id)
        assert result1["points_granted"] == 1000

        # 第二次领取
        result2 = welcome_gift_service.claim_welcome_gift(user_id)
        assert result2["points_granted"] == 1000

        # 验证总积分
        total_balance = points_service.calculate_balance(user_id)
        assert total_balance == 2000

        # 验证历史记录数量
        history = welcome_gift_service.get_user_gift_history(user_id, limit=10)
        assert len(history) == 2

    def test_transaction_group_uniqueness(self, test_db_session_with_data):
        """测试事务组ID唯一性"""
        points_service = PointsService(test_db_session_with_data)
        welcome_gift_service = WelcomeGiftService(test_db_session_with_data, points_service)
        user_id = str(uuid4())

        # 多次领取
        results = []
        for i in range(3):
            mock_points_service_add_points(points_service, 1000, "welcome_gift")
            result = welcome_gift_service.claim_welcome_gift(user_id)
            results.append(result)

        # 验证事务组ID唯一性
        transaction_groups = [result["transaction_group"] for result in results]
        assert len(set(transaction_groups)) == 3  # 所有ID都不同

        # 验证每个事务组都包含用户ID
        for transaction_group in transaction_groups:
            assert user_id in transaction_group

    def test_reward_quantities_consistency(self, test_db_session_with_data):
        """测试奖品数量一致性"""
        points_service = PointsService(test_db_session_with_data)
        welcome_gift_service = WelcomeGiftService(test_db_session_with_data, points_service)
        user_id = str(uuid4())

        # 执行欢迎礼包发放
        result = welcome_gift_service.claim_welcome_gift(user_id)

        # 验证奖品数量
        rewards_granted = result["rewards_granted"]
        reward_quantities = {reward["name"]: reward["quantity"] for reward in rewards_granted}

        assert reward_quantities["积分加成卡"] == 3
        assert reward_quantities["专注道具"] == 10
        assert reward_quantities["time管理券"] == 5

        # 验证总数
        total_quantity = sum(reward_quantities.values())
        assert total_quantity == 18  # 3 + 10 + 5

    def test_welcome_gift_timestamp_format(self, test_db_session_with_data):
        """测试欢迎礼包时间戳格式"""
        points_service = PointsService(test_db_session_with_data)
        welcome_gift_service = WelcomeGiftService(test_db_session_with_data, points_service)
        user_id = str(uuid4())

        # 执行欢迎礼包发放
        result = welcome_gift_service.claim_welcome_gift(user_id)

        # 验证时间戳格式
        granted_at = result["granted_at"]
        assert isinstance(granted_at, str)

        # 验证可以解析为datetime
        parsed_time = datetime.fromisoformat(granted_at)
        assert isinstance(parsed_time, datetime)
        assert parsed_time.tzinfo is not None  # 包含时区信息

        # 验证时间在合理范围内（最近1分钟内）
        now = datetime.now(timezone.utc)
        time_diff = abs((now - parsed_time).total_seconds())
        assert time_diff < 60  # 小于1分钟