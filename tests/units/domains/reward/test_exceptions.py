"""
Reward领域异常测试

测试Reward领域的异常定义和处理，包括：
1. 异常创建和属性验证
2. 异常继承关系
3. 错误消息格式
4. 状态码验证
5. 自定义属性测试

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from typing import List, Dict

from src.domains.reward.exceptions import (
    RewardException,
    RewardNotFoundException,
    RecipeNotFoundException,
    InsufficientRewardsException,
    InsufficientPointsException
)


@pytest.mark.unit
class TestRewardException:
    """Reward基础异常测试类"""

    def test_reward_exception_creation(self):
        """测试Reward基础异常创建"""
        detail = "测试错误详情"
        status_code = 400

        exception = RewardException(detail, status_code)

        assert exception.detail == detail
        assert exception.status_code == status_code
        assert str(exception) == detail

    def test_reward_exception_default_status_code(self):
        """测试Reward基础异常默认状态码"""
        exception = RewardException("测试错误")

        assert exception.status_code == 400
        assert exception.detail == "测试错误"

    def test_reward_exception_string_representation(self):
        """测试Reward异常字符串表示"""
        detail = "测试错误详情"
        status_code = 500
        exception = RewardException(detail, status_code)

        # 验证字符串表示包含关键信息
        str_repr = str(exception)
        assert detail in str_repr

    def test_reward_exception_inheritance(self):
        """测试Reward异常继承关系"""
        exception = RewardException("测试")

        assert isinstance(exception, Exception)
        assert isinstance(exception, RewardException)


@pytest.mark.unit
class TestRewardNotFoundException:
    """奖品未找到异常测试类"""

    def test_reward_not_found_with_id(self):
        """测试带奖品ID的异常创建"""
        reward_id = "reward_12345"
        exception = RewardNotFoundException(reward_id)

        assert f"奖品不存在: {reward_id}" in exception.detail
        assert exception.status_code == 404
        assert reward_id in str(exception)

    def test_reward_not_found_inheritance(self):
        """测试奖品未找到异常继承关系"""
        exception = RewardNotFoundException("test_reward")

        assert isinstance(exception, RewardException)
        assert isinstance(exception, RewardNotFoundException)
        assert isinstance(exception, Exception)

    @pytest.mark.parametrize("reward_id", [
        "reward_123",
        "uuid-string-12345-67890",
        "123e4567-e89b-12d3-a456-426614174000",
        "reward_with_underscores"
    ])
    def test_reward_not_found_various_ids(self, reward_id):
        """测试各种奖品ID格式的异常"""
        exception = RewardNotFoundException(reward_id)

        assert f"奖品不存在: {reward_id}" in exception.detail
        assert exception.status_code == 404


@pytest.mark.unit
class TestRecipeNotFoundException:
    """配方未找到异常测试类"""

    def test_recipe_not_found_with_id(self):
        """测试带配方ID的异常创建"""
        recipe_id = "recipe_12345"
        exception = RecipeNotFoundException(recipe_id)

        assert f"兑换配方不存在: {recipe_id}" in exception.detail
        assert exception.status_code == 404
        assert recipe_id in str(exception)

    def test_recipe_not_found_inheritance(self):
        """测试配方未找到异常继承关系"""
        exception = RecipeNotFoundException("test_recipe")

        assert isinstance(exception, RewardException)
        assert isinstance(exception, RecipeNotFoundException)
        assert isinstance(exception, Exception)

    @pytest.mark.parametrize("recipe_id", [
        "recipe_123",
        "recipe_uuid_string",
        "12345678-1234-5678-9012-123456789012",
        "recipe_with_dashes-and_underscores"
    ])
    def test_recipe_not_found_various_ids(self, recipe_id):
        """测试各种配方ID格式的异常"""
        exception = RecipeNotFoundException(recipe_id)

        assert f"兑换配方不存在: {recipe_id}" in exception.detail
        assert exception.status_code == 404


@pytest.mark.unit
class TestInsufficientRewardsException:
    """奖品数量不足异常测试类"""

    def test_insufficient_rewards_default(self):
        """测试默认奖品数量不足异常"""
        message = "材料不足"
        exception = InsufficientRewardsException(message)

        assert f"奖品数量不足: {message}" in exception.detail
        assert exception.status_code == 400
        assert exception.required_materials == []

    def test_insufficient_rewards_with_materials(self):
        """测试带材料列表的奖品数量不足异常"""
        message = "需要更多材料"
        materials = [
            {"item_id": "material_1", "required": 5, "available": 2},
            {"item_id": "material_2", "required": 3, "available": 0}
        ]
        exception = InsufficientRewardsException(message, materials)

        assert f"奖品数量不足: {message}" in exception.detail
        assert exception.status_code == 400
        assert exception.required_materials == materials
        assert len(exception.required_materials) == 2

    def test_insufficient_rewards_inheritance(self):
        """测试奖品数量不足异常继承关系"""
        exception = InsufficientRewardsException("测试")

        assert isinstance(exception, RewardException)
        assert isinstance(exception, InsufficientRewardsException)
        assert isinstance(exception, Exception)

    @pytest.mark.parametrize("message", [
        "材料不足",
        "库存不够",
        "需要的材料数量超过可用数量",
        "暂时缺货"
    ])
    def test_insufficient_rewards_various_messages(self, message):
        """测试各种错误消息的异常"""
        exception = InsufficientRewardsException(message)

        assert f"奖品数量不足: {message}" in exception.detail
        assert exception.status_code == 400


@pytest.mark.unit
class TestInsufficientPointsException:
    """积分不足异常测试类"""

    def test_insufficient_points_creation(self):
        """测试积分不足异常创建"""
        required = 100
        current = 50
        exception = InsufficientPointsException(required, current)

        assert f"积分不足，需要{required}积分，当前{current}积分" in exception.detail
        assert exception.status_code == 400
        assert str(required) in str(exception)
        assert str(current) in str(exception)

    def test_insufficient_points_zero_current(self):
        """测试当前积分为零的异常"""
        required = 50
        current = 0
        exception = InsufficientPointsException(required, current)

        assert f"积分不足，需要{required}积分，当前{current}积分" in exception.detail
        assert exception.status_code == 400

    def test_insufficient_points_large_values(self):
        """测试大数值积分的异常"""
        required = 10000
        current = 5000
        exception = InsufficientPointsException(required, current)

        assert f"积分不足，需要{required}积分，当前{current}积分" in exception.detail
        assert exception.status_code == 400

    def test_insufficient_points_inheritance(self):
        """测试积分不足异常继承关系"""
        exception = InsufficientPointsException(100, 50)

        assert isinstance(exception, RewardException)
        assert isinstance(exception, InsufficientPointsException)
        assert isinstance(exception, Exception)

    @pytest.mark.parametrize("required,current", [
        (100, 50),
        (50, 0),
        (1000, 999),
        (1, 0),
        (500, 250)
    ])
    def test_insufficient_points_various_values(self, required, current):
        """测试各种积分值的异常"""
        exception = InsufficientPointsException(required, current)

        assert f"积分不足，需要{required}积分，当前{current}积分" in exception.detail
        assert exception.status_code == 400


@pytest.mark.integration
class TestRewardExceptionsIntegration:
    """Reward异常集成测试类"""

    def test_exception_hierarchy_consistency(self):
        """测试异常层次结构一致性"""
        # 所有自定义异常都应该继承自RewardException
        base_exception = RewardException("base")
        reward_not_found = RewardNotFoundException("reward")
        recipe_not_found = RecipeNotFoundException("recipe")
        insufficient_rewards = InsufficientRewardsException("test")
        insufficient_points = InsufficientPointsException(100, 50)

        # 验证继承关系
        assert isinstance(reward_not_found, RewardException)
        assert isinstance(recipe_not_found, RewardException)
        assert isinstance(insufficient_rewards, RewardException)
        assert isinstance(insufficient_points, RewardException)

    def test_exception_status_codes_uniqueness(self):
        """测试异常状态码唯一性"""
        exceptions = [
            RewardNotFoundException("test"),
            RecipeNotFoundException("test"),
            InsufficientRewardsException("test"),
            InsufficientPointsException(100, 50),
        ]

        status_codes = set()
        for exc in exceptions:
            status_codes.add(exc.status_code)

        # 验证主要HTTP状态码都被使用（允许重复）
        assert 404 in status_codes  # NotFoundException使用404
        assert 400 in status_codes  # 其他异常使用400

    def test_exception_raising_and_catching(self):
        """测试异常抛出和捕获"""
        # 测试基类异常
        with pytest.raises(RewardException) as exc_info:
            raise RewardException("基础异常")

        assert exc_info.value.detail == "基础异常"

        # 测试奖品未找到异常
        with pytest.raises(RewardNotFoundException) as exc_info:
            raise RewardNotFoundException("reward_123")

        assert exc_info.value.status_code == 404

        # 测试积分不足异常
        with pytest.raises(InsufficientPointsException) as exc_info:
            raise InsufficientPointsException(100, 50)

        assert exc_info.value.status_code == 400

    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("原始错误")
            except ValueError as original_error:
                raise RewardNotFoundException("chained_error") from original_error
        except RewardNotFoundException as chained_error:
            # 验证异常链
            assert chained_error.__cause__ is not None
            assert isinstance(chained_error.__cause__, ValueError)
            assert chained_error.__cause__.args[0] == "原始错误"
            assert "chained_error" in chained_error.detail

    def test_exception_serialization(self):
        """测试异常序列化兼容性"""
        exception = RewardNotFoundException("test_reward")

        # 验证异常可以正常序列化为JSON兼容格式
        error_dict = {
            "type": "RewardNotFoundException",
            "detail": exception.detail,
            "status_code": exception.status_code,
            "message": str(exception)
        }

        assert error_dict["type"] == "RewardNotFoundException"
        assert "test_reward" in error_dict["detail"]
        assert error_dict["status_code"] == 404
        assert "test_reward" in error_dict["message"]

    def test_materials_list_handling(self):
        """测试材料列表处理"""
        materials = [
            {"id": "item1", "required": 5, "available": 2},
            {"id": "item2", "required": 3, "available": 0}
        ]
        exception = InsufficientRewardsException("测试", materials)

        # 验证材料列表可以正常访问和修改
        assert len(exception.required_materials) == 2
        exception.required_materials.append({"id": "item3", "required": 1, "available": 0})
        assert len(exception.required_materials) == 3

    def test_exception_error_message_completeness(self):
        """测试异常错误消息完整性"""
        # 测试所有异常类型都有详细的错误消息
        reward_exception = RewardNotFoundException("reward_123")
        recipe_exception = RecipeNotFoundException("recipe_456")
        rewards_exception = InsufficientRewardsException("材料不足")
        points_exception = InsufficientPointsException(100, 25)

        # 验证所有异常都包含有意义的错误信息
        assert len(reward_exception.detail) > 10
        assert len(recipe_exception.detail) > 10
        assert len(rewards_exception.detail) > 10
        assert len(points_exception.detail) > 10


@pytest.mark.parametrize("exception_class,expected_status_code", [
    (RewardNotFoundException, 404),
    (RecipeNotFoundException, 404),
    (InsufficientRewardsException, 400),
    (InsufficientPointsException, 400),
])
def test_exception_status_codes(exception_class, expected_status_code):
    """参数化测试异常状态码"""
    if exception_class == InsufficientPointsException:
        exception = exception_class(100, 50)
    else:
        exception = exception_class("test")
    assert exception.status_code == expected_status_code


@pytest.mark.parametrize("exception_class", [
    RewardNotFoundException,
    RecipeNotFoundException,
    InsufficientRewardsException,
    InsufficientPointsException,
])
def test_exception_inheritance_chain(exception_class):
    """参数化测试异常继承链"""
    if exception_class == InsufficientPointsException:
        exception = exception_class(100, 50)
    else:
        exception = exception_class("test")
    assert isinstance(exception, RewardException)
    assert isinstance(exception, Exception)