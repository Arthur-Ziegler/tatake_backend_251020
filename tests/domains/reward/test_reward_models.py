"""
Reward领域模型测试

测试Reward、RewardRecipe、RewardTransaction模型的基本功能，包括：
1. 奖品实体的CRUD操作
2. 奖品兑换配方
3. 流水记录创建
4. 数据验证和约束

遵循模块化设计原则，专注于模型层面的数据验证。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.domains.reward.models import Reward, RewardRecipe, RewardTransaction
# 使用test_db_session fixture而不是导入函数


@pytest.mark.unit
class TestRewardModel:
    """Reward模型测试类"""

    def test_reward_creation_minimal(self, test_db_session):
        """测试Reward最小化创建"""
        reward = Reward(
            name="测试奖品",
            description="这是一个测试奖品",
            points_value=100,
            cost_type="points",
            cost_value=100,
            category="测试分类"
        )

        test_db_session.add(reward)
        test_db_session.commit()

        assert reward.id is not None
        assert reward.name == "测试奖品"
        assert reward.points_value == 100
        assert reward.cost_type == "points"
        assert reward.cost_value == 100
        assert reward.category == "测试分类"
        assert reward.is_active is True
        assert reward.stock_quantity == 0

    def test_reward_with_all_fields(self, test_db_session):
        """测试包含所有字段的Reward"""
        reward = Reward(
            name="完整测试奖品",
            description="这是一个包含所有字段的测试奖品",
            points_value=500,
            image_url="https://example.com/image.jpg",
            cost_type="points",
            cost_value=300,
            stock_quantity=50,
            category="高级奖品",
            is_active=True
        )

        test_db_session.add(reward)
        test_db_session.commit()

        assert reward.name == "完整测试奖品"
        assert reward.description == "这是一个包含所有字段的测试奖品"
        assert reward.points_value == 500
        assert reward.image_url == "https://example.com/image.jpg"
        assert reward.cost_type == "points"
        assert reward.cost_value == 300
        assert reward.stock_quantity == 50
        assert reward.category == "高级奖品"
        assert reward.is_active is True

    def test_reward_different_cost_types(self, test_db_session):
        """测试不同成本类型的Reward"""
        # 积分奖品
        points_reward = Reward(
            name="积分奖品",
            description="使用积分兑换的奖品",
            points_value=200,
            cost_type="points",
            cost_value=200,
            category="积分兑换"
        )

        # 配方奖品
        recipe_reward = Reward(
            name="配方奖品",
            description="使用配方兑换的奖品",
            points_value=1000,
            cost_type="recipe",
            cost_value=5,
            category="配方兑换"
        )

        test_db_session.add_all([points_reward, recipe_reward])
        test_db_session.commit()

        assert points_reward.cost_type == "points"
        assert points_reward.cost_value == 200
        assert recipe_reward.cost_type == "recipe"
        assert recipe_reward.cost_value == 5

    def test_reward_stock_management(self, test_db_session):
        """测试奖品库存管理"""
        reward = Reward(
            name="库存测试奖品",
            description="用于测试库存管理",
            points_value=150,
            cost_type="points",
            cost_value=150,
            stock_quantity=100,
            category="库存测试"
        )

        test_db_session.add(reward)
        test_db_session.commit()

        # 验证初始库存
        assert reward.stock_quantity == 100

        # 模拟库存减少
        reward.stock_quantity = 80
        test_db_session.commit()

        assert reward.stock_quantity == 80

    def test_reward_active_status(self, test_db_session):
        """测试奖品激活状态"""
        # 创建激活的奖品
        active_reward = Reward(
            name="激活奖品",
            description="这是一个激活的奖品",
            points_value=100,
            cost_type="points",
            cost_value=100,
            category="激活测试",
            is_active=True
        )

        # 创建未激活的奖品
        inactive_reward = Reward(
            name="未激活奖品",
            description="这是一个未激活的奖品",
            points_value=200,
            cost_type="points",
            cost_value=200,
            category="未激活测试",
            is_active=False
        )

        test_db_session.add_all([active_reward, inactive_reward])
        test_db_session.commit()

        assert active_reward.is_active is True
        assert inactive_reward.is_active is False

    def test_reward_timestamps(self, test_db_session):
        """测试时间戳"""
        before_creation = datetime.now(timezone.utc)

        reward = Reward(
            name="时间戳测试奖品",
            description="测试时间戳字段",
            points_value=300,
            cost_type="points",
            cost_value=300,
            category="时间测试"
        )

        test_db_session.add(reward)
        test_db_session.commit()

        after_creation = datetime.now(timezone.utc)

        # 验证创建时间在合理范围内
        assert before_creation <= reward.created_at <= after_creation
        assert reward.updated_at is not None

    def test_reward_string_representation(self, test_db_session):
        """测试字符串表示"""
        reward = Reward(
            name="字符串表示测试",
            description="测试repr方法",
            points_value=250,
            cost_type="points",
            cost_value=250,
            category="字符串测试"
        )

        test_db_session.add(reward)
        test_db_session.commit()

        repr_str = repr(reward)
        assert "Reward" in repr_str
        assert str(reward.id) in repr_str
        assert reward.name in repr_str

    def test_reward_field_validation(self, test_db_session):
        """测试字段验证"""
        # 测试负数points_value
        with pytest.raises(Exception):  # 可能是ValidationError或数据库约束错误
            reward = Reward(
                name="无效奖品",
                points_value=-100,  # 负数
                cost_type="points",
                cost_value=100,
                category="无效测试"
            )
            test_db_session.add(reward)
            test_db_session.commit()

        test_db_session.rollback()

        # 测试负数cost_value
        with pytest.raises(Exception):
            reward = Reward(
                name="无效奖品2",
                points_value=100,
                cost_type="points",
                cost_value=-50,  # 负数
                category="无效测试"
            )
            test_db_session.add(reward)
            test_db_session.commit()

        test_db_session.rollback()

        # 测试负数stock_quantity
        with pytest.raises(Exception):
            reward = Reward(
                name="无效奖品3",
                points_value=100,
                cost_type="points",
                cost_value=100,
                stock_quantity=-10,  # 负数
                category="无效测试"
            )
            test_db_session.add(reward)
            test_db_session.commit()


@pytest.mark.unit
class TestRewardRecipeModel:
    """RewardRecipe模型测试类"""

    def test_reward_recipe_creation(self, test_db_session):
        """测试RewardRecipe创建"""
        recipe = RewardRecipe(
            name="测试配方",
            description="这是一个测试配方",
            required_points=1000,
            required_recipes='{"other_recipe": 2}',
            output_reward_id=str(uuid4()),
            output_quantity=1
        )

        test_db_session.add(recipe)
        test_db_session.commit()

        assert recipe.id is not None
        assert recipe.name == "测试配方"
        assert recipe.required_points == 1000
        assert recipe.output_quantity == 1
        assert isinstance(recipe.required_recipes, dict)

    def test_reward_recipe_with_multiple_recipes(self, test_db_session):
        """测试包含多个配方的RewardRecipe"""
        recipe = RewardRecipe(
            name="复合配方",
            description="需要多个其他配方的配方",
            required_points=500,
            required_recipes='{"basic_recipe": 3, "advanced_recipe": 1}',
            output_reward_id=str(uuid4()),
            output_quantity=2
        )

        test_db_session.add(recipe)
        test_db_session.commit()

        recipes_dict = recipe.required_recipes
        assert recipes_dict["basic_recipe"] == 3
        assert recipes_dict["advanced_recipe"] == 1

    def test_reward_recipe_json_fields(self, test_db_session):
        """测试JSON字段处理"""
        # 测试复杂的JSON数据
        complex_recipes = {
            "recipe_a": 2,
            "recipe_b": 1,
            "recipe_c": 3,
            "metadata": {
                "difficulty": "medium",
                "time_required": 30
            }
        }

        recipe = RewardRecipe(
            name="复杂配方",
            description="包含复杂JSON数据的配方",
            required_points=2000,
            required_recipes=complex_recipes,
            output_reward_id=str(uuid4()),
            output_quantity=1
        )

        test_db_session.add(recipe)
        test_db_session.commit()

        # 验证JSON数据正确存储
        assert recipe.required_recipes == complex_recipes
        assert recipe.required_recipes["metadata"]["difficulty"] == "medium"


@pytest.mark.unit
class TestRewardTransactionModel:
    """RewardTransaction模型测试类"""

    def test_reward_transaction_creation(self, test_db_session):
        """测试RewardTransaction创建"""
        transaction = RewardTransaction(
            user_id=str(uuid4()),
            reward_id=str(uuid4()),
            transaction_type="redeem",
            source_type="reward_redeem",
            points_change=-100,
            balance_after=900
        )

        test_db_session.add(transaction)
        test_db_session.commit()

        assert transaction.id is not None
        assert transaction.transaction_type == "redeem"
        assert transaction.source_type == "reward_redeem"
        assert transaction.points_change == -100
        assert transaction.balance_after == 900

    def test_reward_transaction_earn_points(self, test_db_session):
        """测试赚取积分的流水记录"""
        transaction = RewardTransaction(
            user_id=str(uuid4()),
            reward_id=str(uuid4()),
            transaction_type="earn",
            source_type="task_complete",
            points_change=50,
            balance_after=550,
            description="完成任务获得积分"
        )

        test_db_session.add(transaction)
        test_db_session.commit()

        assert transaction.points_change == 50  # 正数表示增加
        assert transaction.balance_after == 550

    def test_reward_transaction_group(self, test_db_session):
        """测试事务组关联"""
        transaction_group = str(uuid4())

        # 创建同一事务组的多个记录
        transaction1 = RewardTransaction(
            user_id=str(uuid4()),
            reward_id=str(uuid4()),
            transaction_type="redeem",
            source_type="reward_redeem",
            points_change=-200,
            balance_after=800,
            transaction_group=transaction_group
        )

        transaction2 = RewardTransaction(
            user_id=str(uuid4()),
            reward_id=str(uuid4()),
            transaction_type="refund",
            source_type="reward_refund",
            points_change=200,
            balance_after=1000,
            transaction_group=transaction_group
        )

        test_db_session.add_all([transaction1, transaction2])
        test_db_session.commit()

        assert transaction1.transaction_group == transaction_group
        assert transaction2.transaction_group == transaction_group

    def test_reward_transaction_metadata(self, test_db_session):
        """测试元数据字段"""
        metadata = {
            "task_id": str(uuid4()),
            "reward_category": "电子产品",
            "redemption_date": datetime.now(timezone.utc).isoformat()
        }

        transaction = RewardTransaction(
            user_id=str(uuid4()),
            reward_id=str(uuid4()),
            transaction_type="redeem",
            source_type="reward_redeem",
            points_change=-150,
            balance_after=850,
            metadata=metadata
        )

        test_db_session.add(transaction)
        test_db_session.commit()

        assert transaction.metadata == metadata
        assert "task_id" in transaction.metadata
        assert transaction.metadata["reward_category"] == "电子产品"

    def test_reward_transaction_balance_calculation(self, test_db_session):
        """测试余额计算正确性"""
        user_id = str(uuid4())
        initial_balance = 1000

        # 赚取积分
        earn_transaction = RewardTransaction(
            user_id=user_id,
            reward_id=str(uuid4()),
            transaction_type="earn",
            source_type="task_complete",
            points_change=100,
            balance_after=initial_balance + 100
        )

        # 兑换奖品
        redeem_transaction = RewardTransaction(
            user_id=user_id,
            reward_id=str(uuid4()),
            transaction_type="redeem",
            source_type="reward_redeem",
            points_change=-200,
            balance_after=initial_balance + 100 - 200
        )

        test_db_session.add_all([earn_transaction, redeem_transaction])
        test_db_session.commit()

        # 验证余额计算正确
        assert earn_transaction.balance_after == 1100
        assert redeem_transaction.balance_after == 900

    def test_reward_transaction_types(self, test_db_session):
        """测试不同的事务类型"""
        user_id = str(uuid4())
        reward_id = str(uuid4())

        transaction_types = [
            ("earn", "task_complete", 50),
            ("redeem", "reward_redeem", -100),
            ("refund", "reward_refund", 100),
            ("adjust", "admin_adjust", 0)
        ]

        for trans_type, source_type, points_change in transaction_types:
            transaction = RewardTransaction(
                user_id=user_id,
                reward_id=reward_id,
                transaction_type=trans_type,
                source_type=source_type,
                points_change=points_change,
                balance_after=1000 + points_change
            )

            test_db_session.add(transaction)

        test_db_session.commit()

        # 验证所有事务类型都正确存储
        transactions = test_db_session.query(RewardTransaction).all()
        assert len(transactions) == 4

        for transaction in transactions:
            assert transaction.transaction_type in ["earn", "redeem", "refund", "adjust"]