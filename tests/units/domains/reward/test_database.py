"""
Reward领域数据库模块测试

测试Reward领域的数据库功能，包括：
1. 数据库初始化功能
2. 奖品和配方数据创建
3. 幂等性操作验证
4. 数据查询和验证
5. 事务管理和错误处理
6. 配置数据集成

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from sqlmodel import Session, create_engine, select
from sqlmodel.pool import StaticPool
from uuid import uuid4

from src.domains.reward.database import (
    initialize_reward_database,
    _initialize_rewards,
    _initialize_recipes,
    verify_initialization,
    get_reward_by_name,
    get_reward_session
)
from src.domains.reward.models import Reward, RewardRecipe


@pytest.mark.unit
class TestInitializeRewardDatabase:
    """奖励数据库初始化测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """为测试设置内存数据库"""
        # 设置内存数据库URL
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"

        yield

        # 测试结束后清理
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

    @patch('src.domains.reward.database.RewardConfig')
    def test_initialize_reward_database_success(self, mock_config_class, mock_session):
        """测试成功初始化奖励数据库"""
        # 模拟配置
        mock_config = Mock()
        mock_config.get_default_rewards.return_value = [
            {
                "name": "test_reward",
                "description": "测试奖品",
                "points_value": 100,
                "category": "test",
                "is_active": True
            }
        ]
        mock_config.get_default_recipes.return_value = []
        mock_config_class.return_value = mock_config

        # 模拟数据库查询无已存在记录
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # 执行初始化
        initialize_reward_database(mock_session)

        # 验证事务被提交
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    @patch('src.domains.reward.database.RewardConfig')
    def test_initialize_reward_database_with_exception(self, mock_config_class, mock_session):
        """测试初始化时处理异常"""
        # 模拟配置抛出异常
        mock_config_class.side_effect = Exception("配置错误")

        # 执行初始化应该抛出异常
        with pytest.raises(Exception) as exc_info:
            initialize_reward_database(mock_session)

        assert "配置错误" in str(exc_info.value)
        # 验证事务被回滚
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    @patch('src.domains.reward.database.logger')
    def test_initialize_logging(self, mock_logger, mock_session):
        """测试初始化日志记录"""
        with patch('src.domains.reward.database.RewardConfig') as mock_config_class:
            mock_config = Mock()
            mock_config.get_default_rewards.return_value = []
            mock_config.get_default_recipes.return_value = []
            mock_config_class.return_value = mock_config

            # 模拟数据库查询无已存在记录
            mock_session.execute.return_value.scalar_one_or_none.return_value = None

            initialize_reward_database(mock_session)

            # 验证日志被正确记录
            mock_logger.info.assert_called()
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            assert any("开始初始化奖励系统数据库" in call for call in log_calls)
            assert any("奖励系统数据库初始化完成" in call for call in log_calls)


@pytest.mark.unit
class TestInitializeRewards:
    """奖品初始化测试类"""

    @patch('src.domains.reward.database.RewardConfig')
    def test_initialize_rewards_new(self, mock_config_class, mock_session):
        """测试初始化新奖品"""
        # 模拟配置
        mock_config = Mock()
        mock_config.get_default_rewards.return_value = [
            {
                "name": "gold_coin",
                "description": "小金币",
                "points_value": 50,
                "category": "currency",
                "is_active": True
            }
        ]
        mock_config_class.return_value = mock_config

        # 模拟数据库查询无已存在记录
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        _initialize_rewards(mock_session, mock_config)

        # 验证奖品被创建
        mock_session.add.assert_called_once()
        added_reward = mock_session.add.call_args[0][0]
        assert added_reward.name == "gold_coin"
        assert added_reward.description == "小金币"
        assert added_reward.points_value == 50

    @patch('src.domains.reward.database.RewardConfig')
    def test_initialize_rewards_existing(self, mock_config_class, mock_session):
        """测试初始化已存在的奖品"""
        # 模拟配置
        mock_config = Mock()
        mock_config.get_default_rewards.return_value = [
            {
                "name": "existing_reward",
                "description": "已存在奖品",
                "points_value": 100,
                "category": "test",
                "is_active": True
            }
        ]
        mock_config_class.return_value = mock_config

        # 模拟数据库查询返回已存在记录
        existing_reward = Mock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_reward

        _initialize_rewards(mock_session, mock_config)

        # 验证奖品不会被重复创建
        mock_session.add.assert_not_called()

    @patch('src.domains.reward.database.RewardConfig')
    def test_initialize_rewards_multiple(self, mock_config_class, mock_session):
        """测试初始化多个奖品"""
        # 模拟配置
        mock_config = Mock()
        mock_config.get_default_rewards.return_value = [
            {
                "name": "reward_1",
                "description": "奖品1",
                "points_value": 50,
                "category": "test",
                "is_active": True
            },
            {
                "name": "reward_2",
                "description": "奖品2",
                "points_value": 100,
                "category": "test",
                "is_active": True
            }
        ]
        mock_config_class.return_value = mock_config

        # 模拟数据库查询无已存在记录
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        _initialize_rewards(mock_session, mock_config)

        # 验证两个奖品都被创建
        assert mock_session.add.call_count == 2


@pytest.mark.unit
class TestInitializeRecipes:
    """配方初始化测试类"""

    @patch('src.domains.reward.database.RewardConfig')
    def test_initialize_recipes_new(self, mock_config_class, mock_session):
        """测试初始化新配方"""
        # 模拟配置
        mock_config = Mock()
        mock_config.get_default_recipes.return_value = [
            {
                "name": "test_recipe",
                "result_reward_id": "gold_coin",
                "materials": ["material_1", "material_2"],
                "is_active": True
            }
        ]
        mock_config_class.return_value = mock_config

        # 模拟数据库查询
        def mock_execute_side_effect(query):
            result = Mock()
            if "RewardRecipe" in str(query):
                result.scalar_one_or_none.return_value = None  # 配方不存在
            else:  # Reward查询
                reward = Mock()
                reward.id = str(uuid4())
                reward.name = "gold_coin"
                result.scalar_one_or_none.return_value = reward
            return result

        mock_session.execute.side_effect = mock_execute_side_effect

        _initialize_recipes(mock_session, mock_config)

        # 验证配方被创建
        mock_session.add.assert_called_once()
        added_recipe = mock_session.add.call_args[0][0]
        assert added_recipe.name == "test_recipe"
        assert added_recipe.materials == ["material_1", "material_2"]

    @patch('src.domains.reward.database.RewardConfig')
    def test_initialize_recipes_existing(self, mock_config_class, mock_session):
        """测试初始化已存在的配方"""
        # 模拟配置
        mock_config = Mock()
        mock_config.get_default_recipes.return_value = [
            {
                "name": "existing_recipe",
                "result_reward_id": "gold_coin",
                "materials": ["material_1"],
                "is_active": True
            }
        ]
        mock_config_class.return_value = mock_config

        # 模拟数据库查询返回已存在记录
        existing_recipe = Mock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_recipe

        _initialize_recipes(mock_session, mock_config)

        # 验证配方不会被重复创建
        mock_session.add.assert_not_called()

    @patch('src.domains.reward.database.RewardConfig')
    @patch('src.domains.reward.database.logger')
    def test_initialize_recipes_missing_reward(self, mock_logger, mock_config_class, mock_session):
        """测试初始化配方时目标奖品不存在"""
        # 模拟配置
        mock_config = Mock()
        mock_config.get_default_recipes.return_value = [
            {
                "name": "invalid_recipe",
                "result_reward_id": "nonexistent_reward",
                "materials": ["material_1"],
                "is_active": True
            }
        ]
        mock_config_class.return_value = mock_config

        # 模拟数据库查询
        def mock_execute_side_effect(query):
            result = Mock()
            if "RewardRecipe" in str(query):
                result.scalar_one_or_none.return_value = None  # 配方不存在
            else:  # Reward查询
                result.scalar_one_or_none.return_value = None  # 奖品不存在
            return result

        mock_session.execute.side_effect = mock_execute_side_effect

        _initialize_recipes(mock_session, mock_config)

        # 验证配方不会被创建，且记录错误日志
        mock_session.add.assert_not_called()
        mock_logger.error.assert_called_once()
        assert "配方目标奖品不存在" in mock_logger.error.call_args[0][0]


@pytest.mark.unit
class TestVerifyInitialization:
    """初始化验证测试类"""

    def test_verify_initialization(self, mock_session):
        """测试验证初始化结果"""
        # 模拟数据库查询结果
        def mock_execute_side_effect(query):
            result = Mock()
            if "Reward" in str(query) and "RewardRecipe" not in str(query):
                result.count.return_value = 5  # 5个奖品
            else:
                result.count.return_value = 3  # 3个配方
            return result

        mock_session.execute.side_effect = mock_execute_side_effect

        result = verify_initialization(mock_session)

        assert result["rewards"] == 5
        assert result["recipes"] == 3
        assert len(result) == 2


@pytest.mark.unit
class TestGetRewardByName:
    """根据名称查询奖品测试类"""

    def test_get_reward_by_name_success(self, mock_session):
        """测试成功查询奖品"""
        # 模拟奖品
        reward = Mock()
        reward.name = "test_reward"
        reward.id = str(uuid4())

        mock_session.execute.return_value.scalar_one_or_none.return_value = reward

        result = get_reward_by_name(mock_session, "test_reward")

        assert result == reward
        assert result.name == "test_reward"

    def test_get_reward_by_name_not_found(self, mock_session):
        """测试查询不存在的奖品"""
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(ValueError) as exc_info:
            get_reward_by_name(mock_session, "nonexistent_reward")

        assert "奖品不存在: nonexistent_reward" in str(exc_info.value)

    def test_get_reward_by_name_empty_name(self, mock_session):
        """测试查询空名称奖品"""
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(ValueError) as exc_info:
            get_reward_by_name(mock_session, "")

        assert "奖品不存在" in str(exc_info.value)


@pytest.mark.unit
class TestGetRewardSession:
    """获取奖励会话测试类"""

    @patch('src.domains.reward.database.get_db_session')
    def test_get_reward_session(self, mock_get_db_session):
        """测试获取奖励会话"""
        mock_session_gen = iter([Mock()])
        mock_get_db_session.return_value = mock_session_gen

        result = get_reward_session()

        assert result == mock_session_gen
        mock_get_db_session.assert_called_once()


@pytest.mark.integration
class TestRewardDatabaseIntegration:
    """奖励数据库集成测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """为测试设置内存数据库"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        # 创建表
        Reward.metadata.create_all(engine)
        RewardRecipe.metadata.create_all(engine)

        yield engine

    def test_complete_initialization_workflow(self):
        """测试完整初始化工作流程"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        # 创建表
        Reward.metadata.create_all(engine)
        RewardRecipe.metadata.create_all(engine)

        with Session(engine) as session:
            # 模拟配置数据
            with patch('src.domains.reward.database.RewardConfig') as mock_config_class:
                mock_config = Mock()
                mock_config.get_default_rewards.return_value = [
                    {
                        "name": "test_coin",
                        "description": "测试金币",
                        "points_value": 50,
                        "category": "currency",
                        "is_active": True
                    }
                ]
                mock_config.get_default_recipes.return_value = [
                    {
                        "name": "coin_recipe",
                        "result_reward_id": "test_coin",
                        "materials": ["base_material"],
                        "is_active": True
                    }
                ]
                mock_config_class.return_value = mock_config

                # 执行初始化
                initialize_reward_database(session)

                # 验证数据被创建
                rewards = session.exec(select(Reward)).all()
                recipes = session.exec(select(RewardRecipe)).all()

                assert len(rewards) == 1
                assert len(recipes) == 1
                assert rewards[0].name == "test_coin"
                assert recipes[0].name == "coin_recipe"

    def test_idempotent_initialization(self):
        """测试初始化幂等性"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        # 创建表
        Reward.metadata.create_all(engine)
        RewardRecipe.metadata.create_all(engine)

        with Session(engine) as session:
            with patch('src.domains.reward.database.RewardConfig') as mock_config_class:
                mock_config = Mock()
                mock_config.get_default_rewards.return_value = [
                    {
                        "name": "idempotent_reward",
                        "description": "幂等测试奖品",
                        "points_value": 100,
                        "category": "test",
                        "is_active": True
                    }
                ]
                mock_config.get_default_recipes.return_value = []
                mock_config_class.return_value = mock_config

                # 第一次初始化
                initialize_reward_database(session)
                rewards_first = session.exec(select(Reward)).all()

                # 第二次初始化
                initialize_reward_database(session)
                rewards_second = session.exec(select(Reward)).all()

                # 验证数据没有重复创建
                assert len(rewards_first) == 1
                assert len(rewards_second) == 1
                assert rewards_first[0].id == rewards_second[0].id

    def test_transaction_rollback_on_error(self):
        """测试错误时事务回滚"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        # 创建表
        Reward.metadata.create_all(engine)
        RewardRecipe.metadata.create_all(engine)

        with Session(engine) as session:
            with patch('src.domains.reward.database.RewardConfig') as mock_config_class:
                # 模拟配置错误
                mock_config_class.side_effect = Exception("配置加载失败")

                # 初始化应该失败并回滚
                with pytest.raises(Exception):
                    initialize_reward_database(session)

                # 验证没有数据被创建
                rewards = session.exec(select(Reward)).all()
                recipes = session.exec(select(RewardRecipe)).all()

                assert len(rewards) == 0
                assert len(recipes) == 0


@pytest.mark.unit
class TestRewardDatabaseEdgeCases:
    """奖励数据库边界条件测试"""

    @patch('src.domains.reward.database.RewardConfig')
    def test_empty_configuration(self, mock_config_class, mock_session):
        """测试空配置初始化"""
        mock_config = Mock()
        mock_config.get_default_rewards.return_value = []
        mock_config.get_default_recipes.return_value = []
        mock_config_class.return_value = mock_config

        # 应该能正常处理空配置
        initialize_reward_database(mock_session)
        mock_session.commit.assert_called_once()

    def test_database_session_error_handling(self, mock_session):
        """测试数据库会话错误处理"""
        mock_session.execute.side_effect = Exception("数据库连接错误")

        with patch('src.domains.reward.database.RewardConfig') as mock_config_class:
            mock_config = Mock()
            mock_config.get_default_rewards.return_value = []
            mock_config.get_default_recipes.return_value = []
            mock_config_class.return_value = mock_config

            with pytest.raises(Exception) as exc_info:
                initialize_reward_database(mock_session)

            assert "数据库连接错误" in str(exc_info.value)
            mock_session.rollback.assert_called_once()


@pytest.mark.parametrize("reward_data", [
    {
        "name": "simple_reward",
        "description": "简单奖品",
        "points_value": 10,
        "category": "basic",
        "is_active": True
    },
    {
        "name": "complex_reward",
        "description": "复杂奖品描述",
        "points_value": 1000,
        "category": "premium",
        "is_active": False
    }
])
def test_reward_data_variations(reward_data):
    """参数化测试不同奖品数据"""
    with patch('src.domains.reward.database.RewardConfig') as mock_config_class:
        mock_config = Mock()
        mock_config.get_default_rewards.return_value = [reward_data]
        mock_config.get_default_recipes.return_value = []
        mock_config_class.return_value = mock_config

        mock_session = Mock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        _initialize_rewards(mock_session, mock_config)

        # 验证奖品被正确创建
        mock_session.add.assert_called_once()
        added_reward = mock_session.add.call_args[0][0]
        assert added_reward.name == reward_data["name"]
        assert added_reward.points_value == reward_data["points_value"]