"""
欢迎礼包服务单元测试

使用轻量级模拟环境进行测试，专注于单一组件的功能验证。

作者：TaKeKe团队
版本：1.0.0 - 单元测试标准化
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from unittest.mock import Mock, patch

from src.domains.reward.welcome_gift_service import WelcomeGiftService
from src.domains.points.service import PointsService


# 导入单元测试fixtures
pytest_plugins = ["tests.conftest_unit"]


@pytest.mark.unit
@pytest.mark.reward
class TestWelcomeGiftServiceUnit:
    """欢迎礼包服务单元测试类"""

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

    def test_service_initialization(self, mock_points_service, mock_session):
        """测试服务初始化"""
        service = WelcomeGiftService(mock_session, mock_points_service)

        assert service.session == mock_session
        assert service.points_service == mock_points_service
        assert hasattr(service, 'logger')
        assert hasattr(service, 'reward_repository')

    def test_claim_welcome_gift_basic_functionality(self, mock_points_service, mock_session):
        """测试基本欢迎礼包发放功能"""
        # 配置模拟服务
        mock_points_service.add_points.return_value = Mock(id=str(uuid4()))

        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        # 执行欢迎礼包发放
        result = service.claim_welcome_gift(user_id)

        # 验证结果结构
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

        # 验证发放时间格式
        granted_at = result["granted_at"]
        assert isinstance(granted_at, str)
        # 验证可以解析为ISO时间
        parsed_time = datetime.fromisoformat(granted_at.replace('Z', '+00:00'))
        assert isinstance(parsed_time, datetime)

    def test_claim_welcome_gift_with_uuid_object(self, mock_points_service, mock_session):
        """测试使用UUID对象调用欢迎礼包"""
        mock_points_service.add_points.return_value = Mock(id=str(uuid4()))

        service = WelcomeGiftService(mock_session, mock_points_service)
        user_uuid = uuid4()

        result = service.claim_welcome_gift(user_uuid)

        # 验证成功发放
        assert result["points_granted"] == 1000
        assert len(result["rewards_granted"]) == 3

        # 验证事务组包含UUID字符串
        transaction_group = result["transaction_group"]
        assert str(user_uuid) in transaction_group

    def test_transaction_group_id_generation(self, mock_points_service, mock_session):
        """测试事务组ID生成"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        # 调用生成方法
        with patch('src.domains.reward.welcome_gift_service.uuid4') as mock_uuid:
            test_uuid = str(uuid4())
            mock_uuid.return_value.hex = test_uuid[:8]  # 模拟hex方法

            transaction_group = service._generate_transaction_group_id(user_id)

        # 验证格式
        expected_format = f"welcome_gift_{user_id}_{test_uuid[:8]}"
        assert transaction_group == expected_format

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

    def test_claim_welcome_gift_points_service_calls(self, mock_points_service, mock_session):
        """测试欢迎礼包对积分服务的调用"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        # 模拟积分服务
        mock_points_service.add_points.return_value = Mock(id=str(uuid4()))

        service.claim_welcome_gift(user_id)

        # 验证调用次数：1000积分调用
        assert mock_points_service.add_points.call_count == 1

        # 验证积分发放调用参数
        call_args = mock_points_service.add_points.call_args
        assert call_args[0][0] == user_id  # user_id
        assert call_args[0][1] == 1000  # amount
        assert call_args[0][2] == "welcome_gift"  # source_type

    def test_get_user_gift_history_empty(self, mock_points_service, mock_session):
        """测试获取用户礼包历史 - 空结果"""
        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        # 模拟无交易记录
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.exec.return_value = mock_result

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

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_transaction]
        mock_session.exec.return_value = mock_result

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
        mock_points_service.add_points.return_value = Mock(id=str(uuid4()))

        # 执行并验证异常
        with pytest.raises(ValueError, match="欢迎礼包奖品.*不存在"):
            service.claim_welcome_gift(user_id)

    def test_welcome_gift_reward_quantities_validation(self, mock_points_service, mock_session):
        """测试欢迎礼包奖品数量验证"""
        mock_points_service.add_points.return_value = Mock(id=str(uuid4()))

        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        result = service.claim_welcome_gift(user_id)

        # 验证奖品数量
        rewards_granted = result["rewards_granted"]
        reward_quantities = {reward["name"]: reward["quantity"] for reward in rewards_granted}

        assert reward_quantities["积分加成卡"] == 3
        assert reward_quantities["专注道具"] == 10
        assert reward_quantities["时间管理券"] == 5

        # 验证总数
        total_quantity = sum(reward_quantities.values())
        assert total_quantity == 18  # 3 + 10 + 5

    def test_welcome_gift_timestamp_validation(self, mock_points_service, mock_session):
        """测试欢迎礼包时间戳验证"""
        mock_points_service.add_points.return_value = Mock(id=str(uuid4()))

        service = WelcomeGiftService(mock_session, mock_points_service)
        user_id = str(uuid4())

        # 记录执行前时间
        before_time = datetime.now(timezone.utc)

        result = service.claim_welcome_gift(user_id)

        # 记录执行后时间
        after_time = datetime.now(timezone.utc)

        # 验证时间戳格式和范围
        granted_at = result["granted_at"]
        assert isinstance(granted_at, str)

        # 验证可以解析为datetime
        parsed_time = datetime.fromisoformat(granted_at.replace('Z', '+00:00'))
        assert isinstance(parsed_time, datetime)

        # 验证时间在合理范围内（考虑时区转换）
        time_diff = abs((after_time - parsed_time).total_seconds())
        assert time_diff < 60  # 小于1分钟


@pytest.mark.unit
@pytest.mark.reward
class TestWelcomeGiftServiceEdgeCases:
    """欢迎礼包服务边界条件测试"""

    def test_empty_string_user_id(self, mock_points_service, mock_session):
        """测试空字符串用户ID"""
        service = WelcomeGiftService(mock_session, mock_points_service)

        mock_points_service.add_points.return_value = Mock(id=str(uuid4()))

        # 空字符串应该被正常处理
        result = service.claim_welcome_gift("")

        assert result["points_granted"] == 1000
        assert len(result["rewards_granted"]) == 3

    def test_none_user_id_handling(self, mock_points_service, mock_session):
        """测试None用户ID处理"""
        service = WelcomeGiftService(mock_session, mock_points_service)

        # None应该被转换为字符串
        result = service.claim_welcome_gift(None)

        assert result["points_granted"] == 1000
        assert len(result["rewards_granted"]) == 3

    def test_database_session_rollback_on_error(self, mock_points_service, mock_session):
        """测试错误时数据库会话回滚"""
        service = WelcomeGiftService(mock_session, mock_points_service)

        # 模拟数据库错误
        mock_points_service.add_points.side_effect = Exception("数据库连接失败")

        with pytest.raises(Exception, match="数据库连接失败"):
            service.claim_welcome_gift(str(uuid4()))

        # 验证回滚被调用
        mock_session.rollback.assert_called()

    def test_multiple_calls_different_users(self, mock_points_service, mock_session):
        """测试不同用户多次调用"""
        service = WelcomeGiftService(mock_session, mock_session)

        mock_points_service.add_points.return_value = Mock(id=str(uuid4()))

        user_ids = [str(uuid4()) for _ in range(3)]
        results = []

        for user_id in user_ids:
            result = service.claim_welcome_gift(user_id)
            results.append(result)

        # 验证每个用户都成功获得礼包
        for i, result in enumerate(results):
            assert result["points_granted"] == 1000
            assert len(result["rewards_granted"]) == 3
            assert user_ids[i] in result["transaction_group"]

        # 验证事务组ID唯一性
        transaction_groups = [result["transaction_group"] for result in results]
        assert len(set(transaction_groups)) == 3