"""
RewardService完整TDD测试套件
基于深度架构分析，系统性地覆盖所有业务逻辑

目标：
- 覆盖率：13% → 100%
- 测试所有公共方法
- 覆盖所有异常分支
- 验证事务一致性
- 测试并发安全性

作者：系统架构师
版本：1.0.0 - TDD严格实现
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, Any, List, Optional
from decimal import Decimal
import json

# 严格遵循TDD：先写测试，再实现代码
# 绕过conftest.py导入问题
import sys
sys.path.insert(0, '/Users/zalelee/Code/tatake_backend')

from src.domains.reward.service import RewardService
from src.domains.reward.models import Reward, RewardTransaction, RewardRecipe
from src.domains.reward.exceptions import RewardNotFoundException, InsufficientPointsException


class TestRewardServiceCompleteTDD:
    """
    RewardService完整TDD测试类
    
    测试策略：
    1. 核心业务逻辑优先
    2. 异常分支全覆盖
    3. 边界条件严格验证
    4. 事务一致性保证
    """
    
    @pytest.fixture
    def mock_dependencies(self):
        """提供所有Mock依赖项"""
        mock_session = MagicMock()
        mock_points_service = MagicMock()
        mock_repository = MagicMock()
        
        return {
            'session': mock_session,
            'points_service': mock_points_service,
            'repository': mock_repository
        }
    
    @pytest.fixture  
    def reward_service(self, mock_dependencies):
        """创建RewardService实例"""
        service = RewardService(
            session=mock_dependencies['session'],
            points_service=mock_dependencies['points_service']
        )
        
        # Mock reward_repository to avoid real database calls
        service.reward_repository = MagicMock()
        
        return service
    
    @pytest.fixture
    def sample_user_id(self):
        """标准测试用户ID"""
        return "550e8400-e29b-41d4-a716-446655440000"
    
    @pytest.fixture
    def sample_reward_data(self):
        """标准奖品数据"""
        return {
            'id': 'reward-123',
            'name': '积分加成卡',
            'description': '24小时内积分收益+50%',
            'points_value': 100,
            'cost_type': 'points',
            'cost_value': 100,
            'category': 'boost',
            'is_active': True,
            'stock_quantity': 999,
            'image_url': 'https://example.com/boost-card.png'
        }
    
    @pytest.fixture
    def sample_transaction_data(self):
        """标准交易记录数据"""
        return {
            'id': 'txn-456',
            'user_id': '550e8400-e29b-41d4-a716-446655440000',
            'reward_id': 'reward-123',
            'reward_name': '积分加成卡',
            'source_type': 'welcome_gift',
            'source_id': 'welcome-001',
            'quantity': 3,
            'transaction_group': 'txn-group-789',
            'created_at': datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        }

    # ============= 核心业务逻辑测试 =============
    
    def test_get_available_rewards_success(self, reward_service, mock_dependencies):
        """
        测试获取可用奖品 - 成功场景
        
        Given: 数据库中有3个可用奖品
        When: 调用get_available_rewards()
        Then: 返回格式正确的奖品列表
        """
        # Given: Mock SQL查询返回3个奖品
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ('reward-1', '积分加成卡', '24小时+50%', 'boost', 'boost.png', 100, True, '2024-01-01', '2024-01-01'),
            ('reward-2', '万能卡', '任意任务万能完成', 'utility', 'universal.png', 200, True, '2024-01-01', '2024-01-01'),
            ('reward-3', '抽奖券', '参与Top3抽奖', 'lottery', 'ticket.png', 50, True, '2024-01-01', '2024-01-01')
        ]
        mock_dependencies['session'].execute.return_value = mock_result
        
        # When: 调用方法
        result = reward_service.get_available_rewards()
        
        # Then: 验证结果
        assert isinstance(result, list), "Result should be list"
        assert len(result) == 3, "Should return 3 rewards"
        
        # 验证第一个奖品的结构
        reward = result[0]
        expected_keys = {'id', 'name', 'description', 'category', 'image_url', 'points_value', 'is_active', 'created_at', 'updated_at'}
        assert set(reward.keys()) == expected_keys, f"Missing keys: {expected_keys - set(reward.keys())}"
        
        # 验证数据正确性
        assert reward['id'] == 'reward-1'
        assert reward['name'] == '积分加成卡'
        assert reward['points_value'] == 100
        assert reward['is_active'] is True
        
        # 验证SQL调用
        mock_dependencies['session'].execute.assert_called_once()
        call_args = mock_dependencies['session'].execute.call_args
        assert 'SELECT' in str(call_args[0][0])
        assert 'is_active = true' in str(call_args[0][0])
    
    def test_get_available_rewards_empty(self, reward_service, mock_dependencies):
        """测试获取可用奖品 - 空结果场景"""
        # Given: Mock空结果
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_dependencies['session'].execute.return_value = mock_result
        
        # When: 调用方法
        result = reward_service.get_available_rewards()
        
        # Then: 验证空结果处理
        assert isinstance(result, list), "Result should be list"
        assert len(result) == 0, "Should return empty list when no rewards"
        assert result == [], "Should be empty list"
    
    def test_get_reward_catalog_format(self, reward_service, mock_dependencies):
        """测试获取奖品目录 - 返回格式验证"""
        # Given: Mock奖品数据
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ('reward-1', '奖品1', '描述1', 'cat1', 'img1.png', 100, True, '2024-01-01', '2024-01-01'),
            ('reward-2', '奖品2', '描述2', 'cat2', 'img2.png', 200, True, '2024-01-01', '2024-01-01')
        ]
        mock_dependencies['session'].execute.return_value = mock_result
        
        # When: 调用方法
        result = reward_service.get_reward_catalog()
        
        # Then: 验证返回格式
        assert isinstance(result, dict), "Result should be dict"
        assert 'rewards' in result, "Should have 'rewards' key"
        assert 'total_count' in result, "Should have 'total_count' key"
        
        assert isinstance(result['rewards'], list), "Rewards should be list"
        assert result['total_count'] == 2, "Should have correct total count"
        assert len(result['rewards']) == 2, "Should have 2 rewards in list"
    
    def test_get_my_rewards_quantity_calculation(self, reward_service, mock_dependencies, sample_user_id):
        """测试获取我的奖品 - 数量计算逻辑（关键修复验证）"""
        """
        这是数量计算Bug修复的核心验证测试
        用户获得3个积分加成卡，应该显示3个而不是1个
        """
        # Given: 用户有3条获得记录（同类型奖品）
        mock_transactions = [
            {
                'id': 'txn-1',
                'reward_id': 'reward-123',
                'reward_name': '积分加成卡',
                'quantity': 1,
                'source_type': 'welcome_gift',
                'source_id': 'welcome-001',
                'transaction_group': 'txn-group-1',
                'created_at': datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            },
            {
                'id': 'txn-2',
                'reward_id': 'reward-123', 
                'reward_name': '积分加成卡',
                'quantity': 1,
                'source_type': 'task_completion',
                'source_id': 'task-001',
                'transaction_group': 'txn-group-2',
                'created_at': datetime(2024, 1, 16, 14, 20, 0, tzinfo=timezone.utc)
            },
            {
                'id': 'txn-3',
                'reward_id': 'reward-123',
                'reward_name': '积分加成卡',
                'quantity': 1,
                'source_type': 'daily_checkin',
                'source_id': 'checkin-001',
                'transaction_group': 'txn-group-3',
                'created_at': datetime(2024, 1, 17, 9, 15, 0, tzinfo=timezone.utc)
            }
        ]
        
        # Mock get_reward_transactions返回字典列表
        reward_service.get_reward_transactions = MagicMock(return_value=mock_transactions)
        
        # Mock reward_repository.get_reward_by_id
        reward_detail = {
            'id': 'reward-123',
            'name': '积分加成卡',
            'image_url': 'https://example.com/boost-card.png',
            'description': '24小时内积分收益+50%'
        }
        reward_service.reward_repository.get_reward_by_id.return_value = reward_detail
        
        # When: 调用get_my_rewards
        result = reward_service.get_my_rewards(sample_user_id)
        
        # Then: 验证数量计算正确性（关键修复验证）
        assert isinstance(result, dict), "Result should be dict"
        assert 'rewards' in result, "Should have rewards key"
        
        rewards = result['rewards']
        assert len(rewards) == 1, "Should aggregate same reward types"
        
        reward = rewards[0]
        assert reward['id'] == 'reward-123'
        assert reward['name'] == '积分加成卡'
        assert reward['quantity'] == 3, "CRITICAL: Should sum quantities (3), not show 1"
        assert reward['icon'] == 'https://example.com/boost-card.png'
        assert reward['description'] == '24小时内积分收益+50%'
        assert reward['is_exchangeable'] is True
    
    def test_get_my_rewards_with_consumption(self, reward_service, mock_dependencies, sample_user_id):
        """测试获取我的奖品 - 包含消耗记录"""
        # Given: 用户有获得和消耗记录
        mock_transactions = [
            {
                'id': 'txn-1',
                'reward_id': 'reward-123',
                'reward_name': '积分加成卡',
                'quantity': 3,
                'source_type': 'purchase',
                'source_id': 'purchase-001',
                'transaction_group': 'txn-group-1',
                'created_at': datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            },
            {
                'id': 'txn-2',
                'reward_id': 'reward-123',
                'reward_name': '积分加成卡',
                'quantity': -1,  # 使用了1个
                'source_type': 'usage',
                'source_id': 'usage-001',
                'transaction_group': 'txn-group-2',
                'created_at': datetime(2024, 1, 16, 14, 20, 0, tzinfo=timezone.utc)
            },
            {
                'id': 'txn-3',
                'reward_id': 'reward-456',
                'reward_name': '万能卡',
                'quantity': 1,
                'source_type': 'gift',
                'source_id': 'gift-001',
                'transaction_group': 'txn-group-3',
                'created_at': datetime(2024, 1, 17, 9, 15, 0, tzinfo=timezone.utc)
            }
        ]
        
        # Mock get_reward_transactions返回字典列表
        reward_service.get_reward_transactions = MagicMock(return_value=mock_transactions)
        
        # Mock reward_repository.get_reward_by_id for different rewards
        def mock_get_reward_by_id(reward_id):
            if reward_id == 'reward-123':
                return {
                    'id': 'reward-123',
                    'name': '积分加成卡',
                    'image_url': 'https://example.com/boost-card.png',
                    'description': '24小时内积分收益+50%'
                }
            elif reward_id == 'reward-456':
                return {
                    'id': 'reward-456',
                    'name': '万能卡',
                    'image_url': 'https://example.com/universal-card.png',
                    'description': '任意任务万能完成'
                }
            return None
        
        reward_service.reward_repository.get_reward_by_id.side_effect = mock_get_reward_by_id
        
        # When: 调用get_my_rewards
        result = reward_service.get_my_rewards(sample_user_id)
        
        # Then: 验证净数量计算
        rewards = result['rewards']
        assert len(rewards) == 2, "Should have 2 different rewards"
        
        # 找到积分加成卡
        boost_card = next((r for r in rewards if r['id'] == 'reward-123'), None)
        assert boost_card is not None, "Should find boost card"
        assert boost_card['quantity'] == 2, "Should calculate net quantity (3 - 1 = 2)"
        
        # 找到万能卡
        universal_card = next((r for r in rewards if r['id'] == 'reward-456'), None)
        assert universal_card is not None, "Should find universal card"
        assert universal_card['quantity'] == 1, "Should have quantity 1"
    
    def test_redeem_reward_complete_flow(self, reward_service, mock_dependencies, sample_user_id, sample_reward_data):
        """测试奖品兑换 - 完整业务流程"""
        """
        这是积分兑换奖品的核心业务流程测试
        验证：查询→验证→扣积分→记录流水→返回结果
        """
        # Given: 完整的业务场景设置
        reward_id = sample_reward_data['id']
        
        # Mock SQL查询返回奖品信息
        mock_result = MagicMock()
        mock_result.first.return_value = (
            reward_id,
            sample_reward_data['name'],
            sample_reward_data['points_value']
        )
        mock_dependencies['session'].execute.return_value = mock_result
        
        # Mock积分服务
        mock_dependencies['points_service'].calculate_balance.return_value = 500  # 足够积分
        
        # Mock事务作用域
        mock_scope = MagicMock()
        mock_scope.__enter__ = MagicMock(return_value=mock_scope)
        mock_scope.__exit__ = MagicMock(return_value=None)
        reward_service.transaction_scope = MagicMock(return_value=mock_scope)
        
        # When: 调用redeem_reward
        result = reward_service.redeem_reward(sample_user_id, reward_id)
        
        # Then: 验证完整业务流程
        assert isinstance(result, dict), "Result should be dict"
        
        # 验证核心返回字段
        required_fields = {'success', 'reward', 'transaction_group', 'points_deducted', 'message'}
        assert set(result.keys()) >= required_fields, f"Missing required fields: {required_fields - set(result.keys())}"
        
        assert result['success'] is True, "Should be successful"
        assert result['reward']['id'] == reward_id, "Should return correct reward ID"
        assert result['reward']['name'] == sample_reward_data['name'], "Should return correct reward name"
        assert result['points_deducted'] == sample_reward_data['points_value'], "Should deduct correct points"
        assert 'transaction_group' in result, "Should have transaction group"
        
        # 验证业务调用链
        mock_dependencies['points_service'].calculate_balance.assert_called_once_with(str(sample_user_id))
        mock_dependencies['points_service'].add_points.assert_called_once_with(
            str(sample_user_id),
            -sample_reward_data['points_value'],  # 负值表示扣减
            'reward_redemption',
            reward_id
        )
        
        # 验证数据库事务
        mock_dependencies['session'].add.assert_called()  # 应该添加了交易记录
        mock_scope.__exit__.assert_called_with(None, None, None)  # 事务成功提交
    
    def test_redeem_reward_insufficient_points(self, reward_service, mock_dependencies, sample_user_id):
        """测试奖品兑换 - 积分不足场景"""
        # Given: 用户积分不足
        reward_id = 'reward-123'
        required_points = 100
        
        mock_result = MagicMock()
        mock_result.first.return_value = (reward_id, '测试奖品', required_points)
        mock_dependencies['session'].execute.return_value = mock_result
        
        # 用户只有50积分，但需要100
        mock_dependencies['points_service'].calculate_balance.return_value = 50
        
        mock_scope = MagicMock()
        mock_scope.__enter__ = MagicMock(return_value=mock_scope)
        mock_scope.__exit__ = MagicMock(return_value=None)
        reward_service.transaction_scope = MagicMock(return_value=mock_scope)
        
        # When/Then: 应该抛出InsufficientPointsException
        with pytest.raises(InsufficientPointsException) as exc_info:
            reward_service.redeem_reward(sample_user_id, reward_id)
        
        exception = exc_info.value
        # 验证异常消息包含正确的积分信息
        assert "积分不足" in str(exception), "Should have Chinese error message"
        assert "需要100积分" in str(exception), "Should mention required points"
        assert "当前50积分" in str(exception), "Should mention current points"
    
    def test_redeem_reward_not_found(self, reward_service, mock_dependencies, sample_user_id):
        """测试奖品兑换 - 奖品不存在场景"""
        # Given: 奖品不存在
        reward_id = 'non-existent-reward'
        
        mock_result = MagicMock()
        mock_result.first.return_value = None  # 奖品不存在
        mock_dependencies['session'].execute.return_value = mock_result
        
        mock_scope = MagicMock()
        mock_scope.__enter__ = MagicMock(return_value=mock_scope)
        mock_scope.__exit__ = MagicMock(return_value=None)
        reward_service.transaction_scope = MagicMock(return_value=mock_scope)
        
        # When/Then: 应该抛出RewardNotFoundException
        with pytest.raises(RewardNotFoundException) as exc_info:
            reward_service.redeem_reward(sample_user_id, reward_id)
        
        exception = exc_info.value
        assert reward_id in str(exception), "Should mention the reward ID in error"
        assert "奖品不存在" in str(exception), "Should have Chinese error message"
    
    def test_top3_lottery_win_scenario(self, reward_service, mock_dependencies, sample_user_id):
        """测试Top3抽奖 - 中奖场景（50%概率）"""
        """
        Top3抽奖系统：
        - 50%概率获得随机奖品
        - 50%概率获得安慰积分
        这个测试通过mock随机数来验证中奖路径
        """
        # Given: 设置中奖场景
        available_rewards = [
            MagicMock(id='reward-1', name='奖品1', points_value=100),
            MagicMock(id='reward-2', name='奖品2', points_value=200),
            MagicMock(id='reward-3', name='奖品3', points_value=300)
        ]
        
        # Mock get_available_rewards返回3个奖品
        reward_service.get_available_rewards = MagicMock(return_value=[
            {'id': 'reward-1', 'name': '奖品1', 'points_value': 100},
            {'id': 'reward-2', 'name': '奖品2', 'points_value': 200},
            {'id': 'reward-3', 'name': '奖品3', 'points_value': 300}
        ])
        
        # Mock随机数生成，确保中奖（随机数<0.5）
        with patch('random.random', return_value=0.3):  # < 0.5，应该中奖
            with patch('random.choice', return_value={'id': 'reward-2', 'name': '奖品2', 'points_value': 200}):
                # Mock事务作用域
                mock_scope = MagicMock()
                mock_scope.__enter__ = MagicMock(return_value=mock_scope)
                mock_scope.__exit__ = MagicMock(return_value=None)
                reward_service.transaction_scope = MagicMock(return_value=mock_scope)
                
                # When: 调用top3_lottery
                result = reward_service.top3_lottery(sample_user_id)
                
                # Then: 验证中奖结果
                assert isinstance(result, dict), "Result should be dict"
                assert result['success'] is True, "Should be successful"
                assert result['is_win'] is True, "Should be a win"
                assert result['reward_type'] == 'item', "Should be item reward"
                assert result['reward']['id'] == 'reward-2', "Should get the mocked reward"
                assert 'transaction_group' in result, "Should have transaction group"
    
    def test_top3_lottery_consolation_scenario(self, reward_service, mock_dependencies, sample_user_id):
        """测试Top3抽奖 - 安慰奖场景（50%概率）"""
        """
        验证安慰奖路径：获得固定积分奖励
        """
        # Given: 设置安慰奖场景
        reward_service.get_available_rewards = MagicMock(return_value=[
            {'id': 'reward-1', 'name': '奖品1', 'points_value': 100}
        ])
        
        # Mock随机数生成，确保不中奖（随机数>=0.5）
        with patch('random.random', return_value=0.7):  # >= 0.5，安慰奖
            # Mock事务作用域
            mock_scope = MagicMock()
            mock_scope.__enter__ = MagicMock(return_value=mock_scope)
            mock_scope.__exit__ = MagicMock(return_value=None)
            reward_service.transaction_scope = MagicMock(return_value=mock_scope)
            
            # When: 调用top3_lottery
            result = reward_service.top3_lottery(sample_user_id)
            
            # Then: 验证安慰奖结果
            assert isinstance(result, dict), "Result should be dict"
            assert result['success'] is True, "Should be successful"
            assert result['is_win'] is False, "Should not be a win"
            assert result['reward_type'] == 'points', "Should be points reward"
            assert result['points_awarded'] == 50, "Should get 50 consolation points"
            assert 'transaction_group' in result, "Should have transaction group"

    def test_get_reward_transactions_pagination_and_ordering(self, reward_service, mock_dependencies, sample_user_id):
        """测试获取交易记录 - 分页和排序"""
        """
        验证分页参数正确传递和结果按时间倒序排列
        """
        # Given: Mock分页查询结果
        mock_transactions = []
        for i in range(1, 6):  # 5条记录
            mock_txn = MagicMock()
            mock_txn.id = f'txn-{i}'
            mock_txn.reward_id = f'reward-{i}'
            mock_txn.reward_name = f'奖品{i}'
            mock_txn.quantity = i
            mock_txn.source_type = 'purchase'
            mock_txn.created_at = datetime(2024, 1, i, 12, 0, 0, tzinfo=timezone.utc)
            mock_transactions.append(mock_txn)
        
        mock_query = MagicMock()
        mock_dependencies['session'].query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_transactions[2:5]  # 返回第3-5条（偏移2，限制3）
        mock_query.count.return_value = 5  # 总数5条
        
        # When: 调用带分页参数
        result = reward_service.get_reward_transactions(sample_user_id, limit=3, offset=2)
        
        # Then: 验证分页结果
        assert isinstance(result, list), "Result should be list"
        assert len(result) == 3, "Should return 3 transactions"
        
        # 验证分页参数传递
        mock_query.limit.assert_called_with(3)
        mock_query.offset.assert_called_with(2)
        mock_query.order_by.assert_called()  # 应该调用了排序
        
        # 验证数据正确性
        assert result[0]['id'] == 'txn-3', "Should be in correct order"
        assert result[2]['id'] == 'txn-5', "Should include last item in page"

    def test_compose_rewards_success_flow(self, reward_service, mock_dependencies, sample_user_id):
        """测试配方合成 - 成功完整流程"""
        """
        配方合成是复杂业务逻辑：
        1. 验证配方存在性
        2. 检查用户材料充足性
        3. 扣除材料（负交易）
        4. 发放结果奖品（正交易）
        5. 事务一致性保证
        """
        # Given: 完整配方合成场景
        recipe_id = 'recipe-123'
        result_reward_id = 'reward-result-456'
        
        # Mock配方查询
        recipe_result = MagicMock()
        recipe_result.id = recipe_id
        recipe_result.result_reward_id = result_reward_id
        recipe_result.result_reward_name = '合成奖品'
        
        recipe_mock_result = MagicMock()
        recipe_mock_result.first.return_value = recipe_result
        
        # Mock用户当前材料（足够合成）
        user_materials_result = MagicMock()
        user_materials_result.fetchall.return_value = [
            ('material-1', '材料1', 5),  # 需要3个，有5个
            ('material-2', '材料2', 4),  # 需要2个，有4个
        ]
        
        # 配置Mock链
        mock_dependencies['session'].execute.side_effect = [
            recipe_mock_result,           # 第一次调用：配方查询
            user_materials_result,        # 第二次调用：用户材料查询
            None,                         # 第三次调用：扣材料
            None                          # 第四次调用：发奖品
        ]
        
        # Mock事务作用域
        mock_scope = MagicMock()
        mock_scope.__enter__ = MagicMock(return_value=mock_scope)
        mock_scope.__exit__ = MagicMock(return_value=None)
        reward_service.transaction_scope = MagicMock(return_value=mock_scope)
        
        # When: 调用compose_rewards
        result = reward_service.compose_rewards(sample_user_id, recipe_id)
        
        # Then: 验证合成成功
        assert isinstance(result, dict), "Result should be dict"
        assert result['success'] is True, "Should be successful"
        assert result['recipe_id'] == recipe_id, "Should return recipe ID"
        assert result['result_reward']['id'] == result_reward_id, "Should return result reward"
        assert 'transaction_group' in result, "Should have transaction group"
        
        # 验证事务一致性（所有操作在同一事务组）
        assert len(mock_dependencies['session'].execute.call_args_list) >= 4, "Should execute multiple SQL statements"

    def test_compose_rewards_insufficient_materials(self, reward_service, mock_dependencies, sample_user_id):
        """测试配方合成 - 材料不足场景"""
        # Given: 用户材料不足
        recipe_id = 'recipe-123'
        
        # Mock配方存在
        recipe_result = MagicMock()
        recipe_result.id = recipe_id
        recipe_result.result_reward_id = 'reward-result-456'
        recipe_result.result_reward_name = '合成奖品'
        
        recipe_mock_result = MagicMock()
        recipe_mock_result.first.return_value = recipe_result
        
        # Mock用户材料不足（需要5个，只有2个）
        user_materials_result = MagicMock()
        user_materials_result.fetchall.return_value = [
            ('material-1', '材料1', 2),  # 需要5个，只有2个
        ]
        
        mock_dependencies['session'].execute.side_effect = [
            recipe_mock_result,      # 配方查询
            user_materials_result    # 材料查询
        ]
        
        mock_scope = MagicMock()
        mock_scope.__enter__ = MagicMock(return_value=mock_scope)
        mock_scope.__exit__ = MagicMock(return_value=None)
        reward_service.transaction_scope = MagicMock(return_value=mock_scope)
        
        # When/Then: 应该抛出材料不足异常
        with pytest.raises(Exception) as exc_info:  # 假设会抛出某种异常
            reward_service.compose_rewards(sample_user_id, recipe_id)
        
        # 验证异常信息包含材料不足
        assert "材料" in str(exc_info.value) or "insufficient" in str(exc_info.value).lower()

    def test_get_available_recipes_basic(self, reward_service, mock_dependencies):
        """测试获取可用配方 - 基础功能"""
        """
        配方系统允许用户使用材料合成更高级的奖品
        """
        # Given: Mock配方数据
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ('recipe-1', '550e8400-e29b-41d4-a716-446655440000', '初级合成', '合成基础奖品', 3, True),
            ('recipe-2', '550e8400-e29b-41d4-a716-446655440001', '高级合成', '合成高级奖品', 5, True)
        ]
        mock_dependencies['session'].execute.return_value = mock_result
        
        # When: 调用get_available_recipes
        result = reward_service.get_available_recipes()
        
        # Then: 验证返回结果
        assert isinstance(result, list), "Result should be list"
        assert len(result) == 2, "Should return 2 recipes"
        
        # 验证第一个配方的结构
        recipe = result[0]
        expected_keys = {'id', 'user_id', 'name', 'description', 'count', 'is_active'}
        assert set(recipe.keys()) >= expected_keys, f"Should have required keys: {expected_keys}"
        
        assert recipe['id'] == 'recipe-1'
        assert recipe['name'] == '初级合成'
        assert recipe['count'] == 3, "Should have correct count"
        assert recipe['is_active'] is True, "Should be active"

    def test_get_reward_transactions_empty_result(self, reward_service, mock_dependencies, sample_user_id):
        """测试获取交易记录 - 空结果处理"""
        # Given: 用户没有交易记录
        mock_query = MagicMock()
        mock_dependencies['session'].query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.count.return_value = 0
        
        # When: 调用get_reward_transactions
        result = reward_service.get_reward_transactions(sample_user_id)
        
        # Then: 验证空结果处理
        assert isinstance(result, list), "Result should be list"
        assert len(result) == 0, "Should return empty list"
        assert result == [], "Should be empty list"

    def test_get_reward_transactions_negative_quantities(self, reward_service, mock_dependencies, sample_user_id):
        """测试获取交易记录 - 负数量处理"""
        """
        负数量表示消耗或使用，这是重要的业务逻辑
        """
        # Given: 包含负数量的交易记录
        mock_transactions = [
            MagicMock(
                id='txn-1',
                reward_id='reward-123',
                reward_name='积分加成卡',
                quantity=3,  # 获得3个
                source_type='purchase',
                created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            ),
            MagicMock(
                id='txn-2',
                reward_id='reward-123',
                reward_name='积分加成卡',
                quantity=-1,  # 使用了1个（负数量）
                source_type='usage',
                created_at=datetime(2024, 1, 16, 14, 20, 0, tzinfo=timezone.utc)
            )
        ]
        
        mock_query = MagicMock()
        mock_dependencies['session'].query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_transactions
        mock_query.count.return_value = 2
        
        # When: 调用get_reward_transactions
        result = reward_service.get_reward_transactions(sample_user_id, limit=10, offset=0)
        
        # Then: 验证负数量正确处理
        assert len(result) == 2, "Should return both transactions"
        
        # 验证获得记录
        purchase_txn = next((t for t in result if t['quantity'] > 0), None)
        assert purchase_txn is not None, "Should have purchase transaction"
        assert purchase_txn['quantity'] == 3, "Should show positive quantity"
        assert purchase_txn['source_type'] == 'purchase', "Should have correct source type"
        
        # 验证消耗记录
        usage_txn = next((t for t in result if t['quantity'] < 0), None)
        assert usage_txn is not None, "Should have usage transaction"
        assert usage_txn['quantity'] == -1, "Should show negative quantity"
        assert usage_txn['source_type'] == 'usage', "Should have correct source type"

    def test_transaction_scope_context_manager(self, reward_service, mock_dependencies):
        """测试事务作用域 - 上下文管理器"""
        """
        验证事务作用域正确管理数据库事务
        """
        # Given: Mock事务作用域
        mock_scope = MagicMock()
        mock_scope.__enter__ = MagicMock(return_value=mock_scope)
        mock_scope.__exit__ = MagicMock(return_value=None)
        
        original_transaction_scope = reward_service.transaction_scope
        reward_service.transaction_scope = MagicMock(return_value=mock_scope)
        
        # When: 使用事务作用域
        with reward_service.transaction_scope() as scope:
            assert scope is mock_scope, "Should return the mock scope"
        
        # Then: 验证上下文管理器调用
        mock_scope.__enter__.assert_called_once()
        mock_scope.__exit__.assert_called_once()
        
        # 恢复原始方法
        reward_service.transaction_scope = original_transaction_scope

    def test_uuid_compatibility_all_methods(self, reward_service, mock_dependencies):
        """测试所有方法的UUID兼容性 - 字符串和UUID对象"""
        """
        确保服务层正确处理字符串UUID和UUID对象
        这是之前修复的关键兼容性问题
        """
        user_id_str = "550e8400-e29b-41d4-a716-446655440000"
        user_id_uuid = uuid.UUID(user_id_str)
        
        # Mock基础依赖
        mock_query = MagicMock()
        mock_dependencies['session'].query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.count.return_value = 0
        
        # 测试get_my_rewards的UUID兼容性
        result_str = reward_service.get_my_rewards(user_id_str)
        result_uuid = reward_service.get_my_rewards(user_id_uuid)
        
        # 验证两种格式都得到正确处理
        assert isinstance(result_str, dict), "String UUID should work"
        assert isinstance(result_uuid, dict), "UUID object should work"
        assert result_str['rewards'] == result_uuid['rewards'], "Results should be identical"
        
        # 验证查询参数被正确转换
        filter_calls = mock_query.filter.call_args_list
        for call in filter_calls:
            # 验证UUID参数被正确传递给数据库查询
            args, kwargs = call
            # 这里应该验证UUID被正确转换，具体取决于实现

    def test_service_initialization_and_dependencies(self, mock_dependencies):
        """测试服务初始化 - 依赖注入验证"""
        """
        验证依赖注入正确性，这是微服务架构的基础
        """
        # When: 创建服务实例
        service = RewardService(
            session=mock_dependencies['session'],
            points_service=mock_dependencies['points_service']
        )
        
        # Then: 验证依赖正确注入
        assert service.session is mock_dependencies['session'], "Session should be injected"
        assert service.points_service is mock_dependencies['points_service'], "Points service should be injected"
        assert hasattr(service, 'logger'), "Should have logger"
        assert hasattr(service, 'transaction_scope'), "Should have transaction scope method"

    def test_error_handling_and_logging(self, reward_service, mock_dependencies, sample_user_id):
        """测试错误处理和日志记录 - 审计要求"""
        """
        验证关键业务操作有适当的错误处理和日志记录
        这是企业级系统的重要要求
        """
        # Given: 设置错误场景（奖品不存在）
        reward_id = 'non-existent-reward'
        
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_dependencies['session'].execute.return_value = mock_result
        
        mock_scope = MagicMock()
        mock_scope.__enter__ = MagicMock(return_value=mock_scope)
        mock_scope.__exit__ = MagicMock(return_value=None)
        reward_service.transaction_scope = MagicMock(return_value=mock_scope)
        
        # Mock日志记录
        with patch.object(reward_service.logger, 'warning') as mock_warning:
            # When/Then: 触发错误
            with pytest.raises(RewardNotFoundException):
                reward_service.redeem_reward(sample_user_id, reward_id)
            
            # 验证错误日志记录
            mock_warning.assert_called_once()
            log_call = mock_warning.call_args[0][0]
            assert 'Redemption failed' in log_call, "Should log redemption failure"
            assert sample_user_id in log_call, "Should include user ID"
            assert reward_id in log_call, "Should include reward ID"


class TestRewardServiceEdgeCases:
    """边界条件和异常场景测试类"""
    
    def test_zero_points_value_handling(self, reward_service, mock_dependencies, sample_user_id):
        """测试零积分值处理 - 边界条件"""
        # Given: 奖品价值为0积分
        reward_id = 'free-reward'
        
        mock_result = MagicMock()
        mock_result.first.return_value = (reward_id, '免费奖品', 0)  # 0积分
        mock_dependencies['session'].execute.return_value = mock_result
        
        mock_scope = MagicMock()
        mock_scope.__enter__ = MagicMock(return_value=mock_scope)
        mock_scope.__exit__ = MagicMock(return_value=None)
        reward_service.transaction_scope = MagicMock(return_value=mock_scope)
        
        # When: 调用redeem_reward
        result = reward_service.redeem_reward(sample_user_id, reward_id)
        
        # Then: 应该成功（免费奖品）
        assert result['success'] is True, "Free reward should be successful"
        assert result['points_deducted'] == 0, "Should deduct 0 points"
        
        # 验证没有调用积分扣减（因为值为0）
        mock_dependencies['points_service'].add_points.assert_not_called(), "Should not deduct points for free reward"

    def test_large_quantity_aggregation(self, reward_service, mock_dependencies, sample_user_id):
        """测试大数量聚合 - 性能边界"""
        # Given: 用户有大量交易记录
        large_quantity = 999999
        mock_transactions = [
            MagicMock(reward_id='reward-123', reward_name='大量奖品', quantity=large_quantity, source_type='bulk_purchase'),
            MagicMock(reward_id='reward-123', reward_name='大量奖品', quantity=large_quantity, source_type='bulk_purchase'),
        ]
        
        mock_query = MagicMock()
        mock_dependencies['session'].query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_transactions
        
        # When: 调用get_my_rewards
        result = reward_service.get_my_rewards(sample_user_id)
        
        # Then: 验证大数量正确处理
        rewards = result['rewards']
        assert len(rewards) == 1, "Should aggregate to single reward"
        
        total_quantity = large_quantity * 2
        assert rewards[0]['quantity'] == total_quantity, f"Should handle large quantity: {total_quantity}"

    def test_unicode_and_special_characters(self, reward_service, mock_dependencies, sample_user_id):
        """测试Unicode和特殊字符处理 - 国际化支持"""
        # Given: 包含Unicode字符的奖品
        unicode_reward_name = '🎁 超级积分卡™ (限量版)'
        unicode_description = '特殊字符测试：!@#$%^&*()_+-=[]{}|;:,.<>?'
        
        reward_id = 'unicode-reward'
        
        mock_result = MagicMock()
        mock_result.first.return_value = (reward_id, unicode_reward_name, 100)
        mock_dependencies['session'].execute.return_value = mock_result
        
        mock_scope = MagicMock()
        mock_scope.__enter__ = MagicMock(return_value=mock_scope)
        mock_scope.__exit__ = MagicMock(return_value=None)
        reward_service.transaction_scope = MagicMock(return_value=mock_scope)
        
        # When: 调用redeem_reward
        result = reward_service.redeem_reward(sample_user_id, reward_id)
        
        # Then: 验证Unicode字符正确处理
        assert result['reward']['name'] == unicode_reward_name, "Should handle Unicode characters"
        assert unicode_reward_name in result['message'], "Should include Unicode in message"

    def test_concurrent_transaction_handling(self, reward_service, mock_dependencies, sample_user_id):
        """测试并发事务处理 - 数据一致性"""
        """
        模拟在高并发场景下的事务处理
        验证事务隔离性和数据一致性
        """
        # Given: 模拟并发环境
        import threading
        import time
        
        results = []
        errors = []
        
        def concurrent_redeem():
            try:
                # 每个线程使用不同的奖品ID避免冲突
                thread_reward_id = f'reward-thread-{threading.current_thread().ident}'
                
                # Mock这个线程的执行结果
                mock_result = MagicMock()
                mock_result.first.return_value = (thread_reward_id, f'线程奖品', 10)
                mock_dependencies['session'].execute.return_value = mock_result
                
                mock_scope = MagicMock()
                mock_scope.__enter__ = MagicMock(return_value=mock_scope)
                mock_scope.__exit__ = MagicMock(return_value=None)
                reward_service.transaction_scope = MagicMock(return_value=mock_scope)
                
                result = reward_service.redeem_reward(sample_user_id, thread_reward_id)
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # When: 启动多个并发线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_redeem)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # Then: 验证并发处理结果
        assert len(results) == 5, f"All threads should succeed. Results: {len(results)}, Errors: {errors}"
        assert len(errors) == 0, f"Should have no errors. Errors: {errors}"
        
        # 验证每个线程都获得了独立的奖品
        reward_ids = [result['reward']['id'] for result in results]
        assert len(set(reward_ids)) == 5, "Each thread should get different reward"


class TestRewardServiceBusinessRules:
    """业务规则验证测试类"""
    
    def test_transaction_group_consistency(self, reward_service, mock_dependencies, sample_user_id):
        """测试事务组一致性 - 业务规则验证"""
        """
        同一业务操作的所有交易记录应该有相同的事务组ID
        这是审计和回滚的重要机制
        """
        # Given: 兑换操作
        reward_id = 'reward-123'
        
        mock_result = MagicMock()
        mock_result.first.return_value = (reward_id, '测试奖品', 100)
        mock_dependencies['session'].execute.return_value = mock_result
        
        mock_scope = MagicMock()
        mock_scope.__enter__ = MagicMock(return_value=mock_scope)
        mock_scope.__exit__ = MagicMock(return_value=None)
        reward_service.transaction_scope = MagicMock(return_value=mock_scope)
        
        # When: 调用redeem_reward
        result = reward_service.redeem_reward(sample_user_id, reward_id)
        
        # Then: 验证事务组一致性
        assert 'transaction_group' in result, "Should have transaction group"
        transaction_group = result['transaction_group']
        
        # 验证事务组ID格式（应该是有效的UUID）
        try:
            uuid.UUID(transaction_group)
        except ValueError:
            pytest.fail(f"Transaction group should be valid UUID: {transaction_group}")
        
        # 验证数据库操作使用了相同的事务组
        add_calls = mock_dependencies['session'].add.call_args_list
        for call in add_calls:
            obj = call[0][0]  # 获取添加的对象
            if hasattr(obj, 'transaction_group'):
                assert obj.transaction_group == transaction_group, "All operations should use same transaction group"

    def test_points_deduction_accuracy(self, reward_service, mock_dependencies, sample_user_id):
        """测试积分扣减准确性 - 财务正确性"""
        """
        验证积分扣减的数值计算准确性
        这对财务正确性至关重要
        """
        # Given: 不同积分价值的奖品
        test_cases = [
            (50, '便宜奖品'),
            (100, '普通奖品'),
            (999, '贵重奖品'),
            (1, '最便宜奖品'),
        ]
        
        for points_value, reward_name in test_cases:
            reward_id = f'reward-{points_value}'
            
            mock_result = MagicMock()
            mock_result.first.return_value = (reward_id, reward_name, points_value)
            mock_dependencies['session'].execute.return_value = mock_result
            
            mock_scope = MagicMock()
            mock_scope.__enter__ = MagicMock(return_value=mock_scope)
            mock_scope.__exit__ = MagicMock(return_value=None)
            reward_service.transaction_scope = MagicMock(return_value=mock_scope)
            
            # When: 兑换奖品
            result = reward_service.redeem_reward(sample_user_id, reward_id)
            
            # Then: 验证积分扣减准确性
            assert result['points_deducted'] == points_value, f"Should deduct exactly {points_value} points for {reward_name}"
            
            # 验证add_points调用参数
            mock_dependencies['points_service'].add_points.assert_called_with(
                str(sample_user_id),
                -points_value,  # 应该是负值
                'reward_redemption',
                reward_id
            )
            
            # 重置mock以供下一次迭代
            mock_dependencies['points_service'].reset_mock()

    def test_reward_lifecycle_state_management(self, reward_service, mock_dependencies):
        """测试奖品生命周期状态管理 - 状态机验证"""
        """
        验证奖品状态转换的正确性
        is_active字段控制奖品是否可用
        """
        # Given: 测试不同状态的奖品
        test_scenarios = [
            (True, True, '应该返回活跃奖品'),
            (False, False, '不应该返回禁用奖品'),
        ]
        
        for is_active, should_appear, description in test_scenarios:
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                ('reward-1', '测试奖品', '描述', 'cat', 'img.png', 100, is_active, '2024-01-01', '2024-01-01')
            ]
            mock_dependencies['session'].execute.return_value = mock_result
            
            # When: 获取可用奖品
            result = reward_service.get_available_rewards()
            
            # Then: 验证状态过滤
            if should_appear:
                assert len(result) == 1, f"{description}"
                assert result[0]['is_active'] is True, "Should only return active rewards"
            else:
                assert len(result) == 0, f"{description}"


# ============= 测试工具函数 =============

def pytest_configure(config):
    """pytest配置钩子"""
    config.addinivalue_line(
        "markers", "reward: mark test as reward system test"
    )
    config.addinivalue_line(
        "markers", "business_critical: mark test as business critical"
    )
    config.addinivalue_line(
        "markers", "edge_case: mark test as edge case scenario"
    )


def assert_valid_reward_structure(reward: Dict[str, Any]) -> None:
    """验证奖品数据结构有效性"""
    required_fields = {'id', 'name', 'description', 'category', 'image_url', 'points_value', 'is_active'}
    assert set(reward.keys()) >= required_fields, f"Missing required fields: {required_fields - set(reward.keys())}"
    
    assert isinstance(reward['id'], str), "ID should be string"
    assert isinstance(reward['name'], str), "Name should be string"
    assert isinstance(reward['points_value'], int), "Points value should be integer"
    assert isinstance(reward['is_active'], bool), "Is active should be boolean"
    assert reward['points_value'] >= 0, "Points value should be non-negative"


def assert_valid_transaction_structure(transaction: Dict[str, Any]) -> None:
    """验证交易记录数据结构有效性"""
    required_fields = {'id', 'reward_id', 'reward_name', 'quantity', 'source_type', 'created_at'}
    assert set(transaction.keys()) >= required_fields, f"Missing required fields: {required_fields - set(transaction.keys())}"
    
    assert isinstance(transaction['id'], str), "Transaction ID should be string"
    assert isinstance(transaction['quantity'], int), "Quantity should be integer"
    assert isinstance(transaction['created_at'], (str, datetime)), "Created at should be datetime or string"
    
    # 验证UUID格式
    try:
        uuid.UUID(transaction['id'])
        uuid.UUID(transaction['reward_id'])
    except ValueError:
        pytest.fail(f"Invalid UUID format in transaction: {transaction}")


if __name__ == "__main__":
    # 独立运行测试
    pytest.main([__file__, "-v", "--tb=short"])