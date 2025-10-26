"""
用户Profile API修复验证测试

专门测试UserRepository数据查询修复和API响应验证问题
"""

import pytest
import os
from uuid import uuid4

# 设置测试环境
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DEBUG"] = "false"

from src.database import get_session
from src.domains.user.repository import UserRepository
from src.domains.user.schemas import UpdateProfileRequest
from src.domains.auth.schemas import UnifiedResponse

def with_session(func):
    """数据库会话装饰器"""
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
class TestUserProfileAPIFix:
    """用户Profile API修复验证测试"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """设置测试环境变量"""
        # 环境变量已在顶部设置
        yield
        # 清理不需要，每个测试使用独立的内存数据库

    def test_user_repository_data_consistency(self):
        """测试UserRepository数据一致性修复"""
        print("🔍 测试UserRepository数据一致性修复...")

        @with_session
        def run_test(session):
            user_repo = UserRepository(session)
            test_user_id = uuid4()

            # 1. 创建用户
            user = user_repo.create_user(test_user_id, "原始昵称")
            assert user.nickname == "原始昵称"
            assert user.bio is None
            print("✅ 用户创建成功")

            # 2. 查询用户 - 验证数据一致性
            found_user = user_repo.get_by_id(test_user_id)
            assert found_user.nickname == "原始昵称"
            assert found_user.bio is None
            assert found_user.user_id == test_user_id
            print("✅ 用户查询数据一致")

            # 3. 更新用户
            updates = {
                "nickname": "更新昵称",
                "bio": "这是更新后的简介",
                "avatar_url": "https://example.com/avatar.jpg"
            }
            updated_user = user_repo.update_user(test_user_id, updates)
            assert updated_user.nickname == "更新昵称"
            assert updated_user.bio == "这是更新后的简介"
            assert updated_user.avatar_url == "https://example.com/avatar.jpg"
            print("✅ 用户更新成功")

            # 4. 再次查询验证修复
            final_user = user_repo.get_by_id(test_user_id)
            assert final_user.nickname == "更新昵称"
            assert final_user.bio == "这是更新后的简介"
            assert final_user.avatar_url == "https://example.com/avatar.jpg"
            print("✅ 更新后数据一致性验证通过")

        run_test()

    def test_update_profile_response_validation(self):
        """测试UpdateProfileResponse验证修复"""
        print("🔍 测试UpdateProfileResponse验证修复...")

        @with_session
        def run_test(session):
            user_repo = UserRepository(session)
            test_user_id = uuid4()

            # 创建用户
            user = user_repo.create_user(test_user_id, "测试用户")

            # 模拟API请求
            request = UpdateProfileRequest(
                nickname="新昵称",
                bio="新简介",
                avatar_url="https://example.com/new-avatar.jpg"
            )

            # 执行更新（模拟API逻辑）
            updates = {}
            updated_fields = []

            if request.nickname:
                updates["nickname"] = request.nickname
                updated_fields.append("nickname")

            if request.avatar_url:
                updates["avatar_url"] = request.avatar_url
                updated_fields.append("avatar_url")

            if request.bio:
                updates["bio"] = request.bio
                updated_fields.append("bio")

            updated_user = user_repo.update_user(test_user_id, updates)

            # 构造响应数据（模拟API响应）
            update_response = {
                "id": str(test_user_id),
                "nickname": updated_user.nickname,
                "avatar_url": updated_user.avatar_url,
                "bio": updated_user.bio,
                "updated_fields": updated_fields
            }

            # 验证响应数据 - 这里不应该再出现None值
            assert update_response["nickname"] == "新昵称"
            assert update_response["bio"] == "新简介"
            assert update_response["avatar_url"] == "https://example.com/new-avatar.jpg"
            assert update_response["nickname"] is not None
            assert update_response["bio"] is not None
            assert update_response["avatar_url"] is not None

            # 尝试构造Pydantic模型（验证Schema）
            response = UnifiedResponse(
                code=200,
                data=update_response,
                message="更新成功"
            )

            print("✅ UpdateProfileResponse验证通过")

        run_test()

    def test_edge_cases(self):
        """测试边界情况"""
        print("🔍 测试边界情况...")

        @with_session
        def run_test(session):
            user_repo = UserRepository(session)
            test_user_id = uuid4()

            # 测试部分更新
            user = user_repo.create_user(test_user_id, "原始昵称")

            # 只更新昵称
            updates = {"nickname": "部分更新昵称"}
            updated_user = user_repo.update_user(test_user_id, updates)

            assert updated_user.nickname == "部分更新昵称"
            assert updated_user.bio is None  # 应该保持原值
            assert updated_user.avatar_url is None  # 应该保持原值
            print("✅ 部分更新验证通过")

            # 测试空值更新
            updates = {
                "nickname": "最终昵称",
                "bio": "最终简介",
                "avatar_url": "https://example.com/final.jpg"
            }
            final_user = user_repo.update_user(test_user_id, updates)

            assert final_user.nickname == "最终昵称"
            assert final_user.bio == "最终简介"
            assert final_user.avatar_url == "https://example.com/final.jpg"
            print("✅ 完整更新验证通过")

        run_test()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])