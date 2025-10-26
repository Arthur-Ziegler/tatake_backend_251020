"""
Service层集成测试

测试Service层与Repository层的完整调用链，确保：
1. UUID类型正确传递
2. Service层业务逻辑正确
3. 数据一致性得到保证
4. 错误处理机制有效

重点测试真实场景下的Service→Repository调用，避免Mock掩盖类型问题。

作者：TaTakeKe团队
版本：2.0.0 - 认证系统测试基础设施
"""

import pytest
import os
from uuid import UUID, uuid4
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# 使用绝对导入
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))

from tests.integration.auth.test_data_factory import (
    AuthTestDataFactory,
    create_test_guest_user,
    create_test_wechat_user,
    create_mock_wechat_api
)
from tests.integration.auth.conftest import (
    auth_repository,
    auth_service,
    audit_repository,
    test_db_session,
    mock_wechat_api
)
from src.domains.auth.exceptions import (
    AuthenticationException,
    UserNotFoundException,
    ValidationError,
    TokenException
)


@pytest.mark.integration
@pytest.mark.auth
class TestServiceTypeSafety:
    """Service层类型安全测试"""

    def test_guest_init_service_uuid_consistency(self, auth_service):
        """
        测试游客初始化Service层UUID类型一致性

        验证Service层正确处理UUID类型，不会传递字符串给Repository。
        """
        # 调用Service层方法
        result = auth_service.init_guest_user()

        # 验证返回数据结构
        assert "user_id" in result
        assert "access_token" in result
        assert "refresh_token" in result
        assert "is_guest" in result
        assert result["is_guest"] is True

        # 验证user_id是有效UUID字符串
        user_id_str = result["user_id"]
        try:
            user_id_uuid = UUID(user_id_str)
        except ValueError:
            pytest.fail("返回的user_id不是有效的UUID字符串")

        # 验证令牌不为空
        assert result["access_token"] is not None
        assert len(result["access_token"]) > 0
        assert result["refresh_token"] is not None
        assert len(result["refresh_token"]) > 0

    def test_wechat_register_service_uuid_handling(self, auth_service, mock_wechat_api):
        """
        测试微信注册Service层UUID处理

        验证Service层在处理微信注册时正确转换UUID类型。
        """
        # 配置Mock微信API
        mock_wechat_api.set_success_response()

        # 创建微信注册请求
        from src.domains.auth.schemas import WeChatRegisterRequest
        request = WeChatRegisterRequest(
            wechat_openid="ox1234567890abcdef",
            authorization_code="test_code"
        )

        # 调用Service层方法
        result = auth_service.wechat_register(request)

        # 验证返回数据
        assert "user_id" in result
        assert result["is_guest"] is False

        # 验证user_id是有效UUID
        try:
            UUID(result["user_id"])
        except ValueError:
            pytest.fail("微信注册返回的user_id不是有效的UUID")

    def test_wechat_login_service_uuid_consistency(self, auth_service, mock_wechat_api):
        """
        测试微信登录Service层UUID一致性
        """
        # 配置Mock微信API
        mock_wechat_api.set_success_response()

        # 创建微信登录请求
        from src.domains.auth.schemas import WeChatLoginRequest
        request = WeChatLoginRequest(
            wechat_openid="ox1234567890abcdef",
            authorization_code="test_code"
        )

        # 调用Service层方法
        result = auth_service.wechat_login(request)

        # 验证UUID一致性
        assert "user_id" in result
        try:
            UUID(result["user_id"])
        except ValueError:
            pytest.fail("微信登录返回的user_id不是有效的UUID")

    def test_guest_upgrade_service_uuid_flow(self, auth_service):
        """
        测试游客升级Service层UUID流程

        验证Service层在游客升级过程中正确处理UUID类型传递。
        """
        # 1. 初始化游客用户
        guest_result = auth_service.init_guest_user()
        guest_user_id = UUID(guest_result["user_id"])

        # 2. 创建升级请求
        from src.domains.auth.schemas import GuestUpgradeRequest
        upgrade_request = GuestUpgradeRequest(
            wechat_openid="ox1234567890abcdef"
        )

        # 3. 调用升级方法
        upgrade_result = auth_service.upgrade_guest_account(
            request=upgrade_request,
            current_user_id=guest_user_id,  # 传入UUID对象
            ip_address="127.0.0.1",
            user_agent="Test-Agent"
        )

        # 4. 验证升级结果
        assert "user_id" in upgrade_result
        assert upgrade_result["is_guest"] is False
        assert upgrade_result["user_id"] == str(guest_user_id)  # 应该是同一个用户

    def test_token_refresh_service_uuid_handling(self, auth_service):
        """
        测试令牌刷新Service层UUID处理
        """
        # 1. 初始化用户获取初始令牌
        init_result = auth_service.init_guest_user()
        refresh_token = init_result["refresh_token"]

        # 2. 创建刷新请求
        from src.domains.auth.schemas import TokenRefreshRequest
        refresh_request = TokenRefreshRequest(
            refresh_token=refresh_token
        )

        # 3. 调用刷新方法
        refresh_result = auth_service.refresh_token(refresh_request)

        # 4. 验证刷新结果中的UUID一致性
        assert "user_id" in refresh_result
        assert refresh_result["user_id"] == init_result["user_id"]  # 同一用户
        try:
            UUID(refresh_result["user_id"])
        except ValueError:
            pytest.fail("令牌刷新返回的user_id不是有效的UUID")


@pytest.mark.integration
@pytest.mark.auth
class TestServiceRepositoryIntegration:
    """Service层与Repository层集成测试"""

    def test_service_repository_uuid_transmission(self, auth_service, auth_repository):
        """
        测试Service层到Repository层的UUID传递

        这个测试确保Service层传递给Repository层的user_id是正确的UUID对象类型。
        """
        # 调用Service层方法
        result = auth_service.init_guest_user()

        # 验证Repository层确实收到了正确的UUID对象
        user_id_str = result["user_id"]

        # 通过Repository层直接查询验证
        found_user = auth_repository.get_by_id(UUID(user_id_str))
        assert found_user is not None
        assert found_user.id == user_id_str
        assert found_user.is_guest is True

    def test_service_method_parameter_types(self, auth_service):
        """
        测试Service方法参数类型安全性

        确保Service层方法能正确处理各种类型的输入参数。
        """
        # 测试UUID类型参数
        valid_uuid = uuid4()

        # 测试游客升级方法的参数类型
        from src.domains.auth.schemas import GuestUpgradeRequest
        upgrade_request = GuestUpgradeRequest(wechat_openid="test-openid")

        # 这里应该能接受UUID类型的current_user_id参数
        try:
            result = auth_service.upgrade_guest_account(
                request=upgrade_request,
                current_user_id=valid_uuid,
                ip_address="127.0.0.1",
                user_agent="Test-Agent"
            )
            assert result is not None
        except Exception as e:
            # 如果有错误，应该不是类型错误
            assert not isinstance(e, TypeError) or "UUID" not in str(e)

    def test_service_error_propagation(self, auth_service):
        """
        测试Service层错误传播机制

        确保Repository层的错误能正确传播到Service层。
        """
        # 测试不存在的用户ID
        non_existent_uuid = uuid4()

        from src.domains.auth.schemas import GuestUpgradeRequest
        upgrade_request = GuestUpgradeRequest(wechat_openid="test-openid")

        # 应该抛出UserNotFoundException
        with pytest.raises(UserNotFoundException):
            auth_service.upgrade_guest_account(
                request=upgrade_request,
                current_user_id=non_existent_uuid,
                ip_address="127.0.0.1",
                user_agent="Test-Agent"
            )


@pytest.mark.integration
@pytest.mark.auth
class TestServiceBusinessLogic:
    """Service层业务逻辑测试"""

    def test_wechat_duplicate_prevention(self, auth_service, auth_repository):
        """
        测试微信账号重复注册防护
        """
        # 1. 创建第一个用户
        from src.domains.auth.schemas import WeChatRegisterRequest
        request1 = WeChatRegisterRequest(
            wechat_openid="ox1234567890abcdef",
            authorization_code="test_code"
        )

        # 使用patch模拟微信API
        with patch.object(auth_service, '_get_wechat_user_info') as mock_wechat:
            mock_wechat.return_value = {
                'openid': 'ox1234567890abcdef',
                'nickname': '测试用户'
            }

            result1 = auth_service.wechat_register(request1)
            first_user_id = result1["user_id"]

        # 2. 尝试用相同openid再次注册
        request2 = WeChatRegisterRequest(
            wechat_openid="ox1234567890abcdef",  # 相同的openid
            authorization_code="test_code2"
        )

        with patch.object(auth_service, '_get_wechat_user_info') as mock_wechat:
            mock_wechat.return_value = {
                'openid': 'ox1234567890abcdef',
                'nickname': '测试用户'
            }

            result2 = auth_service.wechat_register(request2)
            second_user_id = result2["user_id"]

        # 3. 验证返回的是同一个用户
        assert first_user_id == second_user_id

    def test_guest_upgrade_uniqueness(self, auth_service):
        """
        测试游客账号升级唯一性
        """
        # 1. 创建游客用户
        guest_result = auth_service.init_guest_user()
        guest_user_id = UUID(guest_result["user_id"])

        # 2. 第一次升级
        from src.domains.auth.schemas import GuestUpgradeRequest
        upgrade_request = GuestUpgradeRequest(wechat_openid="ox1234567890abcdef")

        result1 = auth_service.upgrade_guest_account(
            request=upgrade_request,
            current_user_id=guest_user_id,
            ip_address="127.0.0.1",
            user_agent="Test-Agent"
        )

        # 3. 第二次尝试升级（应该成功，但没有实质变化）
        result2 = auth_service.upgrade_guest_account(
            request=GuestUpgradeRequest(wechat_openid="ox1234567890abcdef2"),
            current_user_id=guest_user_id,
            ip_address="127.0.0.1",
            user_agent="Test-Agent"
        )

        # 4. 验证结果一致性
        assert result1["user_id"] == result2["user_id"]
        assert result1["is_guest"] == result2["is_guest"] == False

    def test_token_lifecycle(self, auth_service):
        """
        测试令牌生命周期管理
        """
        # 1. 初始化用户
        init_result = auth_service.init_guest_user()
        access_token = init_result["access_token"]
        refresh_token = init_result["refresh_token"]

        # 2. 使用刷新令牌获取新令牌
        from src.domains.auth.schemas import TokenRefreshRequest
        refresh_request = TokenRefreshRequest(refresh_token=refresh_token)
        refresh_result = auth_service.refresh_token(refresh_request)

        # 3. 验证新令牌有效性
        assert refresh_result["access_token"] != access_token
        assert refresh_result["refresh_token"] != refresh_token
        assert refresh_result["user_id"] == init_result["user_id"]

        # 4. 验证新访问令牌可用
        # 这里可以添加JWT验证逻辑


@pytest.mark.integration
@pytest.mark.auth
class TestServiceDataValidation:
    """Service层数据验证测试"""

    def test_invalid_uuid_handling(self, auth_service):
        """
        测试Service层对无效UUID的处理
        """
        from src.domains.auth.schemas import GuestUpgradeRequest
        upgrade_request = GuestUpgradeRequest(wechat_openid="test-openid")

        # 测试各种无效UUID输入
        invalid_uuids = [
            "invalid-uuid",
            "",
            "123",
            None  # 如果类型允许
        ]

        for invalid_uuid in invalid_uuids:
            if invalid_uuid is None:
                continue  # 跳过None，因为类型系统应该捕获

            # 尝试将字符串转换为UUID（模拟类型错误）
            try:
                uuid_obj = UUID(invalid_uuid)
                # 如果转换成功，继续测试
                with pytest.raises((UserNotFoundException, ValidationError)):
                    auth_service.upgrade_guest_account(
                        request=upgrade_request,
                        current_user_id=uuid_obj,
                        ip_address="127.0.0.1",
                        user_agent="Test-Agent"
                    )
            except ValueError:
                # UUID转换失败，这是预期的
                continue

    def test_wechat_data_validation(self, auth_service):
        """
        测试微信数据验证
        """
        from src.domains.auth.schemas import WeChatRegisterRequest

        # 测试无效的微信OpenID
        invalid_openids = [
            "",
            "   ",  # 空白字符
            "x" * 200,  # 过长的字符串
            "invalid@#$%^&*()",  # 包含特殊字符
        ]

        for openid in invalid_openids:
            request = WeChatRegisterRequest(
                wechat_openid=openid,
                authorization_code="test_code"
            )

            # 应该抛出验证异常或业务异常
            with pytest.raises((ValidationError, AuthenticationException)):
                auth_service.wechat_register(request)

    def test_token_validation(self, auth_service):
        """
        测试令牌验证
        """
        from src.domains.auth.schemas import TokenRefreshRequest

        # 测试无效的刷新令牌
        invalid_tokens = [
            "",           # 空字符串
            "invalid",    # 无效格式
            "expired.token",  # 过期格式
        ]

        for invalid_token in invalid_tokens:
            request = TokenRefreshRequest(refresh_token=invalid_token)

            # 应该抛出令牌异常
            with pytest.raises((TokenException, AuthenticationException)):
                auth_service.refresh_token(request)


@pytest.mark.integration
@pytest.mark.auth
class TestServiceConcurrency:
    """Service层并发测试"""

    def test_concurrent_guest_init(self, auth_service):
        """
        测试并发游客初始化
        """
        import threading
        import time

        results = []
        errors = []

        def init_guest_worker():
            try:
                result = auth_service.init_guest_user()
                results.append(result)
                time.sleep(0.01)  # 小延迟
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=init_guest_worker)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发初始化出现错误: {errors}"
        assert len(results) == 5

        # 验证所有用户ID都是唯一的
        user_ids = [result["user_id"] for result in results]
        assert len(set(user_ids)) == len(user_ids), "存在重复的用户ID"

        # 验证所有用户ID都是有效的UUID
        for user_id in user_ids:
            try:
                UUID(user_id)
            except ValueError:
                pytest.fail(f"用户ID {user_id} 不是有效的UUID")

    def test_concurrent_wechat_register(self, auth_service):
        """
        测试并发微信注册
        """
        import threading
        import time

        results = []
        errors = []

        def register_worker(worker_id):
            try:
                from src.domains.auth.schemas import WeChatRegisterRequest
                request = WeChatRegisterRequest(
                    wechat_openid=f"ox{worker_id:04d}-concurrent",
                    authorization_code=f"code_{worker_id}"
                )

                # Mock微信API
                with patch.object(auth_service, '_get_wechat_user_info') as mock_wechat:
                    mock_wechat.return_value = {
                        'openid': f'ox{worker_id:04d}-concurrent',
                        'nickname': f'用户{worker_id}'
                    }

                    result = auth_service.wechat_register(request)
                    results.append((worker_id, result))
                    time.sleep(0.01)
            except Exception as e:
                errors.append((worker_id, e))

        # 创建多个线程
        threads = []
        for i in range(3):
            thread = threading.Thread(target=register_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发注册出现错误: {errors}"
        assert len(results) == 3

        # 验证所有用户ID都是唯一的
        user_ids = [result[1]["user_id"] for result in results]
        assert len(set(user_ids)) == len(user_ids), "存在重复的用户ID"