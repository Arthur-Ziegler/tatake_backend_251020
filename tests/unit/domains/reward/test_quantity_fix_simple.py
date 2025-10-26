"""
奖励数量计算Bug修复简单验证测试

专门验证数量计算bug修复，使用Mock隔离依赖。

作者：TaKeKe团队
版本：1.0.0 - 简单验证
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, MagicMock

from src.domains.reward.service import RewardService
from src.domains.reward.models import Reward, RewardTransaction
from src.domains.points.service import PointsService


@pytest.mark.unit
@pytest.mark.reward
class TestQuantityCalculationFix:
    """数量计算修复验证"""
    
    def test_quantity_calculation_bug_fix_verification(self):
        """验证数量计算bug修复 - 最关键测试"""
        # Given: 创建Mock服务
        mock_session = Mock()
        mock_points_service = Mock(spec=PointsService)
        reward_service = RewardService(mock_session, mock_points_service)
        
        user_id = str(uuid4())
        reward_id = str(uuid4())
        
        # Mock get_reward_transactions 方法
        mock_transactions = [
            {
                "id": str(uuid4()),
                "reward_id": reward_id,
                "reward_name": "积分加成卡",
                "source_type": "welcome_gift",
                "source_id": str(uuid4()),
                "quantity": 3,  # 关键：用户获得了3个
                "transaction_group": str(uuid4()),
                "created_at": datetime.now(timezone.utc)
            }
        ]
        
        with patch.object(reward_service, 'get_reward_transactions', return_value=mock_transactions):
            # Mock 奖品查询
            mock_reward_detail = {
                "id": reward_id,
                "name": "积分加成卡",
                "image_url": "https://example.com/img.jpg",
                "description": "+50%积分"
            }
            
            with patch.object(reward_service.reward_repository, 'get_reward_by_id', return_value=mock_reward_detail):
                # When: 查询用户奖品
                result = reward_service.get_my_rewards(user_id)
                
                # Then: 验证数量计算正确（修复前会显示1，修复后应显示3）
                assert len(result["rewards"]) == 1
                assert result["rewards"][0]["quantity"] == 3  # 关键断言：必须等于实际数量
                assert result["total_types"] == 1
    
    def test_quantity_calculation_with_consumption(self):
        """测试包含消耗的数量计算"""
        # Given: 创建Mock服务
        mock_session = Mock()
        mock_points_service = Mock(spec=PointsService)
        reward_service = RewardService(mock_session, mock_points_service)
        
        user_id = str(uuid4())
        reward_id = str(uuid4())
        
        # Mock交易记录：获得10个，消耗4个
        mock_transactions = [
            {
                "id": str(uuid4()),
                "reward_id": reward_id,
                "reward_name": "专注道具",
                "source_type": "lottery_reward",
                "source_id": str(uuid4()),
                "quantity": 10,  # 获得10个
                "transaction_group": str(uuid4()),
                "created_at": datetime.now(timezone.utc)
            },
            {
                "id": str(uuid4()),
                "reward_id": reward_id,
                "reward_name": "专注道具",
                "source_type": "recipe_consume",
                "source_id": str(uuid4()),
                "quantity": -4,  # 消耗4个
                "transaction_group": str(uuid4()),
                "created_at": datetime.now(timezone.utc)
            }
        ]
        
        with patch.object(reward_service, 'get_reward_transactions', return_value=mock_transactions):
            # Mock 奖品查询
            mock_reward_detail = {
                "id": reward_id,
                "name": "专注道具",
                "image_url": "https://example.com/img.jpg",
                "description": "立即完成"
            }
            
            with patch.object(reward_service.reward_repository, 'get_reward_by_id', return_value=mock_reward_detail):
                # When: 查询用户奖品
                result = reward_service.get_my_rewards(user_id)
                
                # Then: 验证净数量计算正确（10 + (-4) = 6）
                assert len(result["rewards"]) == 1
                assert result["rewards"][0]["quantity"] == 6  # 关键断言：净数量计算
                assert result["total_types"] == 1
    
    def test_quantity_calculation_zero_quantity(self):
        """测试零数量情况"""
        # Given: 创建Mock服务
        mock_session = Mock()
        mock_points_service = Mock(spec=PointsService)
        reward_service = RewardService(mock_session, mock_points_service)
        
        user_id = str(uuid4())
        reward_id = str(uuid4())
        
        # Mock交易记录：获得5个，消耗5个，净0个
        mock_transactions = [
            {
                "id": str(uuid4()),
                "reward_id": reward_id,
                "reward_name": "测试奖品",
                "source_type": "welcome_gift",
                "source_id": str(uuid4()),
                "quantity": 5,
                "transaction_group": str(uuid4()),
                "created_at": datetime.now(timezone.utc)
            },
            {
                "id": str(uuid4()),
                "reward_id": reward_id,
                "reward_name": "测试奖品",
                "source_type": "recipe_consume",
                "source_id": str(uuid4()),
                "quantity": -5,
                "transaction_group": str(uuid4()),
                "created_at": datetime.now(timezone.utc)
            }
        ]
        
        with patch.object(reward_service, 'get_reward_transactions', return_value=mock_transactions):
            # Mock 奖品查询
            mock_reward_detail = {
                "id": reward_id,
                "name": "测试奖品",
                "image_url": "https://example.com/img.jpg",
                "description": "测试描述"
            }
            
            with patch.object(reward_service.reward_repository, 'get_reward_by_id', return_value=mock_reward_detail):
                # When: 查询用户奖品
                result = reward_service.get_my_rewards(user_id)
                
                # Then: 验证零数量被正确处理（重要业务逻辑：零数量也要显示）
                assert len(result["rewards"]) == 1
                assert result["rewards"][0]["quantity"] == 0  # 零数量应该被保留显示
                assert result["total_types"] == 1
    
    def test_quantity_calculation_negative_quantity(self):
        """测试负数量情况"""
        # Given: 创建Mock服务
        mock_session = Mock()
        mock_points_service = Mock(spec=PointsService)
        reward_service = RewardService(mock_session, mock_points_service)
        
        user_id = str(uuid4())
        reward_id = str(uuid4())
        
        # Mock交易记录：消耗3个（负数量）
        mock_transactions = [
            {
                "id": str(uuid4()),
                "reward_id": reward_id,
                "reward_name": "测试奖品",
                "source_type": "recipe_consume",
                "source_id": str(uuid4()),
                "quantity": -3,  # 负数量
                "transaction_group": str(uuid4()),
                "created_at": datetime.now(timezone.utc)
            }
        ]
        
        with patch.object(reward_service, 'get_reward_transactions', return_value=mock_transactions):
            # Mock 奖品查询
            mock_reward_detail = {
                "id": reward_id,
                "name": "测试奖品",
                "image_url": "https://example.com/img.jpg",
                "description": "测试描述"
            }
            
            with patch.object(reward_service.reward_repository, 'get_reward_by_id', return_value=mock_reward_detail):
                # When: 查询用户奖品
                result = reward_service.get_my_rewards(user_id)
                
                # Then: 验证负数量被正确处理
                assert len(result["rewards"]) == 1
                assert result["rewards"][0]["quantity"] == -3  # 负数量应该被保留
                assert result["total_types"] == 1
    
    def test_get_reward_transactions_basic(self):
        """测试基础流水查询"""
        # Given: 创建Mock服务
        mock_session = Mock()
        mock_points_service = Mock(spec=PointsService)
        reward_service = RewardService(mock_session, mock_points_service)
        
        user_id = str(uuid4())
        
        # Mock交易记录返回
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (str(uuid4()), str(uuid4()), "积分加成卡", "welcome_gift", str(uuid4()), 3, str(uuid4()), datetime.now(timezone.utc)),
            (str(uuid4()), str(uuid4()), "专注道具", "lottery_reward", str(uuid4()), 10, str(uuid4()), datetime.now(timezone.utc))
        ]
        mock_session.execute.return_value = mock_result
        
        # When: 查询流水记录
        result = reward_service.get_reward_transactions(user_id)
        
        # Then: 验证结果
        assert len(result) == 2
        assert all(isinstance(t, dict) for t in result)
        
        # 验证每条记录的字段
        for transaction in result:
            assert "id" in transaction
            assert "reward_id" in transaction
            assert "reward_name" in transaction
            assert "source_type" in transaction
            assert "quantity" in transaction
            assert "transaction_group" in transaction
            assert "created_at" in transaction
    
    def test_get_reward_transactions_empty_result(self):
        """测试空流水记录"""
        # Given: 创建Mock服务
        mock_session = Mock()
        mock_points_service = Mock(spec=PointsService)
        reward_service = RewardService(mock_session, mock_points_service)
        
        user_id = str(uuid4())
        
        # Mock空结果
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        # When: 查询流水记录
        result = reward_service.get_reward_transactions(user_id)
        
        # Then: 验证返回空列表
        assert result == []
        assert isinstance(result, list)
    
    def test_get_reward_transactions_pagination(self):
        """测试分页功能 - 简化验证"""
        # Given: 创建Mock服务
        mock_session = Mock()
        mock_points_service = Mock(spec=PointsService)
        reward_service = RewardService(mock_session, mock_points_service)
        
        user_id = str(uuid4())
        
        # Mock交易记录返回 - 模拟分页行为
        def mock_execute_side_effect(query, params):
            mock_result = Mock()
            limit = params.get("limit", 100)
            offset = params.get("offset", 0)
            # 根据limit和offset返回相应的数据
            data = [
                (str(uuid4()), str(uuid4()), f"奖品{i}", "test", str(uuid4()), 1, str(uuid4()), datetime.now(timezone.utc))
                for i in range(20)
            ]
            mock_result.fetchall.return_value = data[offset:offset+limit]
            return mock_result
        
        mock_session.execute.side_effect = mock_execute_side_effect
        
        # When: 查询第一页（10条记录）
        page1 = reward_service.get_reward_transactions(user_id, limit=10, offset=0)
        
        # Then: 验证分页结果
        assert len(page1) == 10
        
        # When: 查询第二页（10条记录，偏移10）
        page2 = reward_service.get_reward_transactions(user_id, limit=10, offset=10)
        
        # Then: 验证第二页结果
        assert len(page2) == 10
    
    def test_get_reward_transactions_ordering(self):
        """测试排序（按创建时间倒序）"""
        # Given: 创建Mock服务
        mock_session = Mock()
        mock_points_service = Mock(spec=PointsService)
        reward_service = RewardService(mock_session, mock_points_service)
        
        user_id = str(uuid4())
        base_time = datetime.now(timezone.utc)
        
        # Mock交易记录返回 - 创建时间降序数据（模拟数据库查询结果）
        mock_result = Mock()
        # 注意：数据库查询已经按created_at DESC排序，所以返回的数据应该是降序的
        mock_result.fetchall.return_value = [
            (str(uuid4()), str(uuid4()), f"奖品{i}", "test", str(uuid4()), 1, str(uuid4()), base_time.replace(second=4-i))
            for i in range(5)
        ]
        mock_session.execute.return_value = mock_result
        
        # When: 查询流水记录
        result = reward_service.get_reward_transactions(user_id)
        
        # Then: 验证按时间倒序排列（最新的在前）
        assert len(result) == 5
        timestamps = [r["created_at"] for r in result]
        # 验证确实是降序排列
        assert timestamps == sorted(timestamps, reverse=True)
        # 验证第一个是最新的
        assert timestamps[0] >= timestamps[-1]
    
    def test_get_reward_transactions_negative_quantity_in_list(self):
        """测试负数量记录"""
        # Given: 创建Mock服务
        mock_session = Mock()
        mock_points_service = Mock(spec=PointsService)
        reward_service = RewardService(mock_session, mock_points_service)
        
        user_id = str(uuid4())
        
        # Mock交易记录返回
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (str(uuid4()), str(uuid4()), "测试奖品", "recipe_consume", str(uuid4()), -5, str(uuid4()), datetime.now(timezone.utc))
        ]
        mock_session.execute.return_value = mock_result
        
        # When: 查询流水记录
        result = reward_service.get_reward_transactions(user_id)
        
        # Then: 验证负数量被正确处理
        assert len(result) == 1
        assert result[0]["quantity"] == -5
        assert result[0]["source_type"] == "recipe_consume"
    
    def test_get_reward_transactions_all_source_types(self):
        """测试所有支持的source_type"""
        # Given: 创建Mock服务
        mock_session = Mock()
        mock_points_service = Mock(spec=PointsService)
        reward_service = RewardService(mock_session, mock_points_service)
        
        user_id = str(uuid4())
        
        # Mock交易记录返回
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (str(uuid4()), str(uuid4()), "奖品1", "welcome_gift", str(uuid4()), 1, str(uuid4()), datetime.now(timezone.utc)),
            (str(uuid4()), str(uuid4()), "奖品2", "lottery_reward", str(uuid4()), 1, str(uuid4()), datetime.now(timezone.utc)),
            (str(uuid4()), str(uuid4()), "奖品3", "recipe_consume", str(uuid4()), -1, str(uuid4()), datetime.now(timezone.utc)),
            (str(uuid4()), str(uuid4()), "奖品4", "recipe_produce", str(uuid4()), 1, str(uuid4()), datetime.now(timezone.utc)),
            (str(uuid4()), str(uuid4()), "奖品5", "redemption", str(uuid4()), 1, str(uuid4()), datetime.now(timezone.utc))
        ]
        mock_session.execute.return_value = mock_result
        
        # When: 查询流水记录
        result = reward_service.get_reward_transactions(user_id)
        
        # Then: 验证所有source_type都被正确处理
        assert len(result) == 5
        source_types = {t["source_type"] for t in result}
        expected_types = {"welcome_gift", "lottery_reward", "recipe_consume", "recipe_produce", "redemption"}
        assert source_types == expected_types
    
    def test_get_reward_transactions_database_error(self):
        """测试数据库错误处理"""
        # Given: 创建Mock服务
        mock_session = Mock()
        mock_points_service = Mock(spec=PointsService)
        reward_service = RewardService(mock_session, mock_points_service)
        
        user_id = str(uuid4())
        
        # Mock数据库抛出异常
        from sqlalchemy.exc import SQLAlchemyError
        mock_session.execute.side_effect = SQLAlchemyError("Database error")
        
        # When/Then: 验证异常被正确传播
        with pytest.raises(SQLAlchemyError):
            reward_service.get_reward_transactions(user_id)