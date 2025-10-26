"""
简化的系统启动集成测试

专门测试v4重构中发现的问题：
1. RewardConfig API兼容性
2. 奖励数据库初始化
3. API服务启动

作者：TaKeKe团队
版本：v4.0 - 启动流程验证
"""

import pytest
import os
import sys

from src.database import get_engine, get_session
from src.domains.reward.database import initialize_reward_database
from src.config.game_config import RewardConfig


def with_session(func):
    """数据库会话装饰器，简化测试中的会话管理"""
    def wrapper(*args, **kwargs):
        session_gen = get_session()
        session = next(session_gen)
        try:
            result = func(session, *args, **kwargs)
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass
        return result
    return wrapper


@pytest.mark.integration
class TestSystemStartupSimple:
    """简化的系统启动集成测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """设置测试环境变量"""
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["DEBUG"] = "false"

        yield

        for key in ["DATABASE_URL", "DEBUG"]:
            if key in os.environ:
                del os.environ[key]

    def test_reward_config_api_compatibility(self):
        """测试奖励配置API兼容性"""
        print("🔍 测试奖励配置API兼容性...")

        config = RewardConfig()

        # 测试v4重构中可能被删除的方法
        assert hasattr(config, 'get_default_rewards'), "get_default_rewards方法应该存在"
        assert hasattr(config, 'get_default_recipes'), "get_default_recipes方法应该存在"
        assert hasattr(config, 'get_recipe_by_id'), "get_recipe_by_id方法应该存在"

        # 测试方法调用不抛出异常
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

        # 测试必要的方法
        try:
            lottery_config = config.get_top3_lottery_config()
            assert "points_amount" in lottery_config
            assert lottery_config["points_amount"] == 100
            print("✅ get_top3_lottery_config() 正常")
        except AttributeError as e:
            pytest.fail(f"get_top3_lottery_config() 方法不存在: {e}")

    def test_reward_database_initialization(self):
        """测试奖励数据库初始化"""
        print("🔍 测试奖励数据库初始化...")

        try:
            with_session(initialize_reward_database)
            print("✅ 奖励数据库初始化成功")
        except Exception as e:
            pytest.fail(f"奖励数据库初始化失败: {e}")
            import traceback
            traceback.print_exc()

    def test_database_v4_structure(self):
        """测试v4数据库结构"""
        print("🔍 测试v4数据库结构...")

        def check_v4_structure(session):
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

        with_session(check_v4_structure)

    def test_reward_service_v4_functionality(self):
        """测试RewardService v4功能"""
        print("🔍 测试RewardService v4功能...")

        from src.domains.reward.service import RewardService
        from src.domains.points.service import PointsService

        def test_reward_service(session):
            points_service = PointsService(session)
            reward_service = RewardService(session, points_service)

            # 测试get_available_rewards方法（v4中应该无库存检查）
            rewards = reward_service.get_available_rewards()
            assert isinstance(rewards, list)
            print("✅ RewardService.get_available_rewards() 正常")

            # 验证返回的数据不包含已删除的字段
            for reward in rewards:
                assert "stock_quantity" not in reward, "奖品数据不应包含stock_quantity"
                assert "cost_type" not in reward, "奖品数据不应包含cost_type"
                assert "cost_value" not in reward, "奖品数据不应包含cost_value"

            print("✅ 奖品数据格式符合v4规范")

        try:
            with_session(test_reward_service)
        except Exception as e:
            pytest.fail(f"RewardService测试失败: {e}")
            import traceback
            traceback.print_exc()

    def test_api_main_imports(self):
        """测试API主模块导入"""
        print("🔍 测试API主模块导入...")

        try:
            import src.api.main
            print("✅ src.api.main 导入成功")

            from src.api.main import app
            assert app is not None
            print("✅ FastAPI app 创建成功")

        except ImportError as e:
            pytest.fail(f"API主模块导入失败: {e}")
        except Exception as e:
            pytest.fail(f"API app 创建失败: {e}")

    def test_end_to_end_reward_flow(self):
        """端到端奖励流程测试"""
        print("🔍 执行端到端奖励流程测试...")

        from src.domains.reward.service import RewardService
        from src.domains.points.service import PointsService

        def test_end_to_end(session):
            # 初始化数据库
            initialize_reward_database(session)

            # 测试服务
            points_service = PointsService(session)
            reward_service = RewardService(session, points_service)
            rewards = reward_service.get_available_rewards()
            assert isinstance(rewards, list)

            print("✅ 端到端奖励流程测试通过")

        try:
            # 1. 配置测试
            config = RewardConfig()
            assert config is not None

            # 2. 数据库测试
            engine = get_engine()
            assert engine is not None

            # 3. 执行端到端测试
            with_session(test_end_to_end)

        except Exception as e:
            pytest.fail(f"端到端奖励流程测试失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])