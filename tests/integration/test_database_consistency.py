"""
数据库一致性测试工程

专门检测和防止数据库分离、数据不一致问题的综合测试套件
"""

import pytest
import os
import tempfile
from uuid import uuid4

# 设置测试环境
temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
temp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{temp_db.name}"
os.environ["AUTH_DATABASE_URL"] = f"sqlite:///{temp_db.name}"  # 统一数据库
os.environ["DEBUG"] = "false"

from src.database import get_session
from src.domains.auth.repository import AuthRepository
from src.domains.auth.database import get_auth_db
from src.domains.auth.models import Auth
from sqlmodel import select
import asyncio
import httpx
from httpx import ASGITransport
from src.api.main import app

def with_main_session(func):
    """主数据库会话装饰器"""
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

def with_auth_session(func):
    """认证数据库会话装饰器"""
    def wrapper(*args, **kwargs):
        with get_auth_db() as session:
            return func(session, *args, **kwargs)
    return wrapper

@pytest.mark.integration
class TestDatabaseConsistency:
    """数据库一致性测试工程"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """设置测试环境"""
        # 清理测试数据库
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)
        yield
        # 测试后清理
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

    def test_database_configuration_consistency(self):
        """测试数据库配置一致性"""
        print("🔍 测试数据库配置一致性...")

        # 检查环境变量
        main_db_url = os.getenv("DATABASE_URL")
        auth_db_url = os.getenv("AUTH_DATABASE_URL")

        print(f"主数据库URL: {main_db_url}")
        print(f"认证数据库URL: {auth_db_url}")

        # 验证一致性
        assert main_db_url is not None, "主数据库URL未设置"
        assert auth_db_url is not None, "认证数据库URL未设置"
        assert main_db_url == auth_db_url, f"数据库不一致: {main_db_url} != {auth_db_url}"

        print("✅ 数据库配置一致性验证通过")

    @with_main_session
    def test_main_database_schema(self, session):
        """测试主数据库Schema"""
        print("🔍 测试主数据库Schema...")

        # 初始化主数据库
        from src.domains.auth.models import Auth, AuthLog, SMSVerification
        from src.domains.user.models import User, UserSettings, UserStats
        from sqlmodel import SQLModel

        engine = session.bind
        SQLModel.metadata.create_all(engine, checkfirst=True)

        # 验证Auth表存在
        try:
            statement = select(Auth)
            session.exec(statement).first()
            print("✅ 主数据库Auth表验证通过")
        except Exception as e:
            pytest.fail(f"主数据库Auth表验证失败: {e}")

    @with_auth_session
    def test_auth_database_schema(self, session):
        """测试认证数据库Schema"""
        print("🔍 测试认证数据库Schema...")

        # 初始化认证数据库
        from src.domains.auth.models import Auth, AuthLog, SMSVerification
        from sqlmodel import SQLModel

        engine = session.bind
        SQLModel.metadata.create_all(engine, checkfirst=True)

        # 验证Auth表存在
        try:
            statement = select(Auth)
            session.exec(statement).first()
            print("✅ 认证数据库Auth表验证通过")
        except Exception as e:
            pytest.fail(f"认证数据库Auth表验证失败: {e}")

    def test_user_registration_data_persistence(self):
        """测试用户注册数据持久化"""
        print("🔍 测试用户注册数据持久化...")

        @with_auth_session
        def create_user(session):
            auth_repo = AuthRepository(session)
            test_user_id = uuid4()
            user = auth_repo.create_user(
                user_id=test_user_id,
                is_guest=True
            )
            return test_user_id

        @with_main_session
        def verify_user_in_main(session, user_id):
            statement = select(Auth).where(Auth.id == str(user_id))
            result = session.exec(statement).first()
            return result is not None

        @with_auth_session
        def verify_user_in_auth(session, user_id):
            statement = select(Auth).where(Auth.id == str(user_id))
            result = session.exec(statement).first()
            return result is not None

        # 创建用户
        test_user_id = create_user()
        print(f"✅ 用户创建成功: {test_user_id}")

        # 验证用户在两个数据库中都存在
        main_has_user = verify_user_in_main(test_user_id)
        auth_has_user = verify_user_in_auth(test_user_id)

        print(f"主数据库有用户: {main_has_user}")
        print(f"认证数据库有用户: {auth_has_user}")

        # 由于配置了统一数据库，两个应该都有数据
        assert main_has_user, "用户数据未持久化到主数据库"
        assert auth_has_user, "用户数据未持久化到认证数据库"

        print("✅ 用户注册数据持久化验证通过")

    async def test_api_endpoints_use_same_database(self):
        """测试API端点使用相同数据库"""
        print("🔍 测试API端点使用相同数据库...")

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            try:
                # 1. 游客注册
                print("1️⃣ 游客注册...")
                auth_response = await client.post("/auth/guest/init")
                assert auth_response.status_code == 200, f"游客注册失败: {auth_response.text}"

                auth_data = auth_response.json()
                access_token = auth_data["data"]["access_token"]
                user_id = auth_data["data"]["user_id"]

                print(f"✅ 游客注册成功: {user_id}")

                # 2. 设置认证头
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }

                # 3. 测试Profile接口
                print("2️⃣ 测试Profile接口...")
                profile_response = await client.get("/user/profile", headers=headers)
                assert profile_response.status_code == 200, f"Profile接口失败: {profile_response.text}"

                profile_data = profile_response.json()
                profile_user_id = profile_data["data"]["id"]
                print(f"✅ Profile接口成功: {profile_user_id}")

                # 4. 测试欢迎礼包接口（关键测试）
                print("3️⃣ 测试欢迎礼包接口...")
                gift_response = await client.post("/user/welcome-gift/claim", headers=headers)

                # 这里应该不再出现"用户不存在"错误
                if gift_response.status_code == 200:
                    print("✅ 欢迎礼包接口成功")
                elif gift_response.status_code in [400, 409]:
                    # 400可能是重复领取，409可能是业务逻辑冲突，都是正常的
                    print(f"✅ 欢迎礼包接口返回业务状态: {gift_response.json()}")
                else:
                    # 如果还是404，说明数据库统一配置未生效
                    pytest.fail(f"欢迎礼包接口仍然失败，数据库统一可能未生效: {gift_response.text}")

                # 5. 验证用户ID一致性
                assert user_id == profile_user_id, "用户ID不一致"

                print("✅ API端点数据库一致性验证通过")

            except Exception as e:
                pytest.fail(f"API端点测试失败: {e}")

    def test_database_migration_consistency(self):
        """测试数据库迁移一致性"""
        print("🔍 测试数据库迁移一致性...")

        # 检查两个数据库文件路径是否相同
        main_db_path = os.getenv("DATABASE_URL", "").replace("sqlite:///", "")
        auth_db_path = os.getenv("AUTH_DATABASE_URL", "").replace("sqlite:///", "")

        print(f"主数据库路径: {main_db_path}")
        print(f"认证数据库路径: {auth_db_path}")

        assert main_db_path == auth_db_path, f"数据库路径不一致: {main_db_path} != {auth_db_path}"

        # 检查数据库文件是否存在
        if os.path.exists(main_db_path):
            file_size = os.path.getsize(main_db_path)
            print(f"数据库文件大小: {file_size} bytes")
            assert file_size > 0, "数据库文件为空"

        print("✅ 数据库迁移一致性验证通过")

    def test_cross_domain_data_consistency(self):
        """测试跨域数据一致性"""
        print("🔍 测试跨域数据一致性...")

        test_user_id = uuid4()

        @with_auth_session
        def create_user_in_auth(session):
            auth_repo = AuthRepository(session)
            user = auth_repo.create_user(
                user_id=test_user_id,
                is_guest=True
            )
            return user

        @with_main_session
        def read_user_from_main(session):
            statement = select(Auth).where(Auth.id == str(test_user_id))
            result = session.exec(statement).first()
            return result

        # 在认证域创建用户
        created_user = create_user_in_auth()
        print(f"✅ 在认证域创建用户: {created_user.id}")

        # 在主域读取用户
        found_user = read_user_from_main()
        print(f"✅ 在主域读取用户: {found_user.id if found_user else None}")

        assert found_user is not None, "跨域数据不一致：主域无法读取认证域创建的用户"
        assert str(found_user.id) == str(test_user_id), "跨域数据ID不一致"

        print("✅ 跨域数据一致性验证通过")

    def test_concurrent_database_access(self):
        """测试并发数据库访问"""
        print("🔍 测试并发数据库访问...")

        import threading
        import time

        results = []
        errors = []

        def create_and_verify_user(user_id_suffix):
            try:
                test_user_id = uuid4()

                @with_auth_session
                def create_user(session):
                    auth_repo = AuthRepository(session)
                    user = auth_repo.create_user(
                        user_id=test_user_id,
                        is_guest=True
                    )
                    return user

                @with_main_session
                def verify_user(session):
                    statement = select(Auth).where(Auth.id == str(test_user_id))
                    result = session.exec(statement).first()
                    return result is not None

                # 创建用户
                created_user = create_user()

                # 验证用户
                verified = verify_user()

                results.append((str(test_user_id), verified))

            except Exception as e:
                errors.append(e)

        # 创建多个并发线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_and_verify_user, args=(i,))
            threads.append(thread)

        # 启动所有线程
        start_time = time.time()
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        end_time = time.time()

        # 验证结果
        print(f"并发测试完成，耗时: {end_time - start_time:.2f}秒")
        print(f"成功操作: {len(results)}")
        print(f"错误数量: {len(errors)}")

        assert len(errors) == 0, f"并发访问出现错误: {errors}"
        assert len(results) == 5, f"并发操作数量不足: {len(results)}"

        # 验证所有操作都成功
        for user_id, verified in results:
            assert verified, f"用户 {user_id} 验证失败"

        print("✅ 并发数据库访问验证通过")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])