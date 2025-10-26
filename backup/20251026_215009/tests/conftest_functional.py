"""
功能测试配置和Fixtures

提供端到端的功能测试，模拟真实用户场景。

作者：TaKeKe团队
版本：1.0.0 - 功能测试专用配置
"""

import pytest
import asyncio
import logging
from typing import Generator, Dict, Any, List, AsyncGenerator
from uuid import uuid4
from unittest.mock import Mock, patch
from httpx import AsyncClient
from sqlalchemy import text

from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.database import get_db_engine
from src.domains.points.service import PointsService
from src.domains.reward.service import RewardService
from src.domains.reward.welcome_gift_service import WelcomeGiftService
from src.domains.task.service import TaskService
from src.domains.top3.service import Top3Service

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def functional_test_db_engine():
    """功能测试数据库引擎"""
    engine = sa_create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "timeout": 30
        },
        echo=False
    )
    return engine


@pytest.fixture(scope="function")
def functional_test_db_session(functional_test_db_engine) -> Generator[Session, None, None]:
    """功能测试数据库会话"""
    SQLModel.metadata.create_all(functional_test_db_engine)
    session = Session(functional_test_db_engine)

    try:
        yield session
    finally:
        session.close()
        SQLModel.metadata.drop_all(functional_test_db_engine)


@pytest.fixture(scope="function")
def functional_test_db_with_complete_data(functional_test_db_session) -> Session:
    """包含完整功能测试数据的数据库"""
    _create_functional_test_data(functional_test_db_session)
    return functional_test_db_session


def _create_functional_test_data(session: Session) -> None:
    """创建功能测试数据"""
    from datetime import datetime, timezone
    from src.domains.reward.models import Reward, RewardRecipe
    from src.domains.user.models import User

    # 创建测试用户
    test_user = User(
        id="test-functional-user-001",
        nickname="功能测试用户",
        avatar_url="https://example.com/functional-avatar.jpg",
        bio="用于功能测试的完整用户",
        created_at=datetime.now(timezone.utc),
        last_login_at=datetime.now(timezone.utc)
    )
    session.add(test_user)

    # 创建完整的奖励系统数据
    rewards_data = [
        {
            "id": "reward-basic-001",
            "name": "小金币",
            "description": "基础金币，可用于兑换奖励",
            "points_value": 10,
            "category": "currency",
            "cost_type": "points",
            "cost_value": 10,
            "stock_quantity": 10000,
            "is_active": True
        },
        {
            "id": "reward-premium-001",
            "name": "钻石",
            "description": "珍贵钻石，高级奖励",
            "points_value": 100,
            "category": "premium",
            "cost_type": "points",
            "cost_value": 100,
            "stock_quantity": 1000,
            "is_active": True
        },
        {
            "id": "points-bonus-card-001",
            "name": "积分加成卡",
            "description": "+50%积分加成，有效期1小时",
            "points_value": 0,
            "category": "道具",
            "cost_type": "points",
            "cost_value": 0,
            "stock_quantity": 0,
            "is_active": True
        },
        {
            "id": "focus-item-001",
            "name": "专注道具",
            "description": "立即完成专注会话",
            "points_value": 0,
            "category": "道具",
            "cost_type": "points",
            "cost_value": 0,
            "stock_quantity": 0,
            "is_active": True
        },
        {
            "id": "time-management-coupon-001",
            "name": "时间管理券",
            "description": "延长任务截止时间1天",
            "points_value": 0,
            "category": "道具",
            "cost_type": "points",
            "cost_value": 0,
            "stock_quantity": 0,
            "is_active": True
        }
    ]

    for reward_data in rewards_data:
        reward = Reward(
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            **reward_data
        )
        session.add(reward)

    # 创建奖励配方
    recipe = RewardRecipe(
        id="recipe-gold-to-diamond-001",
        name="小金币合成钻石",
        description="10个小金币可以合成1个钻石",
        result_reward_id="reward-premium-001",
        result_quantity=1,
        cost_type="rewards",
        cost_value='{"小金币": 10}',
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(recipe)

    session.commit()


@pytest.fixture(scope="function")
async def functional_test_client(functional_test_db_with_complete_data) -> AsyncGenerator[AsyncClient, None]:
    """功能测试HTTP客户端"""
    from fastapi.testclient import TestClient
    from httpx import AsyncClient

    # 覆盖数据库依赖
    def override_get_db():
        try:
            yield functional_test_db_with_complete_data
        finally:
            pass

    app.dependency_overrides[get_db_engine] = override_get_db

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

    # 清理依赖覆盖
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def functional_test_services(functional_test_db_with_complete_data) -> Dict[str, Any]:
    """功能测试服务实例集合"""
    return {
        "points_service": PointsService(functional_test_db_with_complete_data),
        "reward_service": RewardService(
            functional_test_db_with_complete_data,
            PointsService(functional_test_db_with_complete_data)
        ),
        "welcome_gift_service": WelcomeGiftService(
            functional_test_db_with_complete_data,
            PointsService(functional_test_db_with_complete_data)
        ),
        "task_service": TaskService(functional_test_db_with_complete_data),
        "top3_service": Top3Service(functional_test_db_with_complete_data)
    }


@pytest.fixture(scope="function")
def functional_test_user_data() -> Dict[str, Any]:
    """功能测试用户数据"""
    return {
        "user_id": "test-functional-user-001",
        "nickname": "功能测试用户",
        "avatar_url": "https://example.com/functional-avatar.jpg",
        "expected_initial_points": 0,
        "expected_welcome_gift_points": 1000,
        "expected_welcome_gift_rewards": 3
    }


# 场景数据工厂
class FunctionalTestScenarios:
    """功能测试场景工厂"""

    @staticmethod
    async def create_new_user_journey(client: AsyncClient, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新用户完整流程数据"""
        journey_data = {
            "user_id": user_data["user_id"],
            "steps": [],
            "results": {}
        }

        try:
            # 步骤1: 领取欢迎礼包
            welcome_response = await client.post("/api/v1/user/welcome-gift")
            journey_data["steps"].append("welcome_gift_requested")

            if welcome_response.status_code == 200:
                welcome_data = welcome_response.json()
                journey_data["results"]["welcome_gift"] = welcome_data
                journey_data["steps"].append("welcome_gift_success")
            else:
                journey_data["steps"].append("welcome_gift_failed")
                journey_data["results"]["welcome_gift_error"] = welcome_response.text

            # 步骤2: 查询积分余额
            points_response = await client.get("/api/v1/points/balance")
            journey_data["steps"].append("points_balance_checked")

            if points_response.status_code == 200:
                points_data = points_response.json()
                journey_data["results"]["points_balance"] = points_data
            else:
                journey_data["results"]["points_balance_error"] = points_response.text

            # 步骤3: 查询奖励列表
            rewards_response = await client.get("/api/v1/rewards/catalog")
            journey_data["steps"].append("rewards_catalog_checked")

            if rewards_response.status_code == 200:
                rewards_data = rewards_response.json()
                journey_data["results"]["rewards_catalog"] = rewards_data
            else:
                journey_data["results"]["rewards_catalog_error"] = rewards_response.text

            # 步骤4: 查询我的奖励
            my_rewards_response = await client.get("/api/v1/rewards/my-rewards")
            journey_data["steps"].append("my_rewards_checked")

            if my_rewards_response.status_code == 200:
                my_rewards_data = my_rewards_response.json()
                journey_data["results"]["my_rewards"] = my_rewards_data
            else:
                journey_data["results"]["my_rewards_error"] = my_rewards_response.text

        except Exception as e:
            journey_data["steps"].append("journey_failed")
            journey_data["error"] = str(e)

        return journey_data

    @staticmethod
    async def create_task_management_flow(client: AsyncClient, user_id: str) -> Dict[str, Any]:
        """创建任务管理流程数据"""
        flow_data = {
            "user_id": user_id,
            "tasks_created": [],
            "tasks_updated": [],
            "tasks_completed": []
        }

        try:
            # 创建多个任务
            task_titles = ["完成项目文档", "代码审查", "团队会议准备", "学习新技术", "健身计划"]

            for title in task_titles:
                task_data = {
                    "title": title,
                    "description": f"这是关于{title}的详细描述",
                    "priority": "medium",
                    "estimated_minutes": 60
                }

                create_response = await client.post("/api/v1/tasks/", json=task_data)
                if create_response.status_code == 200:
                    created_task = create_response.json()
                    flow_data["tasks_created"].append(created_task)

                    # 更新任务状态
                    update_response = await client.patch(
                        f"/api/v1/tasks/{created_task['id']}",
                        json={"status": "completed"}
                    )
                    if update_response.status_code == 200:
                        flow_data["tasks_completed"].append(created_task)

        except Exception as e:
            flow_data["error"] = str(e)

        return flow_data

    @staticmethod
    async def create_reward_redemption_flow(client: AsyncClient, user_id: str) -> Dict[str, Any]:
        """创建奖励兑换流程数据"""
        flow_data = {
            "user_id": user_id,
            "redemptions_attempted": [],
            "redemptions_successful": [],
            "redemptions_failed": []
        }

        try:
            # 获取奖励目录
            catalog_response = await client.get("/api/v1/rewards/catalog")
            if catalog_response.status_code != 200:
                flow_data["error"] = "无法获取奖励目录"
                return flow_data

            catalog = catalog_response.json()
            available_rewards = catalog.get("rewards", [])

            # 尝试兑换前3个奖励
            for reward in available_rewards[:3]:
                redemption_data = {
                    "reward_id": reward["id"],
                    "quantity": 1
                }

                flow_data["redemptions_attempted"].append(redemption_data)

                redeem_response = await client.post("/api/v1/rewards/redeem", json=redemption_data)

                if redeem_response.status_code == 200:
                    result = redeem_response.json()
                    flow_data["redemptions_successful"].append({
                        "redemption": redemption_data,
                        "result": result
                    })
                else:
                    flow_data["redemptions_failed"].append({
                        "redemption": redemption_data,
                        "error": redeem_response.text
                    })

        except Exception as e:
            flow_data["error"] = str(e)

        return flow_data


@pytest.fixture(scope="function")
def functional_test_scenarios() -> FunctionalTestScenarios:
    """功能测试场景工厂实例"""
    return FunctionalTestScenarios()


# 验证工具
@pytest.fixture(scope="function")
def functional_test_validator():
    """功能测试验证工具"""
    class FunctionalTestValidator:
        @staticmethod
        def validate_welcome_gift_journey(journey_data: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, bool]:
            """验证欢迎礼包流程"""
            results = {}

            # 验证欢迎礼包成功
            results["welcome_gift_success"] = "welcome_gift_success" in journey_data.get("steps", [])

            # 验证积分余额
            if "points_balance" in journey_data.get("results", {}):
                actual_balance = journey_data["results"]["points_balance"].get("balance", 0)
                expected_balance = expected.get("expected_points", 1000)
                results["points_balance_correct"] = actual_balance == expected_balance
            else:
                results["points_balance_checked"] = False

            # 验证奖励数量
            if "my_rewards" in journey_data.get("results", {}):
                my_rewards = journey_data["results"]["my_rewards"]
                actual_reward_count = len(my_rewards.get("rewards", []))
                expected_reward_count = expected.get("expected_reward_count", 3)
                results["reward_count_correct"] = actual_reward_count >= expected_reward_count
            else:
                results["rewards_received"] = False

            return results

        @staticmethod
        def validate_task_flow(flow_data: Dict[str, Any]) -> Dict[str, bool]:
            """验证任务管理流程"""
            results = {}

            results["tasks_created"] = len(flow_data.get("tasks_created", [])) > 0
            results["tasks_completed"] = len(flow_data.get("tasks_completed", [])) > 0
            results["no_errors"] = "error" not in flow_data

            return results

        @staticmethod
        def validate_reward_flow(flow_data: Dict[str, Any]) -> Dict[str, bool]:
            """验证奖励兑换流程"""
            results = {}

            results["attempted_redemptions"] = len(flow_data.get("redemptions_attempted", [])) > 0
            results["has_successful_redemptions"] = len(flow_data.get("redemptions_successful", [])) > 0
            results["no_errors"] = "error" not in flow_data

            return results

    return FunctionalTestValidator()


# 测试标记配置
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "functional: 功能测试")
    config.addinivalue_line("markers", "e2e: 端到端测试")
    config.addinivalue_line("markers", "scenario: 场景测试")
    config.addinivalue_line("markers", "slow: 慢速功能测试")


# 清理辅助
@pytest.fixture(autouse=True)
def functional_test_cleanup(functional_test_db_session):
    """功能测试自动清理"""
    yield
    # 测试后全面清理
    try:
        tables = [
            "points_transactions",
            "reward_transactions",
            "reward_recipes",
            "rewards",
            "top3_entries",
            "tasks",
            "users",
            "user_settings",
            "user_stats"
        ]

        for table in tables:
            functional_test_db_session.execute(text(f"DELETE FROM {table}"))

        functional_test_db_session.commit()
    except Exception as e:
        logger.error(f"功能测试清理失败: {e}")
        functional_test_db_session.rollback()


# 性能监控
@pytest.fixture(scope="function")
def performance_monitor():
    """性能监控工具"""
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = {}

        def start_timing(self, operation_name: str):
            """开始计时"""
            import time
            self.metrics[f"{operation_name}_start"] = time.time()

        def end_timing(self, operation_name: str) -> float:
            """结束计时并返回耗时"""
            import time
            start_time = self.metrics.get(f"{operation_name}_start")
            if start_time:
                duration = time.time() - start_time
                self.metrics[f"{operation_name}_duration"] = duration
                return duration
            return 0.0

        def get_report(self) -> Dict[str, float]:
            """获取性能报告"""
            return {k: v for k, v in self.metrics.items() if k.endswith("_duration")}

    return PerformanceMonitor()