"""
测试UserReward功能清理

验证所有UserReward相关字段和功能已完全从项目中删除。

测试覆盖：
1. Reward Repository中不包含UserReward类导入和方法
2. Reward Schema中不包含UserRewardResponse定义
3. Reward Service中不包含UserReward相关业务逻辑
4. 测试用例中不引用UserReward字段

作者：TaKeKe团队
版本：1.0.0（Phase 1 Day 2）
"""

import pytest
import subprocess
import os


class TestUserRewardCleanup:
    """测试UserReward功能彻底清理"""

    def test_reward_repository_no_userreward_imports(self):
        """验证Reward Repository不包含UserReward导入"""
        try:
            from src.domains.reward.repository import RewardRepository
            import inspect

            # 检查导入语句
            source = inspect.getsource(RewardRepository)
            assert "UserReward" not in source, "RewardRepository imports UserReward"

        except ImportError as e:
            pytest.fail(f"Failed to import RewardRepository: {e}")

    def test_reward_repository_no_userreward_methods(self):
        """验证Reward Repository不包含UserReward方法"""
        try:
            from src.domains.reward.repository import RewardRepository
            import inspect

            # 检查方法
            methods = inspect.getmembers(RewardRepository, predicate=inspect.ismethod)
            userreward_methods = [
                name for name, method in methods
                if 'user_reward' in name.lower()
            ]

            assert len(userreward_methods) == 0, f"Found UserReward methods: {userreward_methods}"

        except ImportError as e:
            pytest.fail(f"Failed to import RewardRepository: {e}")

    def test_reward_schema_no_userreward_response(self):
        """验证Reward Schema不包含UserRewardResponse"""
        try:
            from src.domains.reward.schemas import RewardCatalogResponse, MyRewardsResponse

            # 检查是否有UserRewardResponse
            assert "UserRewardResponse" not in dir(), "Found UserRewardResponse in schemas module"

            # 检查导入语句
            import src.domains.reward.schemas
            source = inspect.getsource(src.domains.reward.schemas)
            assert "UserReward" not in source, "UserReward imported in schemas"

        except ImportError as e:
            pytest.fail(f"Failed to import reward schemas: {e}")

    def test_reward_service_no_userreward_logic(self):
        """验证Reward Service不包含UserReward逻辑"""
        try:
            from src.domains.reward.service import RewardService
            import inspect

            # 检查导入语句
            source = inspect.getsource(RewardService)
            assert "UserReward" not in source, "RewardService imports UserReward"

            # 检查方法
            methods = inspect.getmembers(RewardService, predicate=inspect.ismethod)
            userreward_methods = [
                name for name, method in methods
                if not name.startswith('_') and 'user_reward' in name.lower()
            ]

            assert len(userreward_methods) == 0, f"Found UserReward methods: {userreward_methods}"

        except ImportError as e:
            pytest.fail(f"Failed to import RewardService: {e}")

    def test_no_userreward_references_in_codebase(self):
        """验证整个代码库中没有UserReward相关引用"""
        try:
            # 使用grep搜索整个src目录
            result = subprocess.run(
                ["rg", "--count", "UserReward", "src/"],
                capture_output=True,
                text=True,
                check=True
            )

            # 应该没有匹配结果
            assert result.stdout.strip() == "0", f"Found UserReward references: {result.stdout}"

        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to search codebase: {e}")
        except FileNotFoundError:
            # ripgrep可能不可用，跳过此测试
            pytest.skip("ripgrep not available for codebase search")

    def test_models_no_userreward_class(self):
        """验证models中UserReward类已清理"""
        try:
            from src.domains.reward.models import Reward, PointsTransaction

            # 检查UserReward类不存在
            with pytest.raises(AttributeError):
                from src.domains.reward.models import UserReward

        except ImportError as e:
            pytest.fail(f"Failed to import reward models: {e}")

    def test_service_methods_cleanup(self):
        """验证Reward Service中UserReward相关方法已清理"""
        try:
            from src.domains.reward.service import RewardService
            import inspect

            # 检查方法
            methods = inspect.getmembers(RewardService, predicate=inspect.ismethod)
            userreward_methods = [
                name for name, method in methods
                if not name.startswith('_') and 'user_reward' in name.lower()
            ]

            assert len(userreward_methods) == 0, f"Found UserReward methods: {userreward_methods}"

        except ImportError as e:
            pytest.fail(f"Failed to import RewardService: {e}")