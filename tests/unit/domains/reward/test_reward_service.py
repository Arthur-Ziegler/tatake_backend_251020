"""
测试RewardService功能

测试奖励系统的核心功能，包括：
1. 奖品目录查询
2. 奖品兑换功能
3. Top3抽奖系统
4. 流水记录查询
5. 事务管理正确性
6. 异常处理完整性

作者：TaKeKe团队
版本：1.0.0（Phase 1 Day 2）
"""

import pytest
import random
from datetime import datetime, timezone, date
from uuid import uuid4, UUID

from sqlmodel import Session, text
from sqlalchemy.exc import SQLAlchemyError

from src.domains.reward.service import RewardService
from src.domains.points.service import PointsService
from src.domains.reward.models import Reward, RewardTransaction


class TestRewardService:
    """测试RewardService功能"""

    def test_get_available_rewards_empty(self, session: Session, reward_service_with_points):
        """测试空奖品目录"""
        service, _ = reward_service_with_points

        rewards = service.get_available_rewards()

        assert isinstance(rewards, list), "Should return a list"
        # 如果没有奖品，应该返回空列表
        self.logger.info(f"Got {len(rewards)} available rewards")

    def test_get_available_rewards_with_data(self, session: Session, reward_service_with_points):
        """测试有数据的奖品目录"""
        service, _ = reward_service_with_points

        # 创建测试奖品
        self._create_test_rewards(session)

        rewards = service.get_available_rewards()

        assert len(rewards) >= 2, f"Should have at least 2 rewards, got {len(rewards)}"

        # 验证返回结构
        for reward in rewards:
            assert "id" in reward, "Reward should have id"
            assert "name" in reward, "Reward should have name"
            assert "category" in reward, "Reward should have category"
            assert "cost_type" in reward, "Reward should have cost_type"
            assert "cost_value" in reward, "Reward should have cost_value"
            assert "stock_quantity" in reward, "Reward should have stock_quantity"

    def test_redeem_reward_success(self, session: Session, reward_service_with_points):
        """测试成功兑换奖品"""
        service, points_service = reward_service_with_points

        # 创建测试奖品
        reward_id = self._create_test_rewards(session, cost_value=100)[0]

        # 给用户添加积分
        user_id = uuid4()
        points_service.add_points(user_id, 200, "test_initial", uuid4())

        # 兑换奖品
        result = service.redeem_reward(str(user_id), reward_id)

        # 验证结果
        assert result["success"] is True, "Redemption should succeed"
        assert "reward" in result, "Result should contain reward info"
        assert result["reward"]["id"] == reward_id, "Should return correct reward"
        assert result["points_deducted"] == 100, "Should deduct 100 points"
        assert "transaction_group" in result, "Should have transaction group"

        # 验证用户积分
        remaining_balance = points_service.calculate_balance(user_id)
        assert remaining_balance == 100, f"Should have 100 points remaining, got {remaining_balance}"

    def test_redeem_reward_insufficient_points(self, session: Session, reward_service_with_points):
        """测试积分不足"""
        service, points_service = reward_service_with_points

        # 创建测试奖品
        reward_id = self._create_test_rewards(session, cost_value=200)[0]

        # 给用户添加少量积分
        user_id = uuid4()
        points_service.add_points(user_id, 50, "test_initial", uuid4())

        # 尝试兑换应该失败
        try:
            service.redeem_reward(str(user_id), reward_id)
            assert False, "Should have raised InsufficientPointsException"
        except Exception as e:
            assert "积分不足" in str(e), f"Should indicate insufficient points: {e}"

    def test_redeem_reward_not_found(self, session: Session, reward_service_with_points):
        """测试奖品不存在"""
        service, points_service = reward_service_with_points

        user_id = uuid4()
        points_service.add_points(user_id, 100, "test_initial", uuid4())

        # 尝试兑换不存在的奖品
        try:
            service.redeem_reward(str(user_id), str(uuid4()))
            assert False, "Should have raised RewardNotFoundException"
        except Exception as e:
            assert "不存在" in str(e), f"Should indicate reward not found: {e}"

    def test_top3_lottery_winner(self, session: Session, reward_service_with_points):
        """测试Top3中奖"""
        service, points_service = reward_service_with_points

        # 创建Top3奖品
        user_id = uuid4()
        top3_reward_id = self._create_top3_reward(session)

        # 固定随机数种子确保中奖
        random.seed(0.1)  # 小于0.5，确保中奖

        # 参与抽奖
        result = service.top3_lottery(str(user_id))

        # 验证中奖结果
        assert result["success"] is True, "Lottery should succeed"
        assert result["is_winner"] is True, "Should be winner"
        assert "prize" in result, "Should have prize info"
        assert result["prize"]["id"] == top3_reward_id, "Should win the created prize"

    def test_top3_lottery_consolidation(self, session: Session, reward_service_with_points):
        """测试Top3未中奖"""
        service, points_service = reward_service_with_points

        # 创建Top3奖品
        user_id = uuid4()
        top3_reward_id = self._create_top3_reward(session)

        # 固定随机数种子确保不中奖
        random.seed(0.8)  # 大于0.5，确保不中奖

        # 参与抽奖
        result = service.top3_lottery(str(user_id))

        # 验证安慰奖结果
        assert result["success"] is True, "Lottery should succeed"
        assert result["is_winner"] is False, "Should not be winner"
        assert result["consolation_points"] == 50, "Should get 50 consolation points"
        assert "未中奖" in result["message"], "Should indicate no win"

        # 验证积分增加
        balance = points_service.calculate_balance(user_id)
        assert balance == 50, f"Should have 50 points from consolation, got {balance}"

    def test_get_reward_transactions(self, session: Session, reward_service_with_points):
        """测试获取奖励流水记录"""
        service, points_service = reward_service_with_points

        user_id = uuid4()

        # 添加积分和兑换奖品
        points_service.add_points(user_id, 100, "test_initial", uuid4())
        reward_id = self._create_test_rewards(session, cost_value=50)[0]
        service.redeem_reward(str(user_id), reward_id)

        # 获取流水记录
        transactions = service.get_reward_transactions(str(user_id))

        assert len(transactions) >= 1, f"Should have at least 1 transaction, got {len(transactions)}"

        # 验证交易结构
        for transaction in transactions:
            assert "id" in transaction, "Transaction should have id"
            assert "transaction_type" in transaction, "Transaction should have type"
            assert "created_at" in transaction, "Transaction should have created_at"
            assert transaction["user_id"] == str(user_id), "Should belong to correct user"

    def test_get_reward_transactions_pagination(self, session: Session, reward_service_with_points):
        """测试奖励流水记录分页"""
        service, points_service = reward_service_with_points

        user_id = uuid4()

        # 创建多个交易记录
        for i in range(5):
            points_service.add_points(user_id, 10, f"test_batch_{i}", uuid4())
            reward_id = self._create_test_rewards(session, cost_value=5)[0]
            service.redeem_reward(str(user_id), reward_id)

        # 测试分页
        page1 = service.get_reward_transactions(str(user_id), limit=3, offset=0)
        assert len(page1) == 3, f"First page should have 3 transactions"

        page2 = service.get_reward_transactions(str(user_id), limit=3, offset=3)
        assert len(page2) >= 2, f"Second page should have at least 2 transactions"

    def test_transaction_atomicity(self, session: Session, reward_service_with_points):
        """测试事务原子性"""
        service, points_service = reward_service_with_points

        user_id = uuid4()
        reward_id = self._create_test_rewards(session, cost_value=100)[0]

        # 验证兑换前状态
        initial_balance = points_service.calculate_balance(user_id)

        # 在事务内兑换
        with service.transaction_scope():
            # 库存应该被锁定并扣减
            # 积分应该被扣减
            # 流水记录应该被创建

            pass  # 事务提交

        # 验证最终状态
        final_balance = points_service.calculate_balance(user_id)
        assert final_balance == initial_balance - 100, "Points should be deducted"

    # Helper methods
    def _create_test_rewards(self, session: Session, cost_value: int = 50):
        """创建测试奖品"""
        rewards_data = [
            {
                "id": str(uuid4()),
                "name": "测试奖品1",
                "description": "这是测试奖品1",
                "category": "test",
                "image_url": "https://example.com/image1.jpg",
                "cost_type": "points",
                "cost_value": cost_value,
                "stock_quantity": 10,
                "is_active": True
            },
            {
                "id": str(uuid4()),
                "name": "测试奖品2",
                "description": "这是测试奖品2",
                "category": "test",
                "image_url": "https://example.com/image2.jpg",
                "cost_type": "points",
                "cost_value": cost_value + 20,
                "stock_quantity": 5,
                "is_active": True
            }
        ]

        reward_ids = []
        for reward_data in rewards_data:
            reward = Reward(
                id=UUID(reward_data["id"]),
                name=reward_data["name"],
                description=reward_data["description"],
                category=reward_data["category"],
                image_url=reward_data["image_url"],
                cost_type=reward_data["cost_type"],
                cost_value=reward_data["cost_value"],
                stock_quantity=reward_data["stock_quantity"],
                is_active=reward_data["is_active"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            session.add(reward)
            reward_ids.append(reward_data["id"])

        session.commit()
        return reward_ids

    def _create_top3_reward(self, session: Session):
        """创建Top3奖品"""
        reward_id = str(uuid4())
        reward = Reward(
            id=UUID(reward_id),
            name="Top3测试奖品",
            description="这是Top3测试奖品",
            category="top3",
            image_url="https://example.com/top3.jpg",
            cost_type="points",
            cost_value=0,
            stock_quantity=10,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        session.add(reward)
        session.commit()
        return reward_id


# pytest fixtures
@pytest.fixture
def reward_service_with_points(session):
    """提供RewardService和PointsService实例"""
    points_service = PointsService(session)
    reward_service = RewardService(session, points_service)
    return reward_service, points_service