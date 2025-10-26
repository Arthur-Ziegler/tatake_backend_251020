"""
系统启动集成测试

测试整个系统的启动流程，确保所有模块正常初始化：
1. 数据库连接和表结构
2. 奖励系统初始化
3. API服务启动
4. 配置加载和验证

这个测试用于发现类似 get_default_rewards 这样的启动时错误。

作者：TaKeKe团队
版本：v4.0 - 启动流程验证
"""

import pytest
import os
import sys
from unittest.mock import patch
from io import StringIO

from src.database import get_engine, get_session
from src.domains.reward.database import initialize_reward_database
from src.config.game_config import RewardConfig
from src.domains.task.database import initialize_task_database
from src.domains.chat.database import initialize_chat_database
from src.domains.focus.database import initialize_focus_database
from src.domains.auth.database import initialize_auth_database


@pytest.mark.integration
class TestSystemStartup:
    """系统启动集成测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """设置测试环境变量"""
        # 设置测试数据库
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"

        # 设置其他必要的环境变量
        os.environ["DEBUG"] = "false"

        yield

        # 清理环境变量
        for key in ["DATABASE_URL", "DEBUG"]:
            if key in os.environ:
                del os.environ[key]

    def test_database_connection_and_tables(self):
        """测试数据库连接和表结构"""
        print("🔍 测试数据库连接和表结构...")

        # 获取数据库引擎
        engine = get_engine()
        assert engine is not None

        # 测试表结构（通过尝试连接验证）
        with get_session() as session:
            # 测试关键表是否存在
            tables_to_check = [
                "users",
                "tasks",
                "points_transactions",
                "rewards",
                "reward_transactions",
                "reward_recipes",
                "task_top3",
                "focus_sessions",
                "auth",
                "chat_sessions",
                "chat_messages"
            ]

            for table_name in tables_to_check:
                result = session.execute(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
                ).fetchone()
                assert result is not None, f"表 {table_name} 不存在"

        print("✅ 数据库连接和表结构正常")

    def test_reward_config_api_compatibility(self):
        """测试奖励配置API兼容性"""
        print("🔍 测试奖励配置API兼容性...")

        config = RewardConfig()

        # 测试v4重构中可能被删除的方法
        try:
            default_rewards = config.get_default_rewards()
            assert isinstance(default_rewards, list)
            print("✅ get_default_rewards() 正常")
        except AttributeError as e:
            pytest.fail(f"get_default_rewards() 方法不存在: {e}")

        try:
            default_recipes = config.get_default_recipes()
            assert isinstance(default_recipes, list)
            print("✅ get_default_recipes() 正常")
        except AttributeError as e:
            pytest.fail(f"get_default_recipes() 方法不存在: {e}")

        try:
            recipe = config.get_recipe_by_id("test")
            # v4中应该返回None或抛出明确异常
            print("✅ get_recipe_by_id() 正常")
        except AttributeError as e:
            pytest.fail(f"get_recipe_by_id() 方法不存在: {e}")

        # 测试必要的方法仍然存在
        try:
            lottery_config = config.get_top3_lottery_config()
            assert "points_amount" in lottery_config
            print("✅ get_top3_lottery_config() 正常")
        except AttributeError as e:
            pytest.fail(f"get_top3_lottery_config() 方法不存在: {e}")

    def test_reward_database_initialization(self):
        """测试奖励数据库初始化"""
        print("🔍 测试奖励数据库初始化...")

        try:
            with get_session() as session:
                initialize_reward_database(session)
            print("✅ 奖励数据库初始化成功")
        except Exception as e:
            pytest.fail(f"奖励数据库初始化失败: {e}")

    def test_all_domain_initializations(self):
        """测试所有领域数据库初始化"""
        print("🔍 测试所有领域数据库初始化...")

        try:
            with get_session() as session:
                # 任务数据库
                initialize_task_database(session)
                print("✅ 任务数据库初始化成功")

                # 聊天数据库
                initialize_chat_database(session)
                print("✅ 聊天数据库初始化成功")

                # 专注力数据库
                initialize_focus_database(session)
                print("✅ 专注力数据库初始化成功")

                # 认证数据库
                initialize_auth_database(session)
                print("✅ 认证数据库初始化成功")

                # 奖励数据库（再次测试）
                initialize_reward_database(session)
                print("✅ 奖励数据库初始化成功")

        except Exception as e:
            pytest.fail(f"领域数据库初始化失败: {e}")

    def test_api_main_imports(self):
        """测试API主模块导入"""
        print("🔍 测试API主模块导入...")

        try:
            # 测试主要模块导入
            import src.api.main
            print("✅ src.api.main 导入成功")

            # 测试关键依赖导入
            from src.api.main import app
            assert app is not None
            print("✅ FastAPI app 创建成功")

        except ImportError as e:
            pytest.fail(f"API主模块导入失败: {e}")
        except Exception as e:
            pytest.fail(f"API app 创建失败: {e}")

    def test_service_layer_compatibility(self):
        """测试服务层兼容性"""
        print("🔍 测试服务层兼容性...")

        try:
            # 测试核心服务导入
            from src.domains.reward.service import RewardService
            from src.domains.task.service import TaskService
            from src.domains.focus.service import FocusService
            from src.domains.points.service import PointsService

            print("✅ 所有核心服务导入成功")

            # 测试服务实例化（需要session的暂时跳过）
            print("✅ 服务类定义正常")

        except ImportError as e:
            pytest.fail(f"服务层导入失败: {e}")

    def test_v4_specific_changes(self):
        """测试v4重构的特定变更"""
        print("🔍 测试v4重构的特定变更...")

        with get_session() as session:
            # 检查rewards表结构
            result = session.execute("PRAGMA table_info(rewards)")
            columns = [row[1] for row in result.fetchall()]

            # v4：确保已删除的字段不存在
            assert "stock_quantity" not in columns, "stock_quantity字段应该已删除"
            assert "cost_type" not in columns, "cost_type字段应该已删除"
            assert "cost_value" not in columns, "cost_value字段应该已删除"

            # v4：确保必需的字段存在
            required_fields = ["id", "name", "description", "points_value", "category", "is_active"]
            for field in required_fields:
                assert field in columns, f"必需字段 {field} 不存在"

            print("✅ v4数据库结构验证通过")

        # 测试RewardService的v4变更
        from src.domains.reward.service import RewardService
        from src.domains.points.service import PointsService

        with get_session() as session:
            points_service = PointsService(session)
            reward_service = RewardService(session, points_service)

            # 测试get_available_rewards方法（v4中应该无库存检查）
            try:
                rewards = reward_service.get_available_rewards()
                assert isinstance(rewards, list)
                print("✅ RewardService.get_available_rewards() 正常")
            except Exception as e:
                pytest.fail(f"RewardService.get_available_rewards() 失败: {e}")

    def test_configuration_validation(self):
        """测试配置验证"""
        print("🔍 测试配置验证...")

        config = RewardConfig()

        # 测试配置验证功能
        try:
            is_valid = config.validate_config()
            assert is_valid is True, "配置验证应该通过"
            print("✅ 配置验证通过")
        except Exception as e:
            pytest.fail(f"配置验证失败: {e}")

        # 测试Top3配置
        lottery_config = config.get_top3_lottery_config()
        assert "points_amount" in lottery_config
        assert lottery_config["points_amount"] == 100  # v4默认值
        print("✅ Top3配置正常")

    def test_end_to_end_startup(self):
        """端到端启动测试"""
        print("🔍 执行端到端启动测试...")

        try:
            # 1. 测试配置加载
            config = RewardConfig()
            assert config is not None

            # 2. 测试数据库连接
            engine = get_engine()
            assert engine is not None

            # 3. 测试所有初始化
            with get_session() as session:
                initialize_task_database(session)
                initialize_chat_database(session)
                initialize_focus_database(session)
                initialize_auth_database(session)
                initialize_reward_database(session)

            # 4. 测试API导入
            import src.api.main
            from src.api.main import app
            assert app is not None

            # 5. 测试服务实例化
            from src.domains.reward.service import RewardService
            from src.domains.points.service import PointsService

            with get_session() as session:
                points_service = PointsService(session)
                reward_service = RewardService(session, points_service)
                rewards = reward_service.get_available_rewards()
                assert isinstance(rewards, list)

            print("✅ 端到端启动测试通过")

        except Exception as e:
            pytest.fail(f"端到端启动测试失败: {e}")
            import traceback
            traceback.print_exc()


@pytest.mark.integration
class TestSystemStartupRegression:
    """系统启动回归测试类"""

    def test_v4_regressions(self):
        """测试v4重构的回归问题"""
        print("🔍 测试v4重构的回归问题...")

        # 这个测试专门用于捕获v4重构中可能遗漏的问题
        config = RewardConfig()

        # 测试之前被删除的方法现在是否存在
        assert hasattr(config, 'get_default_rewards'), "get_default_rewards方法应该存在（向后兼容）"
        assert hasattr(config, 'get_default_recipes'), "get_default_recipes方法应该存在（向后兼容）"
        assert hasattr(config, 'get_recipe_by_id'), "get_recipe_by_id方法应该存在（向后兼容）"

        # 测试方法调用不抛出异常
        try:
            config.get_default_rewards()
            config.get_default_recipes()
            config.get_recipe_by_id("test")
        except Exception as e:
            pytest.fail(f"向后兼容方法调用失败: {e}")

        print("✅ v4回归测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])