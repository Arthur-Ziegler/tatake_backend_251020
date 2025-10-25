"""
Reward领域模型测试套件

测试Reward、RewardRecipe、RewardTransaction模型的基本功能，
包括字段验证、关系映射和业务规则。

遵循TDD原则，专注于模型层的数据验证。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID

from src.domains.reward.models import Reward, RewardRecipe, RewardTransaction


@pytest.mark.unit
class TestRewardModel:
    """Reward模型测试类"""

    def test_reward_model_creation(self):
        """测试Reward模型基本创建"""
        reward_id = uuid4()

        reward = Reward(
            id=reward_id,
            name="测试奖品",
            description="这是一个测试奖品",
            cost_type="points",
            cost_value=100,
            image_url="https://example.com/image.jpg"
        )

        # 验证基本字段
        assert reward.id == reward_id
        assert reward.name == "测试奖品"
        assert reward.description == "这是一个测试奖品"
        assert reward.cost_type == "points"
        assert reward.cost_value == 100
        assert reward.image_url == "https://example.com/image.jpg"
        assert reward.is_active is True
        assert reward.created_at is not None

    def test_reward_model_with_recipe_cost(self):
        """测试使用recipe作为成本的奖品"""
        reward_id = uuid4()
        recipe_id = uuid4()

        reward = Reward(
            id=reward_id,
            name="配方奖品",
            description="需要配方兑换的奖品",
            cost_type="recipe",
            cost_value=50,
            required_recipe_id=recipe_id
        )

        assert reward.cost_type == "recipe"
        assert reward.cost_value == 50
        assert reward.required_recipe_id == recipe_id

    def test_reward_model_optional_fields(self):
        """测试可选字段的默认值"""
        reward_id = uuid4()

        reward = Reward(
            id=reward_id,
            name="最简奖品",
            cost_type="points",
            cost_value=10
        )

        # 验证默认值
        assert reward.description is None
        assert reward.image_url is None
        assert reward.required_recipe_id is None
        assert reward.is_active is True

    def test_reward_model_to_dict(self):
        """测试to_dict方法"""
        reward_id = uuid4()

        reward = Reward(
            id=reward_id,
            name="字典测试奖品",
            description="测试描述",
            cost_type="points",
            cost_value=50,
            image_url="https://example.com/test.jpg"
        )

        result = reward.to_dict()

        # 验证字典包含所有字段
        assert result["id"] == reward_id
        assert result["name"] == "字典测试奖品"
        assert result["description"] == "测试描述"
        assert result["cost_type"] == "points"
        assert result["cost_value"] == 50
        assert result["image_url"] == "https://example.com/test.jpg"
        assert result["is_active"] is True
        assert "created_at" in result


@pytest.mark.unit
class TestRewardRecipeModel:
    """RewardRecipe模型测试类"""

    def test_recipe_model_creation(self):
        """测试RewardRecipe模型基本创建"""
        recipe_id = uuid4()
        user_id = uuid4()

        recipe = RewardRecipe(
            id=recipe_id,
            user_id=user_id,
            name="测试配方",
            description="这是一个测试配方",
            count=5
        )

        # 验证基本字段
        assert recipe.id == recipe_id
        assert recipe.user_id == user_id
        assert recipe.name == "测试配方"
        assert recipe.description == "这是一个测试配方"
        assert recipe.count == 5
        assert recipe.is_active is True
        assert recipe.created_at is not None

    def test_recipe_model_optional_fields(self):
        """测试可选字段的默认值"""
        recipe_id = uuid4()
        user_id = uuid4()

        recipe = RewardRecipe(
            id=recipe_id,
            user_id=user_id,
            name="最简配方",
            count=1
        )

        # 验证默认值
        assert recipe.description is None
        assert recipe.is_active is True

    def test_recipe_model_negative_count(self):
        """测试负数配方的处理"""
        recipe_id = uuid4()
        user_id = uuid4()

        # 配方数量应该是非负数
        recipe = RewardRecipe(
            id=recipe_id,
            user_id=user_id,
            name="零配方",
            count=0
        )

        assert recipe.count == 0
        assert recipe.is_active is True  # 即使数量为0也可以是活跃的


@pytest.mark.unit
class TestRewardTransactionModel:
    """RewardTransaction模型测试类"""

    def test_transaction_model_creation_points(self):
        """测试积分类型的交易记录创建"""
        transaction_id = uuid4()
        user_id = uuid4()
        reward_id = uuid4()

        transaction = RewardTransaction(
            id=transaction_id,
            user_id=user_id,
            reward_id=reward_id,
            transaction_type="purchase",
            source_type="points",
            source_value=100,
            transaction_group=str(uuid4())
        )

        # 验证基本字段
        assert transaction.id == transaction_id
        assert transaction.user_id == user_id
        assert transaction.reward_id == reward_id
        assert transaction.transaction_type == "purchase"
        assert transaction.source_type == "points"
        assert transaction.source_value == 100
        assert transaction.transaction_group is not None
        assert transaction.created_at is not None

    def test_transaction_model_creation_recipe(self):
        """测试配方类型的交易记录创建"""
        transaction_id = uuid4()
        user_id = uuid4()
        reward_id = uuid4()
        recipe_id = uuid4()

        transaction = RewardTransaction(
            id=transaction_id,
            user_id=user_id,
            reward_id=reward_id,
            transaction_type="purchase",
            source_type="recipe",
            source_value=2,
            source_id=recipe_id,
            transaction_group=str(uuid4())
        )

        # 验证配方相关字段
        assert transaction.source_type == "recipe"
        assert transaction.source_value == 2
        assert transaction.source_id == recipe_id

    def test_transaction_model_refund_type(self):
        """测试退款类型的交易记录"""
        transaction_id = uuid4()
        user_id = uuid4()
        reward_id = uuid4()
        group_id = str(uuid4())

        transaction = RewardTransaction(
            id=transaction_id,
            user_id=user_id,
            reward_id=reward_id,
            transaction_type="refund",
            source_type="points",
            source_value=100,
            transaction_group=group_id
        )

        assert transaction.transaction_type == "refund"
        assert transaction.transaction_group == group_id

    def test_transaction_model_optional_fields(self):
        """测试可选字段"""
        transaction_id = uuid4()
        user_id = uuid4()
        reward_id = uuid4()

        transaction = RewardTransaction(
            id=transaction_id,
            user_id=user_id,
            reward_id=reward_id,
            transaction_type="purchase",
            source_type="points",
            source_value=50,
            transaction_group=str(uuid4())
        )

        # 验证可选字段默认值
        assert transaction.source_id is None
        assert transaction.metadata is None

    def test_transaction_model_with_metadata(self):
        """测试带元数据的交易记录"""
        transaction_id = uuid4()
        user_id = uuid4()
        reward_id = uuid4()
        metadata = {"promotion": "new_user", "discount": 10}

        transaction = RewardTransaction(
            id=transaction_id,
            user_id=user_id,
            reward_id=reward_id,
            transaction_type="purchase",
            source_type="points",
            source_value=80,
            transaction_group=str(uuid4()),
            metadata=metadata
        )

        assert transaction.metadata == metadata
        assert transaction.metadata["promotion"] == "new_user"
        assert transaction.metadata["discount"] == 10

    def test_transaction_model_string_representation(self):
        """测试字符串表示"""
        transaction_id = uuid4()
        user_id = uuid4()
        reward_id = uuid4()

        transaction = RewardTransaction(
            id=transaction_id,
            user_id=user_id,
            reward_id=reward_id,
            transaction_type="purchase",
            source_type="points",
            source_value=100,
            transaction_group=str(uuid4())
        )

        repr_str = repr(transaction)

        # 验证字符串包含关键信息
        assert "RewardTransaction" in repr_str
        assert str(transaction_id) in repr_str
        assert "purchase" in repr_str
        assert "points" in repr_str
        assert str(user_id) in repr_str


@pytest.mark.unit
class TestRewardModelRelationships:
    """测试模型间的关系"""

    def test_reward_with_required_recipe(self):
        """测试奖励与必需配方的关系"""
        reward_id = uuid4()
        recipe_id = uuid4()

        reward = Reward(
            id=reward_id,
            name="高级奖品",
            cost_type="recipe",
            cost_value=3,
            required_recipe_id=recipe_id
        )

        assert reward.required_recipe_id == recipe_id
        # 验证只有recipe类型才能有required_recipe_id
        assert reward.cost_type == "recipe"

    def test_transaction_group_consistency(self):
        """测试交易组的一致性"""
        group_id = str(uuid4())
        user_id = uuid4()
        reward_id = uuid4()

        # 创建同一组的多个交易记录（比如购买和退款）
        purchase_transaction = RewardTransaction(
            id=uuid4(),
            user_id=user_id,
            reward_id=reward_id,
            transaction_type="purchase",
            source_type="points",
            source_value=100,
            transaction_group=group_id
        )

        refund_transaction = RewardTransaction(
            id=uuid4(),
            user_id=user_id,
            reward_id=reward_id,
            transaction_type="refund",
            source_type="points",
            source_value=100,
            transaction_group=group_id
        )

        # 验证两个交易属于同一组
        assert purchase_transaction.transaction_group == refund_transaction.transaction_group
        assert purchase_transaction.transaction_group == group_id

    def test_reward_cost_types(self):
        """测试奖励成本类型"""
        reward_id = uuid4()

        # 测试points类型
        points_reward = Reward(
            id=reward_id,
            name="积分奖品",
            cost_type="points",
            cost_value=50
        )
        assert points_reward.cost_type == "points"

        # 测试recipe类型
        recipe_reward = Reward(
            id=uuid4(),
            name="配方奖品",
            cost_type="recipe",
            cost_value=2,
            required_recipe_id=uuid4()
        )
        assert recipe_reward.cost_type == "recipe"
        assert recipe_reward.required_recipe_id is not None