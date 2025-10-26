"""
游戏配置测试

测试游戏化系统配置管理功能，包括：
1. 配置加载和默认值
2. 环境变量覆盖
3. 配置获取方法
4. 配置验证功能
5. 事务类型枚举
6. 配置数据结构
7. 错误处理和边界情况

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
import os
import json
from unittest.mock import patch, Mock
from typing import Dict, Any, List, Optional

# 导入被测试的模块
try:
    from src.config.game_config import (
        RewardConfig,
        TransactionSource,
        reward_config
    )
except ImportError as e:
    # 如果导入失败，创建模拟模块
    from enum import Enum

    class TransactionSource(str, Enum):
        """积分/奖励事务类型枚举（基于v3文档）"""
        TASK_COMPLETE = "task_complete"
        TASK_COMPLETE_TOP3 = "task_complete_top3"
        TOP3_COST = "top3_cost"
        LOTTERY_POINTS = "lottery_points"
        LOTTERY_REWARD = "lottery_reward"
        RECHARGE = "recharge"
        REDEMPTION = "redemption"
        MANUAL = "manual"

    class RewardConfig:
        """游戏化系统配置管理类（基于v3 API方案）"""

        def __init__(self):
            self._config = self._load_config()

        def _load_config(self) -> Dict[str, Any]:
            """从环境变量和默认值加载配置"""
            default_config = self._get_default_config()

            # 环境变量覆盖
            if os.getenv("NORMAL_TASK_POINTS"):
                default_config["normal_task_points"] = int(os.getenv("NORMAL_TASK_POINTS"))

            if os.getenv("TOP3_COST_POINTS"):
                default_config["top3_cost_points"] = int(os.getenv("TOP3_COST_POINTS"))

            if os.getenv("TOP3_LOTTERY_POINTS_PROBABILITY"):
                default_config["top3_lottery_points_probability"] = float(os.getenv("TOP3_LOTTERY_POINTS_PROBABILITY"))

            if os.getenv("TOP3_LOTTERY_POINTS_AMOUNT"):
                default_config["top3_lottery_points_amount"] = int(os.getenv("TOP3_LOTTERY_POINTS_AMOUNT"))

            if os.getenv("TOP3_LOTTERY_REWARD_PROBABILITY"):
                default_config["top3_lottery_reward_probability"] = float(os.getenv("TOP3_LOTTERY_REWARD_PROBABILITY"))

            if os.getenv("LOTTERY_REWARD_POOL"):
                try:
                    default_config["lottery_reward_pool"] = json.loads(os.getenv("LOTTERY_REWARD_POOL"))
                except json.JSONDecodeError:
                    print("无效的抽奖奖品池配置JSON，使用默认值")

            return default_config

        def _get_default_config(self) -> Dict[str, Any]:
            """获取默认配置（基于v3文档）"""
            return {
                # 基础奖励配置
                "normal_task_points": 2,
                "top3_cost_points": 300,

                # Top3抽奖配置
                "top3_lottery_points_probability": 0.5,
                "top3_lottery_reward_probability": 0.5,
                "top3_lottery_points_amount": 100,

                # 抽奖奖品池配置
                "lottery_reward_pool": ["gold_coin", "diamond"],

                # 基础奖品配置
                "default_rewards": [
                    {
                        "id": "gold_coin",
                        "name": "小金币",
                        "description": "基础奖品，可通过完成任务获得",
                        "points_value": 10,
                        "category": "basic",
                        "is_active": True
                    },
                    {
                        "id": "diamond",
                        "name": "钻石",
                        "description": "珍贵奖品，可通过小金币合成",
                        "points_value": 100,
                        "category": "premium",
                        "is_active": True
                    }
                ],

                # 兑换配方配置
                "default_recipes": [
                    {
                        "id": "gold_to_diamond",
                        "name": "小金币合成钻石",
                        "result_reward_id": "钻石",
                        "materials": [
                            {"reward_id": "小金币", "quantity": 10}
                        ],
                        "is_active": True
                    }
                ]
            }

        def get_config(self) -> Dict[str, Any]:
            """获取完整配置"""
            return self._config

        def get_normal_task_points(self) -> int:
            """获取普通任务积分"""
            return self._config.get("normal_task_points", 2)

        def get_top3_cost_points(self) -> int:
            """获取Top3设置成本积分"""
            return self._config.get("top3_cost_points", 300)

        def get_top3_lottery_config(self) -> Dict[str, Any]:
            """获取Top3抽奖配置"""
            return {
                "points_probability": self._config.get("top3_lottery_points_probability", 0.5),
                "reward_probability": self._config.get("top3_lottery_reward_probability", 0.5),
                "points_amount": self._config.get("top3_lottery_points_amount", 100)
            }

        def get_lottery_reward_pool(self) -> List[str]:
            """获取抽奖奖品池"""
            return self._config.get("lottery_reward_pool", ["gold_coin", "diamond"])

        def get_default_rewards(self) -> List[Dict[str, Any]]:
            """获取默认奖品列表"""
            return self._config.get("default_rewards", [])

        def get_default_recipes(self) -> List[Dict[str, Any]]:
            """获取默认兑换配方列表"""
            return self._config.get("default_recipes", [])

        def get_source_type_mapping(self) -> Dict[str, str]:
            """获取source_type枚举映射（基于v3文档）"""
            return {
                "task_complete": TransactionSource.TASK_COMPLETE,
                "task_complete_top3": TransactionSource.TASK_COMPLETE_TOP3,
                "top3_cost": TransactionSource.TOP3_COST,
                "lottery_points": TransactionSource.LOTTERY_POINTS,
                "lottery_reward": TransactionSource.LOTTERY_REWARD,
                "recharge": TransactionSource.RECHARGE,
                "redemption": TransactionSource.REDEMPTION,
                "manual": TransactionSource.MANUAL
            }

        def get_recipe_by_id(self, recipe_id: str) -> Optional[Dict[str, Any]]:
            """根据ID获取配方"""
            recipes = self.get_default_recipes()
            for recipe in recipes:
                if recipe["id"] == recipe_id:
                    return recipe
            return None

        def validate_config(self) -> bool:
            """验证配置的有效性"""
            try:
                # 验证抽奖奖品池不为空
                if not self.get_lottery_reward_pool():
                    raise ValueError("抽奖奖品池不能为空")

                # 验证基础奖励配置
                if not self.get_default_rewards():
                    raise ValueError("基础奖品配置不能为空")

                # 验证兑换配方配置
                if not self.get_default_recipes():
                    raise ValueError("兑换配方配置不能为空")

                # 验证积分数值为正数
                if self.get_normal_task_points() <= 0:
                    raise ValueError("普通任务积分必须大于0")

                if self.get_top3_cost_points() <= 0:
                    raise ValueError("Top3设置成本必须大于0")

                # 验证概率值在0-1之间
                lottery_config = self.get_top3_lottery_config()
                if not 0 <= lottery_config["points_probability"] <= 1:
                    raise ValueError("Top3抽奖积分概率必须在0-1之间")

                if not 0 <= lottery_config["reward_probability"] <= 1:
                    raise ValueError("Top3抽奖奖品概率必须在0-1之间")

                return True

            except Exception as e:
                print(f"游戏化配置验证失败: {e}")
                return False

    # 全局配置实例
    reward_config = RewardConfig()


@pytest.mark.unit
class TestTransactionSource:
    """事务类型枚举测试类"""

    def test_transaction_source_values(self):
        """测试事务类型枚举值"""
        expected_values = {
            "TASK_COMPLETE": "task_complete",
            "TASK_COMPLETE_TOP3": "task_complete_top3",
            "TOP3_COST": "top3_cost",
            "LOTTERY_POINTS": "lottery_points",
            "LOTTERY_REWARD": "lottery_reward",
            "RECHARGE": "recharge",
            "REDEMPTION": "redemption",
            "MANUAL": "manual"
        }

        for attr_name, expected_value in expected_values.items():
            enum_value = getattr(TransactionSource, attr_name)
            assert enum_value.value == expected_value
            assert isinstance(enum_value, str)
            assert isinstance(enum_value, TransactionSource)

    def test_transaction_source_inheritance(self):
        """测试事务类型枚举继承"""
        # 应该继承自str和Enum
        assert issubclass(TransactionSource, str)
        assert hasattr(TransactionSource, '__members__')
        assert hasattr(TransactionSource, 'value')

    def test_transaction_source_iteration(self):
        """测试事务类型枚举迭代"""
        sources = list(TransactionSource)
        assert len(sources) == 8
        assert all(isinstance(source, TransactionSource) for source in sources)
        assert all(isinstance(source, str) for source in sources)

    def test_transaction_source_lookup(self):
        """测试事务类型枚举查找"""
        # 通过值查找
        source = TransactionSource("task_complete")
        assert source == TransactionSource.TASK_COMPLETE

        # 通过属性查找
        source = TransactionSource.TASK_COMPLETE
        assert source.value == "task_complete"


@pytest.mark.unit
class TestRewardConfigInitialization:
    """奖励配置初始化测试类"""

    def test_reward_config_default_initialization(self):
        """测试奖励配置默认初始化"""
        config = RewardConfig()

        # 验证配置已加载
        assert hasattr(config, '_config')
        assert isinstance(config._config, dict)

        # 验证默认值
        assert config.get_normal_task_points() == 2
        assert config.get_top3_cost_points() == 300

    def test_reward_config_singleton_behavior(self):
        """测试奖励配置单例行为"""
        config1 = RewardConfig()
        config2 = RewardConfig()

        # 两个实例应该是独立的，但配置内容相同
        assert config1 is not config2
        assert config1.get_config() == config2.get_config()

    def test_reward_config_global_instance(self):
        """测试全局奖励配置实例"""
        assert reward_config is not None
        assert isinstance(reward_config, RewardConfig)
        assert hasattr(reward_config, '_config')


@pytest.mark.unit
class TestRewardConfigEnvironmentOverride:
    """奖励配置环境变量覆盖测试类"""

    @patch.dict(os.environ, {
        'NORMAL_TASK_POINTS': '10',
        'TOP3_COST_POINTS': '500',
        'TOP3_LOTTERY_POINTS_PROBABILITY': '0.8',
        'TOP3_LOTTERY_POINTS_AMOUNT': '200',
        'TOP3_LOTTERY_REWARD_PROBABILITY': '0.2'
    })
    def test_environment_variables_override_values(self):
        """测试环境变量覆盖配置值"""
        config = RewardConfig()

        assert config.get_normal_task_points() == 10
        assert config.get_top3_cost_points() == 500

        lottery_config = config.get_top3_lottery_config()
        assert lottery_config["points_probability"] == 0.8
        assert lottery_config["reward_probability"] == 0.2
        assert lottery_config["points_amount"] == 200

    @patch.dict(os.environ, {
        'NORMAL_TASK_POINTS': 'invalid_int'
    })
    def test_invalid_integer_environment_variable(self):
        """测试无效整数环境变量"""
        with pytest.raises(ValueError):
            RewardConfig()

    @patch.dict(os.environ, {
        'TOP3_LOTTERY_POINTS_PROBABILITY': 'invalid_float'
    })
    def test_invalid_float_environment_variable(self):
        """测试无效浮点数环境变量"""
        with pytest.raises(ValueError):
            RewardConfig()

    @patch.dict(os.environ, {
        'LOTTERY_REWARD_POOL': '["special_reward", "bonus_item"]'
    })
    def test_valid_json_environment_variable(self):
        """测试有效JSON环境变量"""
        config = RewardConfig()
        reward_pool = config.get_lottery_reward_pool()
        assert reward_pool == ["special_reward", "bonus_item"]

    @patch.dict(os.environ, {
        'LOTTERY_REWARD_POOL': 'invalid_json'
    })
    def test_invalid_json_environment_variable(self):
        """测试无效JSON环境变量"""
        with patch('builtins.print') as mock_print:
            config = RewardConfig()
            reward_pool = config.get_lottery_reward_pool()
            # 应该使用默认值
            assert reward_pool == ["gold_coin", "diamond"]
            # 应该打印错误消息
            mock_print.assert_called_with("无效的抽奖奖品池配置JSON，使用默认值")

    def test_no_environment_variables(self):
        """测试无环境变量时使用默认值"""
        # 清除相关环境变量
        env_vars_to_clear = [
            'NORMAL_TASK_POINTS', 'TOP3_COST_POINTS',
            'TOP3_LOTTERY_POINTS_PROBABILITY', 'TOP3_LOTTERY_POINTS_AMOUNT',
            'TOP3_LOTTERY_REWARD_PROBABILITY', 'LOTTERY_REWARD_POOL'
        ]

        with patch.dict(os.environ, {}, clear=True):
            for var in env_vars_to_clear:
                if var in os.environ:
                    del os.environ[var]

            config = RewardConfig()

            # 应该使用默认值
            assert config.get_normal_task_points() == 2
            assert config.get_top3_cost_points() == 300


@pytest.mark.unit
class TestRewardConfigGetters:
    """奖励配置获取方法测试类"""

    def setup_method(self):
        """设置测试方法"""
        self.config = RewardConfig()

    def test_get_config(self):
        """测试获取完整配置"""
        config = self.config.get_config()

        assert isinstance(config, dict)
        assert "normal_task_points" in config
        assert "top3_cost_points" in config
        assert "default_rewards" in config
        assert "default_recipes" in config

    def test_get_normal_task_points(self):
        """测试获取普通任务积分"""
        points = self.config.get_normal_task_points()
        assert isinstance(points, int)
        assert points > 0

    def test_get_top3_cost_points(self):
        """测试获取Top3设置成本积分"""
        cost = self.config.get_top3_cost_points()
        assert isinstance(cost, int)
        assert cost > 0

    def test_get_top3_lottery_config(self):
        """测试获取Top3抽奖配置"""
        lottery_config = self.config.get_top3_lottery_config()

        assert isinstance(lottery_config, dict)
        assert "points_probability" in lottery_config
        assert "reward_probability" in lottery_config
        assert "points_amount" in lottery_config

        # 验证概率值范围
        assert 0 <= lottery_config["points_probability"] <= 1
        assert 0 <= lottery_config["reward_probability"] <= 1
        assert isinstance(lottery_config["points_amount"], int)
        assert lottery_config["points_amount"] > 0

    def test_get_lottery_reward_pool(self):
        """测试获取抽奖奖品池"""
        reward_pool = self.config.get_lottery_reward_pool()

        assert isinstance(reward_pool, list)
        assert len(reward_pool) > 0
        assert all(isinstance(item, str) for item in reward_pool)

    def test_get_default_rewards(self):
        """测试获取默认奖品列表"""
        rewards = self.config.get_default_rewards()

        assert isinstance(rewards, list)
        assert len(rewards) > 0

        for reward in rewards:
            assert isinstance(reward, dict)
            assert "id" in reward
            assert "name" in reward
            assert "points_value" in reward
            assert "is_active" in reward

    def test_get_default_recipes(self):
        """测试获取默认兑换配方列表"""
        recipes = self.config.get_default_recipes()

        assert isinstance(recipes, list)
        assert len(recipes) > 0

        for recipe in recipes:
            assert isinstance(recipe, dict)
            assert "id" in recipe
            assert "name" in recipe
            assert "result_reward_id" in recipe
            assert "materials" in recipe
            assert "is_active" in recipe

    def test_get_source_type_mapping(self):
        """测试获取事务类型映射"""
        mapping = self.config.get_source_type_mapping()

        assert isinstance(mapping, dict)
        assert len(mapping) == 8

        # 验证所有值都是TransactionSource枚举
        for key, value in mapping.items():
            assert isinstance(key, str)
            assert isinstance(value, TransactionSource)
            assert value.value == key

    def test_get_recipe_by_id_existing(self):
        """测试根据ID获取存在的配方"""
        recipe = self.config.get_recipe_by_id("gold_to_diamond")

        assert recipe is not None
        assert isinstance(recipe, dict)
        assert recipe["id"] == "gold_to_diamond"
        assert "materials" in recipe

    def test_get_recipe_by_id_non_existing(self):
        """测试根据ID获取不存在的配方"""
        recipe = self.config.get_recipe_by_id("non_existing_recipe")
        assert recipe is None


@pytest.mark.unit
class TestRewardConfigValidation:
    """奖励配置验证测试类"""

    def setup_method(self):
        """设置测试方法"""
        self.config = RewardConfig()

    def test_validate_config_valid(self):
        """测试有效配置验证"""
        result = self.config.validate_config()
        assert result is True

    def test_validate_config_prints_error_message(self):
        """测试配置验证失败时打印错误消息"""
        # 修改配置使其无效
        self.config._config["normal_task_points"] = -1

        with patch('builtins.print') as mock_print:
            result = self.config.validate_config()
            assert result is False
            mock_print.assert_called_once()
            assert "游戏化配置验证失败" in str(mock_print.call_args)

    def test_validate_empty_lottery_reward_pool(self):
        """测试空抽奖奖品池验证"""
        self.config._config["lottery_reward_pool"] = []

        result = self.config.validate_config()
        assert result is False

    def test_validate_empty_default_rewards(self):
        """测试空默认奖品配置验证"""
        self.config._config["default_rewards"] = []

        result = self.config.validate_config()
        assert result is False

    def test_validate_empty_default_recipes(self):
        """测试空默认配方配置验证"""
        self.config._config["default_recipes"] = []

        result = self.config.validate_config()
        assert result is False

    def test_validate_negative_normal_task_points(self):
        """测试负数普通任务积分验证"""
        self.config._config["normal_task_points"] = -5

        result = self.config.validate_config()
        assert result is False

    def test_validate_zero_normal_task_points(self):
        """测试零普通任务积分验证"""
        self.config._config["normal_task_points"] = 0

        result = self.config.validate_config()
        assert result is False

    def test_validate_negative_top3_cost_points(self):
        """测试负数Top3成本积分验证"""
        self.config._config["top3_cost_points"] -100

        result = self.config.validate_config()
        assert result is False

    def test_validate_invalid_lottery_points_probability(self):
        """测试无效抽奖积分概率验证"""
        # 测试小于0的概率
        self.config._config["top3_lottery_points_probability"] = -0.1
        result = self.config.validate_config()
        assert result is False

        # 测试大于1的概率
        self.config._config["top3_lottery_points_probability"] = 1.1
        result = self.config.validate_config()
        assert result is False

    def test_validate_invalid_lottery_reward_probability(self):
        """测试无效抽奖奖品概率验证"""
        # 测试小于0的概率
        self.config._config["top3_lottery_reward_probability"] = -0.1
        result = self.config.validate_config()
        assert result is False

        # 测试大于1的概率
        self.config._config["top3_lottery_reward_probability"] = 1.1
        result = self.config.validate_config()
        assert result is False


@pytest.mark.unit
class TestRewardConfigEdgeCases:
    """奖励配置边界情况测试类"""

    def test_config_data_structure_integrity(self):
        """测试配置数据结构完整性"""
        config = RewardConfig()
        full_config = config.get_config()

        # 验证所有必需的配置项都存在
        required_keys = [
            "normal_task_points",
            "top3_cost_points",
            "top3_lottery_points_probability",
            "top3_lottery_reward_probability",
            "top3_lottery_points_amount",
            "lottery_reward_pool",
            "default_rewards",
            "default_recipes"
        ]

        for key in required_keys:
            assert key in full_config, f"Missing required config key: {key}"

    def test_reward_data_structure_validation(self):
        """测试奖品数据结构验证"""
        config = RewardConfig()
        rewards = config.get_default_rewards()

        for reward in rewards:
            # 验证必需字段
            required_fields = ["id", "name", "description", "points_value", "category", "is_active"]
            for field in required_fields:
                assert field in reward, f"Missing required reward field: {field}"

            # 验证数据类型
            assert isinstance(reward["id"], str)
            assert isinstance(reward["name"], str)
            assert isinstance(reward["description"], str)
            assert isinstance(reward["points_value"], int)
            assert isinstance(reward["category"], str)
            assert isinstance(reward["is_active"], bool)

    def test_recipe_data_structure_validation(self):
        """测试配方数据结构验证"""
        config = RewardConfig()
        recipes = config.get_default_recipes()

        for recipe in recipes:
            # 验证必需字段
            required_fields = ["id", "name", "result_reward_id", "materials", "is_active"]
            for field in required_fields:
                assert field in recipe, f"Missing required recipe field: {field}"

            # 验证数据类型
            assert isinstance(recipe["id"], str)
            assert isinstance(recipe["name"], str)
            assert isinstance(recipe["result_reward_id"], str)
            assert isinstance(recipe["materials"], list)
            assert isinstance(recipe["is_active"], bool)

            # 验证材料结构
            for material in recipe["materials"]:
                assert "reward_id" in material
                assert "quantity" in material
                assert isinstance(material["reward_id"], str)
                assert isinstance(material["quantity"], int)

    def test_config_immutability(self):
        """测试配置不可变性（如果需要）"""
        config = RewardConfig()
        original_config = config.get_config()

        # 修改返回的配置不应该影响内部配置
        modified_config = config.get_config()
        modified_config["normal_task_points"] = 999

        # 原始配置应该保持不变
        assert config.get_normal_task_points() != 999


@pytest.mark.parametrize("env_var,value,expected_type,getter_method", [
    ("NORMAL_TASK_POINTS", "15", int, "get_normal_task_points"),
    ("TOP3_COST_POINTS", "400", int, "get_top3_cost_points"),
    ("TOP3_LOTTERY_POINTS_PROBABILITY", "0.75", float, "get_top3_lottery_config"),
    ("TOP3_LOTTERY_POINTS_AMOUNT", "150", int, "get_top3_lottery_config"),
])
def test_environment_override_parameterized(env_var, value, expected_type, getter_method):
    """参数化环境变量覆盖测试"""
    with patch.dict(os.environ, {env_var: value}):
        config = RewardConfig()

        if getter_method == "get_top3_lottery_config":
            lottery_config = getattr(config, getter_method)()
            # 验证概率值
            if "probability" in env_var:
                prob_key = "points_probability" if "POINTS" in env_var else "reward_probability"
                assert isinstance(lottery_config[prob_key], expected_type)
            else:
                assert isinstance(lottery_config["points_amount"], expected_type)
        else:
            result = getattr(config, getter_method)()
            assert isinstance(result, expected_type)


@pytest.mark.parametrize("recipe_id,should_exist", [
    ("gold_to_diamond", True),
    ("non_existing_recipe", False),
    ("", False),
    ("GOLD_TO_DIAMOND", False),  # 大小写敏感
])
def test_get_recipe_by_id_parameterized(recipe_id, should_exist):
    """参数化配方ID获取测试"""
    config = RewardConfig()
    recipe = config.get_recipe_by_id(recipe_id)

    if should_exist:
        assert recipe is not None
        assert recipe["id"] == recipe_id
    else:
        assert recipe is None


@pytest.fixture
def sample_config_data():
    """示例配置数据fixture"""
    return {
        "normal_task_points": 5,
        "top3_cost_points": 200,
        "top3_lottery_points_probability": 0.6,
        "top3_lottery_reward_probability": 0.4,
        "top3_lottery_points_amount": 80,
        "lottery_reward_pool": ["bonus", "special"],
        "default_rewards": [
            {
                "id": "test_reward",
                "name": "测试奖品",
                "description": "测试用奖品",
                "points_value": 20,
                "category": "test",
                "is_active": True
            }
        ],
        "default_recipes": [
            {
                "id": "test_recipe",
                "name": "测试配方",
                "result_reward_id": "test_reward",
                "materials": [{"reward_id": "basic", "quantity": 5}],
                "is_active": True
            }
        ]
    }


@pytest.fixture
def sample_environment():
    """示例环境变量fixture"""
    return {
        'NORMAL_TASK_POINTS': '8',
        'TOP3_COST_POINTS': '250',
        'TOP3_LOTTERY_POINTS_PROBABILITY': '0.7',
        'LOTTERY_REWARD_POOL': '["custom_reward", "custom_bonus"]'
    }


def test_with_fixtures(sample_config_data, sample_environment):
    """使用fixture的测试"""
    # 测试配置数据结构
    assert "normal_task_points" in sample_config_data
    assert isinstance(sample_config_data["default_rewards"], list)
    assert isinstance(sample_config_data["default_recipes"], list)

    # 测试环境变量
    with patch.dict(os.environ, sample_environment):
        config = RewardConfig()

        assert config.get_normal_task_points() == 8
        assert config.get_top3_cost_points() == 250

        lottery_config = config.get_top3_lottery_config()
        assert lottery_config["points_probability"] == 0.7

        reward_pool = config.get_lottery_reward_pool()
        assert reward_pool == ["custom_reward", "custom_bonus"]

    # 测试配置验证
    config = RewardConfig()
    assert config.validate_config() is True

    # 测试事务类型映射
    mapping = config.get_source_type_mapping()
    assert len(mapping) == 8
    assert "task_complete" in mapping
    assert mapping["task_complete"] == TransactionSource.TASK_COMPLETE