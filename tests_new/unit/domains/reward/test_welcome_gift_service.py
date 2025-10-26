"""
欢迎礼包服务单元测试

测试欢迎礼包服务的完整功能，包括：
1. 欢迎礼包发放逻辑
2. 积分和奖品记录创建
3. 事务管理和错误处理
4. 历史记录查询

作者：TaKeKe团队
版本：1.0.0 - TDD严格测试
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from unittest.mock import Mock, patch
from sqlmodel import Session

from src.domains.reward.welcome_gift_service import WelcomeGiftService
from src.domains.points.service import PointsService
from src.domains.points.models import PointsTransaction
from src.domains.reward.models import RewardTransaction
from src.core.uuid_converter import UUIDConverter


@pytest.mark.unit
class TestWelcomeGiftService:
    """欢迎礼包服务测试类"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_points_service(self, mock_session):
        """模拟积分服务"""
        return Mock(spec=PointsService)

    @pytest.fixture
    def welcome_gift_service(self, mock_session, mock_points_service):
        """欢迎礼包服务实例"""
        return WelcomeGiftService(mock_session, mock_points_service)

    def test_welcome_gift_service_initialization(self, mock_session, mock_points_service):
        """测试欢迎礼包服务初始化"""
        service = WelcomeGiftService(mock_session, mock_points_service)

        assert service.session == mock_session
        assert service.points_service == mock_points_service
        assert service.logger is not None

    @patch('src.domains.reward.welcome_gift_service.uuid4')
    def test_claim_welcome_gift_success(self, mock_uuid4, welcome_gift_service, mock_points_service):
        """测试成功领取欢迎礼包"""
        # 模拟UUID生成
        transaction_group_id = str(uuid4())
        mock_uuid4.return_value.uuid4.return_value = UUID(transaction_group_id)

        user_id = str(uuid4())
        user_uuid = UUID(user_id)

        # 模拟积分服务方法
        mock_points_service.add_points.return_value = Mock(id=uuid4())

        # 执行欢迎礼包发放
        result = welcome_gift_service.claim_welcome_gift(user_uuid)

        # 验证结果结构
        assert result["success"] is True
        assert result["points_granted"] == 1000
        assert len(result["rewards_granted"]) == 3
        assert result["transaction_group"] == f"welcome_gift_{user_id}_{transaction_group_id}"
        assert result["granted_at"] is not None

        # 验证积分调用
        assert mock_points_service.add_points.call_count == 4  # 1000积分 + 3个奖品

        # 验证积分调用参数
        points_call = mock_points_service.add_points.call_args_list[0]
        assert points_call[1] == 1000
        assert points_call[2] == "welcome_gift"
        assert points_call.kwargs["transaction_group"] == f"welcome_gift_{user_id}_{transaction_group_id}"

    def test_claim_welcome_gift_with_string_user_id(self, welcome_gift_service, mock_points_service):
        """测试使用字符串用户ID领取欢迎礼包"""
        user_id_str = str(uuid4())

        # 模拟积分服务方法
        mock_points_service.add_points.return_value = Mock(id=uuid4())

        # 执行欢迎礼包发放
        result = welcome_gift_service.claim_welcome_gift(user_id_str)

        # 验证成功发放
        assert result["success"] is True
        assert result["points_granted"] == 1000

    @patch('src.domains.reward.welcome_gift_service.uuid4')
    def test_claim_welcome_gift_transaction_group_generation(self, mock_uuid4, welcome_gift_service, mock_points_service):
        """测试事务组ID生成格式"""
        user_id = str(uuid4())
        generated_uuid = str(uuid4())
        mock_uuid4.return_value.uuid4.return_value = UUID(generated_uuid)

        # 模拟积分服务方法
        mock_points_service.add_points.return_value = Mock(id=uuid4())

        # 执行欢迎礼包发放
        result = welcome_gift_service.claim_welcome_gift(user_id)

        # 验证事务组ID格式
        expected_format = f"welcome_gift_{user_id}_{generated_uuid}"
        assert result["transaction_group"] == expected_format

    def test_claim_welcome_gift_database_error_handling(self, welcome_gift_service, mock_points_service):
        """测试数据库错误处理"""
        user_id = str(uuid4())

        # 模拟数据库错误
        mock_points_service.add_points.side_effect = Exception("数据库连接失败")

        # 执行并验证异常处理
        with pytest.raises(Exception, match="数据库连接失败"):
            welcome_gift_service.claim_welcome_gift(user_id)

    def test_get_reward_id_by_name_existing_reward(self, welcome_gift_service):
        """测试根据名称获取已存在奖品的ID"""
        reward_name = "积分加成卡"
        reward_id = "points-bonus-card-001"

        # 模拟get_reward_by_name函数
        mock_reward = Mock()
        mock_reward.id = reward_id

        with patch('src.domains.reward.welcome_gift_service.get_reward_by_name', return_value=mock_reward):
            result = welcome_gift_service._get_reward_id_by_name(reward_name)

        assert result == reward_id

    def test_get_reward_id_by_name_nonexistent_reward(self, welcome_gift_service):
        """测试根据名称获取不存在奖品的ID"""
        reward_name = "不存在的奖品"

        # 模拟get_reward_by_name抛出异常
        with patch('src.domains.reward.welcome_gift_service.get_reward_by_name') as mock_get_reward:
            mock_get_reward.side_effect = ValueError("奖品不存在: 不存在的奖品")

            # 验证异常传播
            with pytest.raises(ValueError, match="欢迎礼包奖品 '不存在的奖品' 不存在"):
                welcome_gift_service._get_reward_id_by_name(reward_name)

    def test_create_reward_transactions_success(self, welcome_gift_service):
        """测试成功创建奖品交易记录"""
        user_id = str(uuid4())
        transaction_group = f"test_group_{uuid4()}"

        # 创建模拟奖品交易
        mock_transaction = Mock()
        mock_transaction.id = uuid4()
        welcome_gift_service.session.add.return_value = None
        welcome_gift_service.session.flush.return_value = None

        # 执行创建奖品交易
        with patch('src.domains.reward.welcome_gift_service.RewardTransaction') as mock_reward_tx_class:
            mock_reward_tx_class.return_value = mock_transaction

            result = welcome_gift_service._create_reward_transactions(
                user_id, transaction_group
            )

        # 验证结果
        assert len(result) == 3
        assert all("name" in item and "quantity" in item for item in result)

        # 验证奖品名称和数量
        reward_names = [item["name"] for item in result]
        assert "积分加成卡" in reward_names
        assert "专注道具" in reward_names
        assert "时间管理券" in reward_names

    def test_get_user_gift_history_success(self, welcome_gift_service):
        """测试成功获取用户礼包历史"""
        user_id = str(uuid4())
        limit = 5

        # 模拟积分交易记录
        mock_points_tx = Mock()
        mock_points_tx.id = uuid4()
        mock_points_tx.amount = 1000
        mock_points_tx.source_type = "welcome_gift"
        mock_points_tx.transaction_group = f"welcome_gift_{user_id}_group1"
        mock_points_tx.created_at = datetime.now(timezone.utc)

        # 模拟查询结果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_points_tx]
        welcome_gift_service.session.exec.return_value = mock_result

        # 执行查询
        history = welcome_gift_service.get_user_gift_history(user_id, limit)

        # 验证结果
        assert len(history) == 1
        assert history[0]["transaction_group"] == f"welcome_gift_{user_id}_group1"
        assert history[0]["points_granted"] == 1000
        assert history[0]["rewards_count"] == 3

    def test_get_user_gift_history_empty_result(self, welcome_gift_service):
        """测试获取空历史记录"""
        user_id = str(uuid4())

        # 模拟空查询结果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        welcome_gift_service.session.exec.return_value = mock_result

        # 执行查询
        history = welcome_gift_service.get_user_gift_history(user_id)

        # 验证空结果
        assert history == []

    def test_get_user_gift_history_with_uuid_parameter(self, welcome_gift_service):
        """测试使用UUID参数获取礼包历史"""
        user_uuid = uuid4()

        # 模拟空查询结果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        welcome_gift_service.session.exec.return_value = mock_result

        # 执行查询（使用UUID对象）
        history = welcome_gift_service.get_user_gift_history(user_uuid)

        # 验证查询执行
        assert history == []

    @pytest.mark.parametrize("reward_name,expected_quantity", [
        ("积分加成卡", 3),
        ("专注道具", 10),
        ("时间管理券", 5)
    ])
    def test_welcome_gift_reward_quantities(self, welcome_gift_service, mock_points_service, reward_name, expected_quantity):
        """测试欢迎礼包中各种奖品的数量"""
        user_id = str(uuid4())

        # 模拟积分服务方法
        mock_points_service.add_points.return_value = Mock(id=uuid4())

        # 执行欢迎礼包发放
        result = welcome_gift_service.claim_welcome_gift(user_id)

        # 验证指定奖品的数量
        reward_items = [item for item in result["rewards_granted"] if item["name"] == reward_name]
        assert len(reward_items) == 1
        assert reward_items[0]["quantity"] == expected_quantity

    def test_welcome_gift_granted_at_timestamp(self, welcome_gift_service, mock_points_service):
        """测试欢迎礼包发放时间戳"""
        user_id = str(uuid4())

        # 模拟积分服务方法
        mock_points_service.add_points.return_value = Mock(id=uuid4())

        # 记录执行前时间
        before_time = datetime.now(timezone.utc)

        # 执行欢迎礼包发放
        result = welcome_gift_service.claim_welcome_gift(user_id)

        # 记录执行后时间
        after_time = datetime.now(timezone.utc)

        # 验证时间戳在合理范围内
        granted_at = result["granted_at"]
        assert before_time <= granted_at <= after_time
        assert granted_at.tzinfo == timezone.utc


@pytest.mark.integration
class TestWelcomeGiftServiceIntegration:
    """欢迎礼包服务集成测试类"""

    def test_welcome_gift_end_to_end_flow(self, test_db_session):
        """测试欢迎礼包端到端流程"""
        # 创建真实的服务实例
        points_service = PointsService(test_db_session)
        welcome_gift_service = WelcomeGiftService(test_db_session, points_service)

        user_id = str(uuid4())

        # 执行欢迎礼包发放
        result = welcome_gift_service.claim_welcome_gift(user_id)

        # 验证发放成功
        assert result["success"] is True
        assert result["points_granted"] == 1000
        assert len(result["rewards_granted"]) == 3

        # 验证积分余额
        balance = points_service.calculate_balance(user_id)
        assert balance == 1000

        # 验证积分交易记录
        transactions = points_service.get_transactions(user_id, limit=10)
        assert len(transactions) == 4  # 1000积分 + 3个奖品

        # 验证历史记录
        history = welcome_gift_service.get_user_gift_history(user_id, limit=5)
        assert len(history) == 1
        assert history[0]["points_granted"] == 1000
        assert history[0]["rewards_count"] == 3

    def test_welcome_gift_multiple_claims(self, test_db_session):
        """测试多次领取欢迎礼包（无防刷限制）"""
        points_service = PointsService(test_db_session)
        welcome_gift_service = WelcomeGiftService(test_db_session, points_service)

        user_id = str(uuid4())

        # 第一次领取
        result1 = welcome_gift_service.claim_welcome_gift(user_id)
        assert result1["success"] is True

        # 第二次领取
        result2 = welcome_gift_service.claim_welcome_gift(user_id)
        assert result2["success"] is True

        # 验证总积分
        total_balance = points_service.calculate_balance(user_id)
        assert total_balance == 2000  # 两次1000积分

        # 验证历史记录数量
        history = welcome_gift_service.get_user_gift_history(user_id, limit=10)
        assert len(history) == 2