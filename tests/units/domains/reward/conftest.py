"""
Reward领域测试配置

提供reward领域测试所需的特定fixtures和工具函数。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.domains.reward.models import Reward, RewardRecipe, RewardTransaction
from src.domains.reward.service import RewardService
from src.domains.reward.repository import RewardRepository


@pytest.fixture(scope="function")
def reward_service(reward_db_session):
    """提供RewardService实例的fixture"""
    repository = RewardRepository(reward_db_session)
    service = RewardService(reward_db_session, repository)
    return service


@pytest.fixture(scope="function")
def reward_repository(reward_db_session):
    """提供RewardRepository实例的fixture"""
    return RewardRepository(reward_db_session)


@pytest.fixture(scope="function")
def sample_reward(reward_repository):
    """创建测试用的奖品"""
    return reward_repository.create({
        "name": "测试奖品",
        "description": "这是一个测试奖品",
        "cost_type": "points",
        "cost_value": 100,
        "image_url": "https://example.com/reward.jpg"
    })


@pytest.fixture(scope="function")
def sample_recipe(reward_repository, sample_user_id):
    """创建测试用的配方"""
    return reward_repository.create_recipe({
        "user_id": sample_user_id,
        "name": "测试配方",
        "description": "这是一个测试配方",
        "count": 3
    })


@pytest.fixture(scope="function")
def sample_user_id():
    """提供测试用户ID"""
    return str(uuid4())


@pytest.fixture(scope="function")
def multiple_rewards(reward_repository):
    """创建多个测试奖品"""
    rewards = []

    # 创建不同类型的奖品
    rewards.append(reward_repository.create({
        "name": "积分奖品1",
        "description": "使用积分兑换的奖品",
        "cost_type": "points",
        "cost_value": 50
    }))

    rewards.append(reward_repository.create({
        "name": "积分奖品2",
        "description": "更贵的积分奖品",
        "cost_type": "points",
        "cost_value": 200
    }))

    rewards.append(reward_repository.create({
        "name": "配方奖品",
        "description": "需要配方兑换的奖品",
        "cost_type": "recipe",
        "cost_value": 2,
        "required_recipe_id": uuid4()
    }))

    return rewards


@pytest.fixture(scope="function")
def reward_with_transactions(reward_service, reward_repository, sample_user_id):
    """创建带有交易记录的奖品"""
    # 创建奖品
    reward = reward_repository.create({
        "name": "交易测试奖品",
        "cost_type": "points",
        "cost_value": 100
    })

    # 创建交易记录
    transaction_group = str(uuid4())
    reward_service.create_transaction({
        "user_id": sample_user_id,
        "reward_id": reward.id,
        "transaction_type": "purchase",
        "source_type": "points",
        "source_value": 100,
        "transaction_group": transaction_group
    })

    return reward, transaction_group


@pytest.fixture(scope="function")
def sample_reward_data():
    """提供测试用的奖品数据"""
    return {
        "name": "测试奖品",
        "description": "这是一个测试奖品",
        "cost_type": "points",
        "cost_value": 100,
        "image_url": "https://example.com/test.jpg"
    }


@pytest.fixture(scope="function")
def sample_recipe_data():
    """提供测试用的配方数据"""
    return {
        "name": "测试配方",
        "description": "这是一个测试配方",
        "count": 5
    }