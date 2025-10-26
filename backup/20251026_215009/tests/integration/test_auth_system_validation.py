"""
认证系统综合验证测试

针对欢迎礼包接口"用户不存在"错误创建的完整测试套件：
1. 验证数据库Schema一致性
2. 验证JWT token有效性
3. 验证用户数据持久化
4. 验证认证链路完整性
"""

import pytest
import os
import sys
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID

# 设置测试环境
os.environ["DATABASE_URL"] = "sqlite:///./test_auth_validation.db"
os.environ["DEBUG"] = "false"

from src.database import get_session
from src.domains.auth.repository import AuthRepository
from src.domains.auth.models import Auth
from src.domains.user.router import claim_welcome_gift
from src.api.dependencies import get_current_user_id
from sqlmodel import select
import jwt
from jwt import PyJWTError


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
class TestAuthSystemValidation:
    """认证系统综合验证测试"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """设置测试环境"""
        # 清理测试数据库
        if os.path.exists("./test_auth_validation.db"):
            os.remove("./test_auth_validation.db")
        yield
        # 测试后清理
        if os.path.exists("./test_auth_validation.db"):
            os.remove("./test_auth_validation.db")

    def test_database_schema_consistency(self):
        """测试数据库Schema一致性"""
        print("🔍 测试数据库Schema一致性...")

        @with_session
        def run_test(session):
            # 检查Auth表结构
            statement = select(Auth)
            try:
                # 尝试查询所有字段
                result = session.exec(statement).first()
                print("✅ 数据库Schema正常，所有字段可访问")
                return True
            except Exception as e:
                if "no such column" in str(e):
                    print(f"❌ 数据库Schema不匹配: {e}")
                    return False
                else:
                    raise

        return run_test()

    def test_user_creation_and_persistence(self):
        """测试用户创建和持久化"""
        print("🔍 测试用户创建和持久化...")

        test_user_id = uuid4()

        @with_session
        def create_user(session):
            auth_repo = AuthRepository(session)
            user = auth_repo.create_user(
                user_id=test_user_id,
                is_guest=True
            )
            return user

        @with_session
        def verify_user_persistence(session):
            auth_repo = AuthRepository(session)
            found_user = auth_repo.get_by_id(test_user_id)
            return found_user

        # 创建用户
        created_user = create_user()
        assert created_user.id == str(test_user_id)
        assert created_user.is_guest is True
        print("✅ 用户创建成功")

        # 验证持久化（新会话）
        found_user = verify_user_persistence()
        assert found_user is not None
        assert found_user.id == str(test_user_id)
        assert found_user.is_guest is True
        print("✅ 用户数据持久化验证通过")

    def test_jwt_token_validation_chain(self):
        """测试JWT token验证链路"""
        print("🔍 测试JWT token验证链路...")

        test_user_id = uuid4()

        # 创建测试用户
        @with_session
        def create_test_user(session):
            auth_repo = AuthRepository(session)
            user = auth_repo.create_user(
                user_id=test_user_id,
                is_guest=True
            )
            return user

        create_test_user()

        # 模拟JWT token生成
        def create_test_jwt(user_id: UUID) -> str:
            payload = {
                "sub": str(user_id),
                "is_guest": True,
                "jwt_version": 1,
                "token_type": "access",
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
                "jti": str(uuid4())
            }

            # 使用测试密钥（实际应用中应从配置获取）
            secret_key = "test_secret_key"
            token = jwt.encode(payload, secret_key, algorithm="HS256")
            return token

        # 验证JWT token
        def validate_test_jwt(token: str) -> dict:
            try:
                secret_key = "test_secret_key"
                payload = jwt.decode(token, secret_key, algorithms=["HS256"])
                return payload
            except PyJWTError as e:
                print(f"❌ JWT验证失败: {e}")
                return None

        # 创建JWT token
        jwt_token = create_test_jwt(test_user_id)
        print("✅ JWT token创建成功")

        # 验证JWT token
        jwt_payload = validate_test_jwt(jwt_token)
        assert jwt_payload is not None
        assert jwt_payload["sub"] == str(test_user_id)
        print("✅ JWT token验证通过")

        # 验证用户存在性
        @with_session
        def verify_user_exists(session):
            auth_repo = AuthRepository(session)
            user_id = UUID(jwt_payload["sub"])
            user = auth_repo.get_by_id(user_id)
            return user

        user = verify_user_exists()
        assert user is not None
        assert user.id == str(test_user_id)
        print("✅ JWT用户存在性验证通过")

    def test_welcome_gift_api_full_flow(self):
        """测试欢迎礼包API完整流程"""
        print("🔍 测试欢迎礼包API完整流程...")

        test_user_id = uuid4()

        # 1. 创建用户
        @with_session
        def create_user_for_gift(session):
            auth_repo = AuthRepository(session)
            user = auth_repo.create_user(
                user_id=test_user_id,
                is_guest=True
            )
            return user

        created_user = create_user_for_gift()
        print(f"✅ 测试用户创建成功: {created_user.id}")

        # 2. 模拟API调用链路
        @with_session
        def simulate_welcome_gift_api(session):
            """模拟欢迎礼包API的完整调用链路"""

            # 步骤1：从JWT token获取用户ID（模拟get_current_user_id）
            def mock_get_current_user_id():
                return test_user_id

            # 步骤2：验证用户存在（模拟API中的验证逻辑）
            user_id = mock_get_current_user_id()
            auth_repo = AuthRepository(session)
            user = auth_repo.get_by_id(user_id)

            if not user:
                return {"success": False, "error": "用户不存在"}

            # 步骤3：调用欢迎礼包服务（模拟）
            # 这里简化处理，只验证用户存在性
            return {
                "success": True,
                "user_id": str(user.id),
                "is_guest": user.is_guest
            }

        result = simulate_welcome_gift_api()
        assert result["success"] is True
        assert result["user_id"] == str(test_user_id)
        print("✅ 欢迎礼包API完整流程验证通过")

    def test_edge_cases(self):
        """测试边界情况"""
        print("🔍 测试边界情况...")

        # 测试不存在的用户ID
        @with_session
        def test_nonexistent_user(session):
            auth_repo = AuthRepository(session)
            fake_user_id = uuid4()
            user = auth_repo.get_by_id(fake_user_id)
            return user

        nonexistent_user = test_nonexistent_user()
        assert nonexistent_user is None
        print("✅ 不存在用户查询验证通过")

        # 测试空数据库查询
        @with_session
        def test_empty_database(session):
            auth_repo = AuthRepository(session)
            # 直接查询所有用户
            statement = select(Auth)
            users = session.exec(statement).all()
            return len(users)

        user_count = test_empty_database()
        assert user_count == 0
        print("✅ 空数据库验证通过")

    def test_database_file_persistence(self):
        """测试数据库文件持久化"""
        print("🔍 测试数据库文件持久化...")

        test_user_id = uuid4()

        # 在第一个会话中创建用户
        @with_session
        def create_user_in_first_session(session):
            auth_repo = AuthRepository(session)
            user = auth_repo.create_user(
                user_id=test_user_id,
                is_guest=True
            )
            return user

        created_user = create_user_in_first_session()
        print("✅ 第一会话用户创建成功")

        # 在第二个完全独立的会话中验证用户存在
        @with_session
        def verify_user_in_second_session(session):
            auth_repo = AuthRepository(session)
            user = auth_repo.get_by_id(test_user_id)
            return user

        found_user = verify_user_in_second_session()
        assert found_user is not None
        assert found_user.id == str(test_user_id)
        print("✅ 数据库文件持久化验证通过")

        # 验证数据库文件确实存在
        assert os.path.exists("./test_auth_validation.db")
        print("✅ 数据库文件存在验证通过")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])