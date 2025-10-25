"""
Reward领域模型测试套件（修正版）

测试Reward、RewardRecipe、RewardTransaction模型的基本功能，
根据实际模型字段编写测试。

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
            points_value=100,
            cost_type="points",
            cost_value=50,
            category="测试分类",
            image_url="https://example.com/image.jpg"
        )

        # 验证基本字段
        assert reward.id == reward_id
        assert reward.name == "测试奖品"
        assert reward.description == "这是一个测试奖品"
        assert reward.points_value == 100
        assert reward.cost_type == "points"
        assert reward.cost_value == 50
        assert reward.category == "测试分类"
        assert reward.image_url == "https://example.com/image.jpg"
        assert reward.is_active is True
        assert reward.stock_quantity == 0
        assert reward.created_at is not None

    def test_reward_model_with_recipe_cost(self):
        """测试使用recipe作为成本的奖品"""
        reward_id = uuid4()

        reward = Reward(
            id=reward_id,
            name="配方奖品",
            description="需要配方兑换的奖品",
            points_value=200,
            cost_type="recipe",
            cost_value=2,
            category="配方类"
        )

        assert reward.cost_type == "recipe"
        assert reward.cost_value == 2
        assert reward.points_value == 200

    def test_reward_model_optional_fields(self):
        """测试可选字段的默认值"""
        reward_id = uuid4()

        reward = Reward(
            id=reward_id,
            name="最简奖品",
            points_value=10,
            cost_type="points",
            cost_value=5,
            category="基础类"
        )

        # 验证默认值
        assert reward.description is None
        assert reward.image_url is None
        assert reward.stock_quantity == 0
        assert reward.is_active is True

    def test_reward_model_stock_quantity(self):
        """测试库存数量字段"""
        reward_id = uuid4()

        reward = Reward(
            id=reward_id,
            name="限量奖品",
            points_value=150,
            cost_type="points",
            cost_value=75,
            category="限量类",
            stock_quantity=10
        )

        assert reward.stock_quantity == 10
        assert reward.stock_quantity >= 0  # 库存不能为负数

    def test_reward_model_category_validation(self):
        """测试分类字段"""
        reward_id = uuid4()

        reward = Reward(
            id=reward_id,
            name="分类奖品",
            points_value=80,
            cost_type="points",
            cost_value=40,
            category="电子产品"
        )

        assert reward.category == "电子产品"

    def test_reward_model_string_representation(self):
        """测试字符串表示"""
        reward_id = uuid4()

        reward = Reward(
            id=reward_id,
            name="字符串测试奖品",
            points_value=120,
            cost_type="points",
            cost_value=60,
            category="测试类"
        )

        repr_str = repr(reward)

        # 验证字符串包含关键信息
        assert "Reward" in repr_str
        assert str(reward_id) in repr_str
        assert "字符串测试奖品" in repr_str


@pytest.mark.unit
class TestRewardRecipeModel:
    """RewardRecipe模型测试类"""

    def test_recipe_model_creation(self):
        """测试RewardRecipe模型基本创建"""
        recipe_id = uuid4()
        reward_id = uuid4()

        recipe = RewardRecipe(
            id=recipe_id,
            name="测试配方",
            result_reward_id=reward_id,
            materials=[
                {"reward_id": str(uuid4()), "quantity": 2},
                {"reward_id": str(uuid4()), "quantity": 1}
            ]
        )

        # 验证基本字段
        assert recipe.id == recipe_id
        assert recipe.name == "测试配方"
        assert recipe.result_reward_id == reward_id
        assert len(recipe.materials) == 2
        assert recipe.is_active is True
        assert recipe.created_at is not None

    def test_recipe_model_optional_fields(self):
        """测试可选字段的默认值"""
        recipe_id = uuid4()
        reward_id = uuid4()

        recipe = RewardRecipe(
            id=recipe_id,
            result_reward_id=reward_id
        )

        # 验证默认值
        assert recipe.name is None
        assert recipe.materials == []
        assert recipe.is_active is True

    def test_recipe_model_with_empty_materials(self):
        """测试空材料列表的配方"""
        recipe_id = uuid4()
        reward_id = uuid4()

        recipe = RewardRecipe(
            id=recipe_id,
            name="空配方",
            result_reward_id=reward_id,
            materials=[]
        )

        assert recipe.materials == []
        assert len(recipe.materials) == 0

    def test_recipe_model_complex_materials(self):
        """测试复杂材料列表"""
        recipe_id = uuid4()
        reward_id = uuid4()
        material1_id = uuid4()
        material2_id = uuid4()

        materials = [
            {"reward_id": str(material1_id), "quantity": 3},
            {"reward_id": str(material2_id), "quantity": 1},
            {"reward_id": str(uuid4()), "quantity": 2}
        ]

        recipe = RewardRecipe(
            id=recipe_id,
            name="复杂配方",
            result_reward_id=reward_id,
            materials=materials
        )

        assert len(recipe.materials) == 3
        assert recipe.materials[0]["quantity"] == 3
        assert recipe.materials[1]["quantity"] == 1
        assert recipe.materials[2]["quantity"] == 2


@pytest.mark.unit
class TestRewardTransactionModel:
    """RewardTransaction模型测试类"""

    def test_transaction_model_creation_positive(self):
        """测试正数数量（获得）的交易记录创建"""
        transaction_id = uuid4()
        user_id = str(uuid4())
        reward_id = str(uuid4())

        transaction = RewardTransaction(
            id=transaction_id,
            user_id=user_id,
            reward_id=reward_id,
            source_type="top3_lottery",
            quantity=1,
            transaction_group=str(uuid4())
        )

        # 验证基本字段
        assert transaction.id == transaction_id
        assert transaction.user_id == user_id
        assert transaction.reward_id == reward_id
        assert transaction.source_type == "top3_lottery"
        assert transaction.quantity == 1
        assert transaction.transaction_group is not None
        assert transaction.created_at is not None

    def test_transaction_model_creation_negative(self):
        """测试负数数量（消耗）的交易记录创建"""
        transaction_id = uuid4()
        user_id = str(uuid4())
        reward_id = str(uuid4())
        source_id = str(uuid4())

        transaction = RewardTransaction(
            id=transaction_id,
            user_id=user_id,
            reward_id=reward_id,
            source_type="recipe_consume",
            source_id=source_id,
            quantity=-2,
            transaction_group=str(uuid4())
        )

        # 验证消耗字段
        assert transaction.source_type == "recipe_consume"
        assert transaction.source_id == source_id
        assert transaction.quantity == -2

    def test_transaction_model_recipe_produce(self):
        """测试配方产出类型的交易记录"""
        transaction_id = uuid4()
        user_id = str(uuid4())
        reward_id = str(uuid4())
        recipe_id = str(uuid4())

        transaction = RewardTransaction(
            id=transaction_id,
            user_id=user_id,
            reward_id=reward_id,
            source_type="recipe_produce",
            source_id=recipe_id,
            quantity=1,
            transaction_group=str(uuid4())
        )

        assert transaction.source_type == "recipe_produce"
        assert transaction.source_id == recipe_id
        assert transaction.quantity == 1

    def test_transaction_model_optional_fields(self):
        """测试可选字段"""
        transaction_id = uuid4()
        user_id = str(uuid4())
        reward_id = str(uuid4())

        transaction = RewardTransaction(
            id=transaction_id,
            user_id=user_id,
            reward_id=reward_id,
            source_type="top3_lottery",
            quantity=1
        )

        # 验证可选字段默认值
        assert transaction.source_id is None
        assert transaction.transaction_group is None

    def test_transaction_model_group_consistency(self):
        """测试交易组的一致性"""
        group_id = str(uuid4())
        user_id = str(uuid4())
        reward1_id = str(uuid4())
        reward2_id = str(uuid4())

        # 创建同一组的多个交易记录（配方兑换）
        consume_transaction = RewardTransaction(
            id=uuid4(),
            user_id=user_id,
            reward_id=reward1_id,
            source_type="recipe_consume",
            source_id=str(uuid4()),
            quantity=-2,
            transaction_group=group_id
        )

        produce_transaction = RewardTransaction(
            id=uuid4(),
            user_id=user_id,
            reward_id=reward2_id,
            source_type="recipe_produce",
            source_id=str(uuid4()),
            quantity=1,
            transaction_group=group_id
        )

        # 验证两个交易属于同一组
        assert consume_transaction.transaction_group == produce_transaction.transaction_group
        assert consume_transaction.transaction_group == group_id

    def test_transaction_model_string_representation(self):
        """测试字符串表示"""
        transaction_id = uuid4()
        user_id = str(uuid4())
        reward_id = str(uuid4())

        transaction = RewardTransaction(
            id=transaction_id,
            user_id=user_id,
            reward_id=reward_id,
            source_type="top3_lottery",
            quantity=1,
            transaction_group=str(uuid4())
        )

        repr_str = repr(transaction)

        # 验证字符串包含关键信息
        assert "RewardTransaction" in repr_str
        assert str(transaction_id) in repr_str
        assert "top3_lottery" in repr_str
        assert user_id in repr_str


@pytest.mark.unit
class TestRewardModelRelationships:
    """测试模型间的关系"""

    def test_reward_cost_types(self):
        """测试奖励成本类型"""
        reward_id = uuid4()

        # 测试points类型
        points_reward = Reward(
            id=reward_id,
            name="积分奖品",
            points_value=100,
            cost_type="points",
            cost_value=50,
            category="积分类"
        )
        assert points_reward.cost_type == "points"

        # 测试recipe类型
        recipe_reward = Reward(
            id=uuid4(),
            name="配方奖品",
            points_value=200,
            cost_type="recipe",
            cost_value=3,
            category="配方类"
        )
        assert recipe_reward.cost_type == "recipe"

    def test_recipe_to_reward_relationship(self):
        """测试配方与结果奖品的关系"""
        recipe_id = uuid4()
        reward_id = uuid4()
        material1_id = uuid4()

        recipe = RewardRecipe(
            id=recipe_id,
            name="升级配方",
            result_reward_id=reward_id,
            materials=[
                {"reward_id": str(material1_id), "quantity": 2}
            ]
        )

        # 验证配方指向正确的奖品
        assert recipe.result_reward_id == reward_id
        assert len(recipe.materials) == 1
        assert recipe.materials[0]["reward_id"] == str(material1_id)

    def test_transaction_source_types(self):
        """测试不同的交易来源类型"""
        user_id = str(uuid4())
        reward_id = str(uuid4())

        # Top3抽奖
        lottery_transaction = RewardTransaction(
            id=uuid4(),
            user_id=user_id,
            reward_id=reward_id,
            source_type="top3_lottery",
            quantity=1
        )
        assert lottery_transaction.source_type == "top3_lottery"

        # 配方消耗
        consume_transaction = RewardTransaction(
            id=uuid4(),
            user_id=user_id,
            reward_id=reward_id,
            source_type="recipe_consume",
            source_id=str(uuid4()),
            quantity=-1
        )
        assert consume_transaction.source_type == "recipe_consume"

        # 配方产出
        produce_transaction = RewardTransaction(
            id=uuid4(),
            user_id=user_id,
            reward_id=reward_id,
            source_type="recipe_produce",
            source_id=str(uuid4()),
            quantity=1
        )
        assert produce_transaction.source_type == "recipe_produce"