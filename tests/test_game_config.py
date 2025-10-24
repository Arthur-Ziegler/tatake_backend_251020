"""
游戏化系统配置测试

测试游戏化配置模块的功能，包括：
- 配置加载
- 奖品配置
- 兑换配方配置
- 抽奖奖品池配置
- 配置验证

作者：TaTakeKe团队
版本：v1.0（Day3实施）
"""

import pytest
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.game_config import RewardConfig, TransactionSource


class TestGameConfig:
    """游戏化配置测试类"""

    def setup_method(self):
        """测试前置设置"""
        # 设置环境变量
        os.environ["NORMAL_TASK_POINTS"] = "5"
        os.environ["TOP3_COST_POINTS"] = "400"
        os.environ["LOTTERY_REWARD_POOL"] = '["gold_coin", "diamond", "chest"]'

    def teardown_method(self):
        """测试后置清理"""
        # 清理环境变量
        env_vars_to_clear = [
            "NORMAL_TASK_POINTS",
            "TOP3_COST_POINTS",
            "LOTTERY_REWARD_POOL"
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]

    def test_config_loading(self):
        """测试配置加载"""
        config = RewardConfig()
        assert config is not None
        assert isinstance(config.get_config(), dict)

    def test_environment_variable_override(self):
        """测试环境变量覆盖"""
        config = RewardConfig()

        # 验证环境变量是否正确覆盖了默认值
        assert config.get_normal_task_points() == 5
        assert config.get_top3_cost_points() == 400
        assert "chest" in config.get_lottery_reward_pool()

    def test_default_values(self):
        """测试默认配置值"""
        # 清理环境变量以使用默认值
        for var in ["NORMAL_TASK_POINTS", "TOP3_COST_POINTS", "LOTTERY_REWARD_POOL"]:
            if var in os.environ:
                del os.environ[var]

        config = RewardConfig()

        # 验证默认值
        assert config.get_normal_task_points() == 2
        assert config.get_top3_cost_points() == 300
        assert config.get_lottery_reward_pool() == ["gold_coin", "diamond"]

    def test_lottery_config(self):
        """测试抽奖配置"""
        config = RewardConfig()
        lottery_config = config.get_top3_lottery_config()

        assert isinstance(lottery_config, dict)
        assert "points_probability" in lottery_config
        assert "reward_probability" in lottery_config
        assert "points_amount" in lottery_config
        assert lottery_config["points_amount"] == 100
        assert lottery_config["points_probability"] == 0.5
        assert lottery_config["reward_probability"] == 0.5

    def test_default_rewards(self):
        """测试默认奖品配置"""
        config = RewardConfig()
        rewards = config.get_default_rewards()

        assert isinstance(rewards, list)
        assert len(rewards) >= 2

        # 验证小金币配置
        gold_coin = next((r for r in rewards if r["id"] == "gold_coin"), None)
        assert gold_coin is not None
        assert gold_coin["name"] == "小金币"
        assert gold_coin["points_value"] == 10
        assert gold_coin["category"] == "basic"
        assert gold_coin["is_active"] is True

        # 验证钻石配置
        diamond = next((r for r in rewards if r["id"] == "diamond"), None)
        assert diamond is not None
        assert diamond["name"] == "钻石"
        assert diamond["points_value"] == 100
        assert diamond["category"] == "premium"
        assert diamond["is_active"] is True

    def test_default_recipes(self):
        """测试默认兑换配方配置"""
        config = RewardConfig()
        recipes = config.get_default_recipes()

        assert isinstance(recipes, list)
        assert len(recipes) >= 1

        # 验证金币兑换钻石配方
        recipe = next((r for r in recipes if r["id"] == "gold_to_diamond"), None)
        assert recipe is not None
        assert recipe["name"] == "小金币合成钻石"
        assert recipe["result_reward_id"] == "diamond"
        assert "materials" in recipe
        assert isinstance(recipe["materials"], list)
        assert len(recipe["materials"]) >= 1

        # 验证材料配置
        material = recipe["materials"][0]
        assert material["reward_id"] == "gold_coin"
        assert material["quantity"] == 10

    def test_source_type_mapping(self):
        """测试source_type枚举映射"""
        config = RewardConfig()
        mapping = config.get_source_type_mapping()

        assert isinstance(mapping, dict)
        assert "task_complete" in mapping
        assert "task_complete_top3" in mapping
        assert "top3_cost" in mapping
        assert "lottery_points" in mapping
        assert "recharge" in mapping
        assert "redemption" in mapping
        assert "manual" in mapping

        # 验证映射到正确的枚举值
        assert mapping["task_complete"] == TransactionSource.TASK_COMPLETE
        assert mapping["task_complete_top3"] == TransactionSource.TASK_COMPLETE_TOP3

    def test_recipe_by_id(self):
        """测试根据ID获取配方"""
        config = RewardConfig()

        # 测试存在的配方
        recipe = config.get_recipe_by_id("gold_to_diamond")
        assert recipe is not None
        assert recipe["id"] == "gold_to_diamond"

        # 测试不存在的配方
        recipe = config.get_recipe_by_id("non_existent")
        assert recipe is None

    def test_config_validation_success(self):
        """测试配置验证成功"""
        config = RewardConfig()
        assert config.validate_config() is True

    def test_config_validation_failure(self):
        """测试配置验证失败"""
        from config.game_config import RewardConfig

        # 临时修改配置以测试验证失败
        original_method = RewardConfig.validate_config

        def mock_validate_config(self):
            return False

        # 临时替换验证方法
        RewardConfig.validate_config = mock_validate_config

        try:
            config = RewardConfig()
            assert config.validate_config() is False
        finally:
            # 恢复原始方法
            RewardConfig.validate_config = original_method


class TestTransactionSource:
    """事务源枚举测试类"""

    def test_transaction_source_values(self):
        """测试事务源枚举值"""
        assert TransactionSource.TASK_COMPLETE == "task_complete"
        assert TransactionSource.TASK_COMPLETE_TOP3 == "task_complete_top3"
        assert TransactionSource.TOP3_COST == "top3_cost"
        assert TransactionSource.LOTTERY_POINTS == "lottery_points"
        assert TransactionSource.RECHARGE == "recharge"
        assert TransactionSource.REDEMPTION == "redemption"
        assert TransactionSource.MANUAL == "manual"

    def test_transaction_source_is_enum(self):
        """测试事务源是枚举类型"""
        assert hasattr(TransactionSource, '__members__')
        assert len(list(TransactionSource)) >= 7


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])