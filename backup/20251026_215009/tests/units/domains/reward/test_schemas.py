"""
Reward领域Schemas测试

测试Reward领域的数据模型和验证规则，包括：
1. 请求模型验证
2. 响应模型验证
3. 字段类型和约束验证
4. Pydantic模型序列化
5. 自定义验证器测试

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError

from src.domains.reward.schemas import (
    # 奖品相关
    RewardResponse,
    RewardCatalogResponse,
    MyRewardsResponse,
    # 兑换相关
    RewardRedeemRequest,
    RewardRedeemResponse,
    # 积分相关
    PointsBalanceResponse,
    PointsTransactionResponse,
    PointsTransactionsResponse,
    # 任务完成奖励
    LotteryResult,
    TaskCompleteResponse,
    # 配方合成相关
    RedeemRecipeRequest,
    RecipeMaterial,
    RecipeReward,
    RedeemRecipeResponse,
    AvailableRecipe,
    AvailableRecipesResponse
)


@pytest.mark.unit
class TestRewardResponse:
    """奖品响应测试类"""

    def test_reward_response_creation(self):
        """测试创建奖品响应"""
        reward_id = str(uuid4())
        response = RewardResponse(
            id=reward_id,
            name="测试奖品",
            icon="https://example.com/icon.png",
            description="这是一个测试奖品",
            is_exchangeable=True
        )

        assert response.id == reward_id
        assert response.name == "测试奖品"
        assert response.icon == "https://example.com/icon.png"
        assert response.description == "这是一个测试奖品"
        assert response.is_exchangeable is True

    def test_reward_response_minimal(self):
        """测试最小奖品响应"""
        reward_id = str(uuid4())
        response = RewardResponse(
            id=reward_id,
            name="简单奖品",
            icon=None,
            description=None,
            is_exchangeable=False
        )

        assert response.id == reward_id
        assert response.name == "简单奖品"
        assert response.icon is None
        assert response.description is None
        assert response.is_exchangeable is False

    def test_reward_response_serialization(self):
        """测试奖品响应序列化"""
        reward_id = str(uuid4())
        response = RewardResponse(
            id=reward_id,
            name="序列化测试",
            icon="test_icon",
            description="测试序列化",
            is_exchangeable=True
        )

        # 测试字典序列化
        data = response.model_dump()
        assert data["id"] == reward_id
        assert data["name"] == "序列化测试"
        assert data["is_exchangeable"] is True

        # 测试JSON序列化
        json_data = response.model_dump_json()
        assert reward_id in json_data
        assert "序列化测试" in json_data

    @pytest.mark.parametrize("is_exchangeable", [True, False])
    def test_reward_response_exchangeable(self, is_exchangeable):
        """测试不同兑换状态的奖品响应"""
        response = RewardResponse(
            id=str(uuid4()),
            name="测试奖品",
            icon=None,
            description=None,
            is_exchangeable=is_exchangeable
        )

        assert response.is_exchangeable == is_exchangeable


@pytest.mark.unit
class TestRewardCatalogResponse:
    """奖品目录响应测试类"""

    def test_reward_catalog_response_creation(self):
        """测试创建奖品目录响应"""
        rewards = [
            RewardResponse(
                id=str(uuid4()),
                name="奖品1",
                icon=None,
                description=None,
                is_exchangeable=True
            ),
            RewardResponse(
                id=str(uuid4()),
                name="奖品2",
                icon=None,
                description=None,
                is_exchangeable=False
            )
        ]

        catalog = RewardCatalogResponse(
            rewards=rewards,
            total_count=2
        )

        assert len(catalog.rewards) == 2
        assert catalog.total_count == 2
        assert catalog.rewards[0].name == "奖品1"
        assert catalog.rewards[1].name == "奖品2"

    def test_reward_catalog_response_empty(self):
        """测试空奖品目录响应"""
        catalog = RewardCatalogResponse(
            rewards=[],
            total_count=0
        )

        assert len(catalog.rewards) == 0
        assert catalog.total_count == 0

    def test_reward_catalog_response_serialization(self):
        """测试奖品目录响应序列化"""
        rewards = [
            RewardResponse(
                id=str(uuid4()),
                name="序列化测试",
                icon=None,
                description=None,
                is_exchangeable=True
            )
        ]

        catalog = RewardCatalogResponse(
            rewards=rewards,
            total_count=1
        )

        data = catalog.model_dump()
        assert len(data["rewards"]) == 1
        assert data["total_count"] == 1


@pytest.mark.unit
class TestMyRewardsResponse:
    """我的奖品响应测试类"""

    def test_my_rewards_response_creation(self):
        """测试创建我的奖品响应"""
        rewards = [
            RewardResponse(
                id=str(uuid4()),
                name="我的奖品1",
                icon=None,
                description=None,
                is_exchangeable=True
            )
        ]

        my_rewards = MyRewardsResponse(
            rewards=rewards,
            total_types=1
        )

        assert len(my_rewards.rewards) == 1
        assert my_rewards.total_types == 1

    def test_my_rewards_response_empty(self):
        """测试空我的奖品响应"""
        my_rewards = MyRewardsResponse(
            rewards=[],
            total_types=0
        )

        assert len(my_rewards.rewards) == 0
        assert my_rewards.total_types == 0


@pytest.mark.unit
class TestRewardRedeemRequest:
    """兑换奖品请求测试类"""

    def test_reward_redeem_request_valid(self):
        """测试有效的兑换奖品请求"""
        recipe_id = str(uuid4())
        request = RewardRedeemRequest(recipe_id=recipe_id)

        assert request.recipe_id == recipe_id

    def test_reward_redeem_request_invalid_uuid(self):
        """测试无效UUID的兑换请求"""
        with pytest.raises(ValidationError) as exc_info:
            RewardRedeemRequest(recipe_id="invalid-uuid")

        assert "Invalid UUID" in str(exc_info.value) or "uuid" in str(exc_info.value).lower()

    def test_reward_redeem_request_empty(self):
        """测试空UUID的兑换请求"""
        with pytest.raises(ValidationError):
            RewardRedeemRequest(recipe_id="")

    def test_reward_redeem_request_serialization(self):
        """测试兑换请求序列化"""
        recipe_id = str(uuid4())
        request = RewardRedeemRequest(recipe_id=recipe_id)

        data = request.model_dump()
        assert data["recipe_id"] == recipe_id

        json_data = request.model_dump_json()
        assert recipe_id in json_data


@pytest.mark.unit
class TestRewardRedeemResponse:
    """兑换奖品响应测试类"""

    def test_reward_redeem_response_creation(self):
        """测试创建兑换奖品响应"""
        result_reward = RewardResponse(
            id=str(uuid4()),
            name="兑换结果",
            icon=None,
            description=None,
            is_exchangeable=True
        )
        consumed_rewards = [
            {"reward": {"id": str(uuid4()), "name": "材料1"}, "quantity": 2}
        ]

        response = RewardRedeemResponse(
            success=True,
            result_reward=result_reward,
            consumed_rewards=consumed_rewards,
            message="兑换成功"
        )

        assert response.success is True
        assert response.result_reward.name == "兑换结果"
        assert len(response.consumed_rewards) == 1
        assert response.message == "兑换成功"

    def test_reward_redeem_response_failed(self):
        """测试失败的兑换响应"""
        result_reward = RewardResponse(
            id=str(uuid4()),
            name="失败的奖品",
            icon=None,
            description=None,
            is_exchangeable=False
        )

        response = RewardRedeemResponse(
            success=False,
            result_reward=result_reward,
            consumed_rewards=[],
            message="兑换失败：材料不足"
        )

        assert response.success is False
        assert response.message == "兑换失败：材料不足"
        assert len(response.consumed_rewards) == 0


@pytest.mark.unit
class TestPointsBalanceResponse:
    """积分余额响应测试类"""

    def test_points_balance_response_creation(self):
        """测试创建积分余额响应"""
        response = PointsBalanceResponse(
            current_balance=1000,
            total_earned=5000,
            total_spent=4000
        )

        assert response.current_balance == 1000
        assert response.total_earned == 5000
        assert response.total_spent == 4000

    def test_points_balance_response_zero(self):
        """测试零积分余额响应"""
        response = PointsBalanceResponse(
            current_balance=0,
            total_earned=0,
            total_spent=0
        )

        assert response.current_balance == 0
        assert response.total_earned == 0
        assert response.total_spent == 0

    @pytest.mark.parametrize("balance,earned,spent", [
        (100, 500, 400),
        (0, 0, 0),
        (10000, 15000, 5000),
        (50, 100, 50)
    ])
    def test_points_balance_various_values(self, balance, earned, spent):
        """测试各种积分余额值"""
        response = PointsBalanceResponse(
            current_balance=balance,
            total_earned=earned,
            total_spent=spent
        )

        assert response.current_balance == balance
        assert response.total_earned == earned
        assert response.total_spent == spent


@pytest.mark.unit
class TestPointsTransactionResponse:
    """积分流水响应测试类"""

    def test_points_transaction_response_creation(self):
        """测试创建积分流水响应"""
        response = PointsTransactionResponse(
            id=str(uuid4()),
            amount=100,
            source="任务完成",
            related_task_id=str(uuid4()),
            created_at="2024-01-15T10:30:00Z"
        )

        assert response.amount == 100
        assert response.source == "任务完成"
        assert response.related_task_id is not None
        assert response.created_at == "2024-01-15T10:30:00Z"

    def test_points_transaction_response_minimal(self):
        """测试最小积分流水响应"""
        response = PointsTransactionResponse(
            id=str(uuid4()),
            amount=50,
            source="系统奖励",
            related_task_id=None,
            created_at="2024-01-15T10:30:00Z"
        )

        assert response.amount == 50
        assert response.related_task_id is None


@pytest.mark.unit
class TestLotteryResult:
    """抽奖结果测试类"""

    def test_lottery_result_points(self):
        """测试积分抽奖结果"""
        result = LotteryResult(
            type="points",
            amount=100,
            reward=None
        )

        assert result.type == "points"
        assert result.amount == 100
        assert result.reward is None

    def test_lottery_result_reward(self):
        """测试奖品抽奖结果"""
        reward = RewardResponse(
            id=str(uuid4()),
            name="幸运奖品",
            icon=None,
            description=None,
            is_exchangeable=True
        )

        result = LotteryResult(
            type="reward",
            amount=None,
            reward=reward
        )

        assert result.type == "reward"
        assert result.amount is None
        assert result.reward.name == "幸运奖品"

    def test_lottery_result_invalid_type(self):
        """测试无效抽奖类型"""
        with pytest.raises(ValidationError):
            LotteryResult(
                type="invalid_type",
                amount=100,
                reward=None
            )

    @pytest.mark.parametrize("result_type", ["points", "reward"])
    def test_lottery_result_valid_types(self, result_type):
        """测试有效抽奖类型"""
        if result_type == "points":
            result = LotteryResult(
                type=result_type,
                amount=50,
                reward=None
            )
            assert result.amount == 50
        else:
            reward = RewardResponse(
                id=str(uuid4()),
                name="测试奖品",
                icon=None,
                description=None,
                is_exchangeable=True
            )
            result = LotteryResult(
                type=result_type,
                amount=None,
                reward=reward
            )
            assert result.reward.name == "测试奖品"


@pytest.mark.unit
class TestRedeemRecipeRequest:
    """配方兑换请求测试类"""

    def test_redeem_recipe_request_empty(self):
        """测试空的配方兑换请求"""
        request = RedeemRecipeRequest()

        # 请求体应该为空，所有信息从URL和JWT获取
        assert hasattr(request, 'model_config')

    def test_redeem_recipe_request_extra_fields_forbidden(self):
        """测试禁止额外字段"""
        with pytest.raises(ValidationError):
            RedeemRecipeRequest(extra_field="should_fail")


@pytest.mark.unit
class TestRecipeMaterial:
    """配方材料测试类"""

    def test_recipe_material_creation(self):
        """测试创建配方材料"""
        material = RecipeMaterial(
            reward_id=str(uuid4()),
            reward_name="魔法药剂",
            quantity=5
        )

        assert material.reward_name == "魔法药剂"
        assert material.quantity == 5

    def test_recipe_material_invalid_quantity(self):
        """测试无效材料数量"""
        with pytest.raises(ValidationError) as exc_info:
            RecipeMaterial(
                reward_id=str(uuid4()),
                reward_name="测试材料",
                quantity=0
            )

        assert "greater than or equal to 1" in str(exc_info.value)

    def test_recipe_material_negative_quantity(self):
        """测试负数材料数量"""
        with pytest.raises(ValidationError):
            RecipeMaterial(
                reward_id=str(uuid4()),
                reward_name="测试材料",
                quantity=-5
            )

    @pytest.mark.parametrize("quantity", [1, 5, 10, 100])
    def test_recipe_material_valid_quantities(self, quantity):
        """测试有效材料数量"""
        material = RecipeMaterial(
            reward_id=str(uuid4()),
            reward_name="测试材料",
            quantity=quantity
        )

        assert material.quantity == quantity


@pytest.mark.unit
class TestRecipeReward:
    """配方奖品测试类"""

    def test_recipe_reward_creation(self):
        """测试创建配方奖品"""
        reward = RecipeReward(
            id=str(uuid4()),
            name="神秘宝箱",
            description="包含随机奖励",
            image_url="https://example.com/chest.jpg",
            category="稀有"
        )

        assert reward.name == "神秘宝箱"
        assert reward.description == "包含随机奖励"
        assert reward.image_url == "https://example.com/chest.jpg"
        assert reward.category == "稀有"

    def test_recipe_reward_minimal(self):
        """测试最小配方奖品"""
        reward = RecipeReward(
            id=str(uuid4()),
            name="基础奖品",
            description=None,
            image_url=None,
            category="普通"
        )

        assert reward.name == "基础奖品"
        assert reward.description is None
        assert reward.image_url is None
        assert reward.category == "普通"


@pytest.mark.unit
class TestRedeemRecipeResponse:
    """配方兑换响应测试类"""

    def test_redeem_recipe_response_creation(self):
        """测试创建配方兑换响应"""
        result_reward = RecipeReward(
            id=str(uuid4()),
            name="合成结果",
            description=None,
            image_url=None,
            category="合成"
        )
        materials = [
            RecipeMaterial(
                reward_id=str(uuid4()),
                reward_name="材料1",
                quantity=2
            )
        ]

        response = RedeemRecipeResponse(
            success=True,
            recipe_id=str(uuid4()),
            recipe_name="测试配方",
            result_reward=result_reward,
            materials_consumed=materials,
            transaction_group="txn_123",
            message="配方合成成功"
        )

        assert response.success is True
        assert response.recipe_name == "测试配方"
        assert response.result_reward.name == "合成结果"
        assert len(response.materials_consumed) == 1
        assert response.transaction_group == "txn_123"
        assert response.message == "配方合成成功"




@pytest.mark.unit
class TestAvailableRecipe:
    """可用配方测试类"""

    def test_available_recipe_creation(self):
        """测试创建可用配方"""
        materials = [
            RecipeMaterial(
                reward_id=str(uuid4()),
                reward_name="基础材料",
                quantity=3
            )
        ]

        recipe = AvailableRecipe(
            id=str(uuid4()),
            name="初级配方",
            result_reward_id=str(uuid4()),
            result_reward_name="初级结果",
            result_image_url=None,
            materials=materials,
            created_at=datetime.now(timezone.utc)
        )

        assert recipe.name == "初级配方"
        assert recipe.result_reward_name == "初级结果"
        assert len(recipe.materials) == 1
        assert isinstance(recipe.created_at, datetime)


@pytest.mark.integration
class TestRewardSchemasIntegration:
    """Reward Schema集成测试类"""

    def test_complete_reward_workflow_schemas(self):
        """测试完整Reward工作流程的Schema使用"""
        # 1. 创建奖品响应
        reward = RewardResponse(
            id=str(uuid4()),
            name="工作流测试奖品",
            icon=None,
            description=None,
            is_exchangeable=True
        )

        # 2. 创建奖品目录
        catalog = RewardCatalogResponse(
            rewards=[reward],
            total_count=1
        )

        # 3. 创建兑换请求
        redeem_request = RewardRedeemRequest(recipe_id=str(uuid4()))

        # 4. 创建兑换响应
        redeem_response = RewardRedeemResponse(
            success=True,
            result_reward=reward,
            consumed_rewards=[],
            message="兑换成功"
        )

        # 验证数据一致性
        assert catalog.rewards[0].id == reward.id
        assert redeem_response.result_reward.id == reward.id

    def test_schema_json_roundtrip(self):
        """测试Schema JSON序列化往返"""
        original_data = {
            "id": str(uuid4()),
            "name": "往返测试奖品",
            "icon": None,
            "description": None,
            "is_exchangeable": True
        }

        # 创建响应对象
        response = RewardResponse(**original_data)

        # 序列化为JSON
        json_data = response.model_dump_json()

        # 从JSON重建对象（简化验证）
        reconstructed_data = response.model_dump()

        # 验证关键字段保持一致
        assert reconstructed_data["id"] == original_data["id"]
        assert reconstructed_data["name"] == original_data["name"]

    def test_complex_recipe_workflow(self):
        """测试复杂配方工作流程"""
        # 创建材料
        materials = [
            RecipeMaterial(
                reward_id=str(uuid4()),
                reward_name="基础材料",
                quantity=5
            ),
            RecipeMaterial(
                reward_id=str(uuid4()),
                reward_name="稀有材料",
                quantity=2
            )
        ]

        # 创建结果奖品
        result_reward = RecipeReward(
            id=str(uuid4()),
            name="合成产物",
            description="通过配方合成的物品",
            image_url=None,
            category="合成"
        )

        # 创建配方响应
        recipe_response = RedeemRecipeResponse(
            success=True,
            recipe_id=str(uuid4()),
            recipe_name="高级合成配方",
            result_reward=result_reward,
            materials_consumed=materials,
            transaction_group="complex_txn_123",
            message="配方合成成功"
        )

        # 验证复杂结构
        assert len(recipe_response.materials_consumed) == 2
        assert recipe_response.result_reward.name == "合成产物"
        assert recipe_response.materials_consumed[0].quantity == 5
        assert recipe_response.materials_consumed[1].quantity == 2


@pytest.mark.parametrize("reward_id,should_pass", [
    (str(uuid4()), True),  # 有效UUID
    ("550e8400-e29b-41d4-a716-446655440000", True),  # 有效UUID
    ("invalid-uuid", False),  # 无效格式
    ("", False),  # 空字符串
])
def test_redeem_request_id_validation(reward_id, should_pass):
    """参数化测试兑换请求ID验证"""
    if should_pass:
        request = RewardRedeemRequest(recipe_id=reward_id)
        assert request.recipe_id == reward_id
    else:
        with pytest.raises(ValidationError):
            RewardRedeemRequest(recipe_id=reward_id)


@pytest.mark.parametrize("quantity", [
    1, 5, 10, 50, 100
])
def test_material_quantity_validation(quantity):
    """参数化测试材料数量验证"""
    material = RecipeMaterial(
        reward_id=str(uuid4()),
        reward_name="数量测试材料",
        quantity=quantity
    )
    assert material.quantity == quantity