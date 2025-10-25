"""
User领域类型安全测试

测试User领域内的UUID到字符串类型转换，确保SQLite兼容性。
这个测试专门针对User领域，不修改其他任何领域的代码。

测试覆盖：
1. UUID类型转换为字符串
2. 数据库查询兼容性
3. API端点类型安全
4. 端到端流程验证
"""

import pytest
import pytest_asyncio
from uuid import UUID, uuid4
from sqlmodel import Session
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.domains.auth.models import Auth
from src.api.main import app


class TestUserTypeSafety:
    """User领域类型安全测试套件"""

    @pytest.mark.unit
    def test_uuid_to_string_conversion(self):
        """测试UUID到字符串转换逻辑"""
        # 测试UUID对象转换为字符串
        uuid_obj = uuid4()
        uuid_str = str(uuid_obj)

        # 验证转换结果
        assert isinstance(uuid_str, str)
        assert len(uuid_str) == 36  # 标准UUID字符串长度
        assert uuid_str.count('-') == 4  # UUID格式验证

        # 验证往返转换一致性
        uuid_back = UUID(uuid_str)
        assert str(uuid_back) == uuid_str

    @pytest.mark.unit
    def test_user_id_type_compatibility_with_sqlite(self, test_db_session: Session):
        """测试用户ID类型与SQLite的兼容性"""
        # 创建测试用户
        test_uuid = str(uuid4())
        auth_user = Auth(
            id=test_uuid,  # 使用字符串ID
            wechat_openid="test_openid_12345",
            is_guest=False
        )

        # 保存到数据库
        test_db_session.add(auth_user)
        test_db_session.commit()
        test_db_session.refresh(auth_user)

        # 验证可以用字符串ID查询
        found_user = test_db_session.get(Auth, test_uuid)
        assert found_user is not None
        assert found_user.id == test_uuid
        assert isinstance(found_user.id, str)

        # 验证UUID对象查询会失败（模拟原始错误）
        uuid_obj = UUID(test_uuid)
        with pytest.raises(Exception) as exc_info:
            # 这里应该抛出SQLite绑定错误
            test_db_session.get(Auth, uuid_obj)

        # 验证错误类型
        assert "UUID" in str(exc_info.value) or "binding" in str(exc_info.value).lower()

    @pytest.mark.integration
    async def test_user_api_type_conversion_flow(self, test_client: AsyncClient):
        """测试用户API的完整类型转换流程"""
        # 1. 创建游客用户
        guest_response = await test_client.post("/api/v3/auth/guest-init")
        assert guest_response.status_code == 200
        guest_data = guest_response.json()["data"]

        # 2. 获取用户信息（这个操作会经过类型转换）
        headers = {"Authorization": f"Bearer {guest_data['access_token']}"}
        profile_response = await test_client.get("/user/profile", headers=headers)

        # 验证API调用成功
        assert profile_response.status_code == 200
        profile_data = profile_response.json()["data"]

        # 验证返回的ID是字符串类型
        assert isinstance(profile_data["id"], str)
        assert len(profile_data["id"]) == 36

        # 3. 更新用户信息（也会经过类型转换）
        update_data = {"nickname": "测试用户昵称"}
        update_response = await test_client.put(
            "/user/profile",
            json=update_data,
            headers=headers
        )

        # 验证更新成功
        assert update_response.status_code == 200
        update_result = update_response.json()["data"]
        assert isinstance(update_result["id"], str)
        assert update_result["nickname"] == "测试用户昵称"

    @pytest.mark.integration
    async def test_welcome_gift_type_safety(self, test_client: AsyncClient):
        """测试欢迎礼包功能的类型安全"""
        # 1. 创建用户
        guest_response = await test_client.post("/api/v3/auth/guest-init")
        assert guest_response.status_code == 200
        guest_data = guest_response.json()["data"]

        # 2. 领取欢迎礼包
        headers = {"Authorization": f"Bearer {guest_data['access_token']}"}
        gift_response = await test_client.post("/user/welcome-gift/claim", headers=headers)

        # 验证领取成功
        assert gift_response.status_code == 200
        gift_data = gift_response.json()["data"]

        # 验证返回的事务组ID和用户ID都是字符串
        assert isinstance(gift_data["transaction_group"], str)
        assert isinstance(gift_data["granted_at"], str)

        # 3. 获取历史记录
        history_response = await test_client.get("/user/welcome-gift/history", headers=headers)
        assert history_response.status_code == 200
        history_data = history_response.json()["data"]

        # 验证历史记录中的ID都是字符串
        for item in history_data["history"]:
            assert isinstance(item["transaction_group"], str)
            assert isinstance(item["granted_at"], str)

    @pytest.mark.unit
    def test_database_id_field_consistency(self, test_db_session: Session):
        """测试数据库ID字段的一致性"""
        # 创建多个用户，验证ID类型一致性
        users = []
        for i in range(3):
            user_uuid = str(uuid4())
            user = Auth(
                id=user_uuid,
                wechat_openid=f"test_openid_{i}",
                is_guest=False
            )
            test_db_session.add(user)
            users.append(user)

        test_db_session.commit()

        # 验证所有用户的ID都是字符串类型
        for user in users:
            test_db_session.refresh(user)
            assert isinstance(user.id, str)
            assert len(user.id) == 36

            # 验证可以用字符串ID查询
            found_user = test_db_session.get(Auth, user.id)
            assert found_user is not None
            assert found_user.id == user.id

    @pytest.mark.integration
    async def test_error_handling_and_logging(self, test_client: AsyncClient, caplog):
        """测试错误处理和日志记录"""
        # 创建用户
        guest_response = await test_client.post("/api/v3/auth/guest-init")
        guest_data = guest_response.json()["data"]
        headers = {"Authorization": f"Bearer {guest_data['access_token']}"}

        # 测试无效的更新请求
        invalid_response = await test_client.put(
            "/user/profile",
            json={},  # 空数据
            headers=headers
        )

        # 验证错误响应
        assert invalid_response.status_code in [200, 400]  # 根据业务逻辑可能是200或400

        # 如果是200响应，检查数据字段
        if invalid_response.status_code == 200:
            result = invalid_response.json()["data"]
            # 验证ID仍然是字符串类型
            assert isinstance(result["id"], str)

    @pytest.mark.e2e
    async def test_complete_user_journey_type_safety(self, test_client: AsyncClient):
        """测试完整用户旅程的类型安全性"""
        # 1. 用户注册流程
        guest_response = await test_client.post("/api/v3/auth/guest-init")
        guest_data = guest_response.json()["data"]
        headers = {"Authorization": f"Bearer {guest_data['access_token']}"}

        # 2. 获取用户信息
        profile_response = await test_client.get("/user/profile", headers=headers)
        profile_data = profile_response.json()["data"]
        user_id = profile_data["id"]

        # 3. 更新用户信息
        update_response = await test_client.put(
            "/user/profile",
            json={"nickname": "旅程测试用户"},
            headers=headers
        )

        # 4. 领取欢迎礼包
        gift_response = await test_client.post("/user/welcome-gift/claim", headers=headers)

        # 5. 获取礼包历史
        history_response = await test_client.get("/user/welcome-gift/history", headers=headers)

        # 验证所有响应中的ID都是字符串类型
        assert isinstance(user_id, str)
        assert isinstance(profile_data["id"], str)
        assert isinstance(update_response.json()["data"]["id"], str)
        assert isinstance(gift_response.json()["data"]["transaction_group"], str)

        history_data = history_response.json()["data"]
        for item in history_data["history"]:
            assert isinstance(item["transaction_group"], str)


class TestUserTypeConversionHelpers:
    """测试User领域类型转换辅助函数"""

    def test_uuid_string_conversion_helper(self):
        """测试UUID字符串转换辅助函数"""
        # 模拟User领域可能需要的转换逻辑
        def ensure_string_id(user_id):
            """确保用户ID是字符串类型"""
            if isinstance(user_id, UUID):
                return str(user_id)
            elif isinstance(user_id, str):
                return user_id
            else:
                raise ValueError(f"Invalid user_id type: {type(user_id)}")

        # 测试UUID对象转换
        uuid_obj = uuid4()
        uuid_str = ensure_string_id(uuid_obj)
        assert isinstance(uuid_str, str)

        # 测试字符串直接返回
        direct_str = "550e8400-e29b-41d4-a716-446655440000"
        returned_str = ensure_string_id(direct_str)
        assert returned_str == direct_str
        assert isinstance(returned_str, str)

        # 测试无效类型抛出异常
        with pytest.raises(ValueError):
            ensure_string_id(12345)
        with pytest.raises(ValueError):
            ensure_string_id(None)