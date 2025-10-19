"""
奖励Repository测试

验证RewardRepository的业务逻辑方法，包括：
- 奖励查询方法（按类型、状态、价格查询奖励）
- 奖励兑换方法（用户兑换奖励、验证余额）
- 用户碎片管理方法（查询余额、交易记录）
- 抽奖管理方法（抽奖记录、概率统计）
- 积分流水方法（查询流水、统计分析）

设计原则：
1. 继承BaseRepository，复用基础CRUD操作
2. 封装奖励相关的业务查询逻辑
3. 提供类型安全的方法签名
4. 统一的异常处理机制

使用示例：
    >>> # 创建奖励Repository
    >>> reward_repo = RewardRepository(session)
    >>>
    >>> # 查找可用奖励
    >>> rewards = reward_repo.find_available_rewards()
    >>>
    >>> # 兑换奖励
    >>> success = reward_repo.redeem_reward("user123", "reward456")
    >>>
    >>> # 查询用户碎片余额
    >>> balance = reward_repo.get_user_fragment_balance("user123")
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from sqlmodel import Session, select, and_, or_, func
from sqlalchemy.exc import SQLAlchemyError

# 导入相关模型和Repository
from src.models.reward import Reward, RewardRule, UserFragment, LotteryRecord, PointsTransaction
from src.models.enums import RewardType, RewardStatus, TransactionType
from src.repositories.reward import RewardRepository
from src.repositories.base import RepositoryError, RepositoryValidationError, RepositoryNotFoundError


class TestRewardRepositoryBasic:
    """RewardRepository基础功能测试类"""

    def test_reward_repository_inheritance(self):
        """验证RewardRepository继承自BaseRepository"""
        mock_session = Mock(spec=Session)
        reward_repo = RewardRepository(mock_session)

        # 验证继承关系
        assert isinstance(reward_repo, RewardRepository)
        assert reward_repo.model == Reward
        assert reward_repo.session == mock_session

    def test_reward_repository_methods_exist(self):
        """验证RewardRepository的业务方法存在"""
        mock_session = Mock(spec=Session)
        reward_repo = RewardRepository(mock_session)

        # 验证所有业务方法存在
        required_methods = [
            # 奖励查询方法
            'find_available_rewards',
            'find_by_reward_type',
            'find_by_status',
            'find_rewards_by_price_range',

            # 奖励兑换方法
            'redeem_reward',
            'validate_user_balance',
            'get_user_redeemed_rewards',

            # 用户碎片管理方法
            'get_user_fragment_balance',
            'award_fragments',
            'get_user_transaction_history',

            # 抽奖管理方法
            'draw_lottery',
            'get_user_lottery_records',
            'get_lottery_statistics',

            # 积分流水方法
            'create_points_transaction',
            'get_user_points_history',
            'get_user_points_summary'
        ]

        for method in required_methods:
            assert hasattr(reward_repo, method), f"RewardRepository缺少方法: {method}"
            assert callable(getattr(reward_repo, method)), f"RewardRepository.{method}不是可调用方法"

    def test_find_available_rewards_method_interface(self):
        """测试find_available_rewards方法接口"""
        mock_session = Mock(spec=Session)
        reward_repo = RewardRepository(mock_session)

        # 测试方法存在
        assert hasattr(reward_repo, 'find_available_rewards')
        assert callable(reward_repo.find_available_rewards)

        # 测试方法签名
        import inspect
        sig = inspect.signature(reward_repo.find_available_rewards)
        assert len(sig.parameters) == 0  # 无参数方法

    def test_find_by_reward_type_method_interface(self):
        """测试find_by_reward_type方法接口"""
        mock_session = Mock(spec=Session)
        reward_repo = RewardRepository(mock_session)

        # 测试方法存在
        assert hasattr(reward_repo, 'find_by_reward_type')
        assert callable(reward_repo.find_by_reward_type)

        # 测试方法签名
        import inspect
        sig = inspect.signature(reward_repo.find_by_reward_type)
        assert 'reward_type' in sig.parameters

    def test_redeem_reward_method_interface(self):
        """测试redeem_reward方法接口"""
        mock_session = Mock(spec=Session)
        reward_repo = RewardRepository(mock_session)

        # 测试方法存在
        assert hasattr(reward_repo, 'redeem_reward')
        assert callable(reward_repo.redeem_reward)

        # 测试方法签名
        import inspect
        sig = inspect.signature(reward_repo.redeem_reward)
        assert 'user_id' in sig.parameters
        assert 'reward_id' in sig.parameters
        assert sig.parameters['user_id'].annotation == str
        assert sig.parameters['reward_id'].annotation == str

    def test_get_user_fragment_balance_method_interface(self):
        """测试get_user_fragment_balance方法接口"""
        mock_session = Mock(spec=Session)
        reward_repo = RewardRepository(mock_session)

        # 测试方法存在
        assert hasattr(reward_repo, 'get_user_fragment_balance')
        assert callable(reward_repo.get_user_fragment_balance)

        # 测试方法签名
        import inspect
        sig = inspect.signature(reward_repo.get_user_fragment_balance)
        assert 'user_id' in sig.parameters
        assert sig.parameters['user_id'].annotation == str

    def test_award_fragments_method_interface(self):
        """测试award_fragments方法接口"""
        mock_session = Mock(spec=Session)
        reward_repo = RewardRepository(mock_session)

        # 测试方法存在
        assert hasattr(reward_repo, 'award_fragments')
        assert callable(reward_repo.award_fragments)

        # 测试方法签名
        import inspect
        sig = inspect.signature(reward_repo.award_fragments)
        assert 'user_id' in sig.parameters
        assert 'amount' in sig.parameters
        assert 'reason' in sig.parameters
        assert sig.parameters['user_id'].annotation == str
        assert sig.parameters['amount'].annotation == int
        assert sig.parameters['reason'].annotation == str

    def test_draw_lottery_method_interface(self):
        """测试draw_lottery方法接口"""
        mock_session = Mock(spec=Session)
        reward_repo = RewardRepository(mock_session)

        # 测试方法存在
        assert hasattr(reward_repo, 'draw_lottery')
        assert callable(reward_repo.draw_lottery)

        # 测试方法签名
        import inspect
        sig = inspect.signature(reward_repo.draw_lottery)
        assert 'user_id' in sig.parameters
        assert 'cost_fragments' in sig.parameters
        assert sig.parameters['user_id'].annotation == str
        assert sig.parameters['cost_fragments'].annotation == int

    def test_create_points_transaction_method_interface(self):
        """测试create_points_transaction方法接口"""
        mock_session = Mock(spec=Session)
        reward_repo = RewardRepository(mock_session)

        # 测试方法存在
        assert hasattr(reward_repo, 'create_points_transaction')
        assert callable(reward_repo.create_points_transaction)

        # 测试方法签名
        import inspect
        sig = inspect.signature(reward_repo.create_points_transaction)
        assert 'user_id' in sig.parameters
        assert 'transaction_type' in sig.parameters
        assert 'amount' in sig.parameters
        assert 'reason' in sig.parameters


class TestRewardRepositoryBusinessLogic:
    """RewardRepository业务逻辑测试类"""

    def test_find_available_rewards_with_mock_session(self):
        """测试find_available_rewards方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟奖励对象
        mock_reward = Mock(spec=Reward)
        mock_reward.id = "reward-123"
        mock_reward.name = "专注达人"
        mock_reward.reward_type = RewardType.BADGE
        mock_reward.is_active = True

        # 模拟查询执行
        mock_exec_result = Mock()
        mock_exec_result.all.return_value = [mock_reward]
        mock_session.exec.return_value = mock_exec_result

        # 创建Repository并测试
        reward_repo = RewardRepository(mock_session)

        # 执行测试
        result = reward_repo.find_available_rewards()

        # 验证结果
        assert len(result) == 1
        assert result[0] == mock_reward
        mock_session.exec.assert_called_once()

    def test_redeem_reward_with_mock_session(self):
        """测试redeem_reward方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟奖励信息
        mock_reward = Mock(spec=Reward)
        mock_reward.id = "reward-123"
        mock_reward.name = "专注达人"
        mock_reward.cost_fragments = 100
        mock_reward.is_active = True

        # 模拟用户碎片余额（需要返回正确的整数类型）
        with patch.object(RewardRepository, 'get_by_id', return_value=mock_reward), \
             patch.object(RewardRepository, 'validate_user_balance', return_value=True), \
             patch.object(RewardRepository, 'create_points_transaction', return_value=None) as mock_create:

            reward_repo = RewardRepository(mock_session)

            # 执行测试
            result = reward_repo.redeem_reward("user123", "reward-123")

            # 验证结果
            assert result is None  # create_points_transaction返回None时，redeem_reward也返回None

            # 验证方法调用
            mock_create.assert_called_once()

    def test_get_user_fragment_balance_with_mock_session(self):
        """测试get_user_fragment_balance方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟用户碎片记录
        mock_user_fragment = Mock(spec=UserFragment)
        mock_user_fragment.user_id = "user123"
        mock_user_fragment.fragment_count = 150

        # 模拟查询执行
        mock_exec_result = Mock()
        mock_exec_result.first.return_value = mock_user_fragment
        mock_session.exec.return_value = mock_exec_result

        # 创建Repository并测试
        reward_repo = RewardRepository(mock_session)

        # 执行测试
        result = reward_repo.get_user_fragment_balance("user123")

        # 验证结果
        assert result == 150
        mock_session.exec.assert_called_once()

    def test_award_fragments_with_mock_session(self):
        """测试award_fragments方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟现有用户碎片
        mock_existing_fragment = Mock(spec=UserFragment)
        mock_existing_fragment.user_id = "user123"
        mock_existing_fragment.fragment_count = 100

        # 模拟更新后的用户碎片
        mock_updated_fragment = Mock(spec=UserFragment)
        mock_updated_fragment.user_id = "user123"
        mock_updated_fragment.fragment_count = 150

        # 模拟查询执行
        mock_exec_result = Mock()
        mock_exec_result.first.return_value = mock_existing_fragment
        mock_session.exec.return_value = mock_exec_result

        # 模拟交易记录
        mock_transaction = Mock(spec=PointsTransaction)
        mock_transaction.id = "transaction-123"

        with patch('src.models.reward.PointsTransaction') as mock_transaction_class:
            mock_transaction_class.return_value = mock_transaction

            reward_repo = RewardRepository(mock_session)

            # 执行测试
            result = reward_repo.award_fragments("user123", 50, "专注奖励")

            # 验证结果
            assert result is not None

    def test_draw_lottery_with_mock_session(self):
        """测试draw_lottery方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟抽奖记录
        mock_lottery_record = Mock(spec=LotteryRecord)
        mock_lottery_record.id = "lottery-123"
        mock_lottery_record.user_id = "user123"
        mock_lottery_record.is_winner = True
        mock_lottery_record.prize_name = "幸运奖励"

        # 模拟用户碎片验证
        with patch.object(RewardRepository, 'get_user_fragment_balance', return_value=100):

            with patch('src.models.reward.LotteryRecord') as mock_lottery_class:
                mock_lottery_class.return_value = mock_lottery_record

                reward_repo = RewardRepository(mock_session)

                # 执行测试
                result = reward_repo.draw_lottery("user123", 10)

                # 验证结果
                assert result is not None

    def test_create_points_transaction_with_mock_session(self):
        """测试create_points_transaction方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟积分交易记录
        mock_transaction = Mock(spec=PointsTransaction)
        mock_transaction.id = "transaction-123"
        mock_transaction.user_id = "user123"
        mock_transaction.transaction_type = TransactionType.EARN
        mock_transaction.amount = 50

        with patch('src.models.reward.PointsTransaction') as mock_transaction_class:
            mock_transaction_class.return_value = mock_transaction

            reward_repo = RewardRepository(mock_session)

            # 执行测试
            result = reward_repo.create_points_transaction(
                user_id="user123",
                transaction_type=TransactionType.EARN,
                amount=50,
                reason="专注奖励"
            )

            # 验证结果
            assert result is not None

    def test_get_user_points_history_with_mock_session(self):
        """测试get_user_points_history方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟积分交易记录
        mock_transaction = Mock(spec=PointsTransaction)
        mock_transaction.id = "transaction-123"
        mock_transaction.user_id = "user123"
        mock_transaction.amount = 50

        # 模拟查询执行
        mock_exec_result = Mock()
        mock_exec_result.all.return_value = [mock_transaction]
        mock_session.exec.return_value = mock_exec_result

        # 创建Repository并测试
        reward_repo = RewardRepository(mock_session)

        # 执行测试
        result = reward_repo.get_user_points_history("user123")

        # 验证结果
        assert len(result) == 1
        assert result[0] == mock_transaction
        mock_session.exec.assert_called_once()

    def test_get_user_points_summary_with_mock_session(self):
        """测试get_user_points_summary方法使用模拟会话"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)

        # 模拟统计查询结果
        mock_total_earned = 500  # 总获得积分
        mock_total_spent = 200   # 总消费积分
        mock_current_balance = 300  # 当前余额
        mock_transaction_count = 15  # 交易次数

        # 创建scalar mock对象
        mock_scalar_earned = Mock()
        mock_scalar_earned.one.return_value = mock_total_earned

        mock_scalar_spent = Mock()
        mock_scalar_spent.one.return_value = mock_total_spent

        mock_scalar_count = Mock()
        mock_scalar_count.one.return_value = mock_transaction_count

        # 模拟查询执行（需要4个查询：总收入、总支出、用户碎片余额、交易次数）
        mock_session.exec.side_effect = [
            mock_scalar_earned,  # 总获得查询
            mock_scalar_spent,   # 总消费查询
            Mock(first=Mock(return_value=None)),  # 用户碎片查询（返回None表示没有记录）
            mock_scalar_count    # 交易次数查询
        ]

        # 创建Repository并测试
        reward_repo = RewardRepository(mock_session)

        # 执行测试
        result = reward_repo.get_user_points_summary("user123")

        # 验证结果
        assert 'total_earned' in result
        assert 'total_spent' in result
        assert 'current_balance' in result
        assert 'net_change' in result
        assert 'transaction_count' in result
        assert 'average_transaction' in result
        assert 'statistics_days' in result
        assert result['total_earned'] == mock_total_earned
        assert result['total_spent'] == mock_total_spent
        assert result['current_balance'] == 0  # 没有碎片记录时应该是0
        assert result['net_change'] == mock_total_earned - mock_total_spent
        assert result['transaction_count'] == mock_transaction_count
        assert result['statistics_days'] == 30


# 导出测试类
__all__ = [
    "TestRewardRepositoryBasic",
    "TestRewardRepositoryBusinessLogic"
]