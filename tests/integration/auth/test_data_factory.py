"""
认证系统测试数据工厂

提供全面的测试数据生成功能，包括：
1. 用户数据生成（游客、微信用户）
2. 微信API响应模拟
3. 认证令牌数据
4. 审计日志数据
5. 边界条件测试数据

设计原则：
- 数据多样性：覆盖各种正常和异常情况
- 类型安全：确保生成的数据符合Schema定义
- 易于使用：简化测试用例的数据准备
- 可扩展：便于添加新的测试场景

作者：TaTakeKe团队
版本：2.0.0 - 认证系统测试基础设施
"""

import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone, date
from unittest.mock import Mock
from dataclasses import dataclass, field

from src.domains.auth.exceptions import (
    AuthenticationException,
    UserNotFoundException,
    ValidationError,
    TokenException
)


@dataclass
class UserData:
    """用户数据结构"""
    id: str
    wechat_openid: Optional[str]
    is_guest: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    jwt_version: int = 1


@dataclass
class WeChatUserData:
    """微信用户数据结构"""
    openid: str
    nickname: str
    headimgurl: Optional[str]
    unionid: Optional[str] = None
    sex: Optional[int] = None
    province: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


@dataclass
class TokenData:
    """令牌数据结构"""
    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    is_guest: bool = True


@dataclass
class AuditLogData:
    """审计日志数据结构"""
    id: Optional[str] = None
    user_id: Optional[str] = None
    action: str = ""
    result: str = ""
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_id: Optional[str] = None
    error_code: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AuthTestDataFactory:
    """
    认证系统测试数据工厂

    提供各种类型的测试数据生成方法，支持正常场景和边界条件测试。
    """

    @staticmethod
    def create_guest_user(**overrides) -> UserData:
        """
        创建游客用户数据

        Args:
            **overrides: 覆盖默认字段

        Returns:
            UserData: 游客用户数据
        """
        default_data = {
            "id": str(uuid.uuid4()),
            "wechat_openid": None,
            "is_guest": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_login_at": datetime.now(timezone.utc),
            "jwt_version": 1
        }
        default_data.update(overrides)
        return UserData(**default_data)

    @staticmethod
    def create_wechat_user(**overrides) -> UserData:
        """
        创建微信用户数据

        Args:
            **overrides: 覆盖默认字段

        Returns:
            UserData: 微信用户数据
        """
        default_data = {
            "id": str(uuid.uuid4()),
            "wechat_openid": f"ox{uuid.uuid4().hex[:16]}",
            "is_guest": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_login_at": datetime.now(timezone.utc),
            "jwt_version": 1
        }
        default_data.update(overrides)
        return UserData(**default_data)

    @staticmethod
    def create_wechat_user_info(**overrides) -> WeChatUserData:
        """
        创建微信用户信息数据

        Args:
            **overrides: 覆盖默认字段

        Returns:
            WeChatUserData: 微信用户信息
        """
        default_data = {
            "openid": f"ox{uuid.uuid4().hex[:16]}",
            "nickname": "测试用户",
            "headimgurl": "http://example.com/avatar.jpg",
            "unionid": f"ox{uuid.uuid4().hex[:16]}",
            "sex": 1,
            "province": "北京",
            "city": "北京",
            "country": "中国"
        }
        default_data.update(overrides)
        return WeChatUserData(**default_data)

    @staticmethod
    def create_token_data(**overrides) -> TokenData:
        """
        创建令牌数据

        Args:
            **overrides: 覆盖默认字段

        Returns:
            TokenData: 令牌数据
        """
        user_id = overrides.get("user_id", str(uuid.uuid4()))
        default_data = {
            "user_id": user_id,
            "access_token": f"access.{user_id[:8]}.mock.token",
            "refresh_token": f"refresh.{user_id[:8]}.mock.token",
            "token_type": "bearer",
            "expires_in": 3600,
            "is_guest": overrides.get("is_guest", True)
        }
        default_data.update(overrides)
        return TokenData(**default_data)

    @staticmethod
    def create_audit_log(**overrides) -> AuditLogData:
        """
        创建审计日志数据

        Args:
            **overrides: 覆盖默认字段

        Returns:
            AuditLogData: 审计日志数据
        """
        default_data = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "action": "login",
            "result": "success",
            "details": None,
            "ip_address": "127.0.0.1",
            "user_agent": "Test-Agent/1.0",
            "device_id": None,
            "error_code": None,
            "created_at": datetime.now(timezone.utc)
        }
        default_data.update(overrides)
        return AuditLogData(**default_data)

    # ===== 边界条件测试数据 =====

    @staticmethod
    def create_boundary_test_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """
        创建边界条件测试场景

        Returns:
            Dict[str, List[Dict]]: 各种边界条件测试数据
        """
        return {
            "uuid_inputs": [
                {"input": str(uuid.uuid4()), "type": "valid_uuid", "expected": "success"},
                {"input": uuid.uuid4(), "type": "valid_uuid_object", "expected": "success"},
                {"input": None, "type": "null_value", "expected": "error"},
                {"input": "", "type": "empty_string", "expected": "error"},
                {"input": "   ", "type": "whitespace_only", "expected": "error"},
                {"input": "invalid-uuid-string", "type": "invalid_format", "expected": "error"},
                {"input": "0" * 32, "type": "numeric_uuid", "expected": "depends"},
                {"input": "a" * 32, "type": "alpha_uuid", "expected": "depends"},
                {"input": "x" * 33, "type": "too_long", "expected": "error"},
                {"input": "123", "type": "too_short", "expected": "error"}
            ],

            "wechat_openid_inputs": [
                {"input": f"ox{uuid.uuid4().hex[:16]}", "type": "valid_openid", "expected": "success"},
                {"input": None, "type": "null_openid", "expected": "error_for_regular_user"},
                {"input": "", "type": "empty_openid", "expected": "error"},
                {"input": " ", "type": "space_openid", "expected": "error"},
                {"input": "ox1234567890@#$%^&*()", "type": "special_chars", "expected": "success_or_warning"},
                {"input": "测试中文", "type": "chinese_chars", "expected": "success_or_warning"},
                {"input": "ox" + "a" * 100, "type": "very_long", "expected": "truncated_or_error"},
                {"input": "invalid", "type": "invalid_format", "expected": "error"}
            ],

            "user_names": [
                {"input": "测试用户", "type": "chinese_name", "expected": "success"},
                {"input": "Test User", "type": "english_name", "expected": "success"},
                {"input": "ユーザー", "type": "japanese_name", "expected": "success"},
                {"input": "", "type": "empty_name", "expected": "error_or_default"},
                {"input": "x" * 1000, "type": "very_long_name", "expected": "truncated_or_error"},
                {"input": "Test<>User", "type": "html_chars", "expected": "sanitized_or_error"},
                {"input": "Test'User", "type": "quote_chars", "expected": "sanitized_or_error"},
                {"input": None, "type": "null_name", "expected": "error_or_default"}
            ],

            "token_values": [
                {"input": f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{uuid.uuid4().hex}.signature",
                 "type": "valid_jwt", "expected": "success"},
                {"input": "", "type": "empty_token", "expected": "error"},
                {"input": "invalid.token", "type": "invalid_format", "expected": "error"},
                {"input": None, "type": "null_token", "expected": "error"},
                {"input": "expired.token.value", "type": "expired_token", "expected": "error"},
                {"input": "revoked.token.value", "type": "revoked_token", "expected": "error"}
            ]
        }

    @staticmethod
    def create_wechat_api_responses() -> Dict[str, Any]:
        """
        创建微信API响应模拟数据

        Returns:
            Dict[str, Any]: 各种微信API响应场景
        """
        return {
            "success_response": {
                "status": 200,
                "data": {
                    "openid": f"ox{uuid.uuid4().hex[:16]}",
                    "nickname": "测试用户",
                    "headimgurl": "http://example.com/avatar.jpg",
                    "unionid": f"ox{uuid.uuid4().hex[:16]}",
                    "sex": 1,
                    "province": "北京",
                    "city": "北京",
                    "country": "中国"
                },
                "expected_result": "success"
            },

            "null_response": {
                "status": 200,
                "data": None,
                "expected_result": "error",
                "expected_error": AuthenticationException
            },

            "empty_response": {
                "status": 200,
                "data": {},
                "expected_result": "error",
                "expected_error": AuthenticationException
            },

            "missing_openid_response": {
                "status": 200,
                "data": {
                    "nickname": "测试用户",
                    "headimgurl": "http://example.com/avatar.jpg"
                    # 缺少openid
                },
                "expected_result": "error",
                "expected_error": AuthenticationException
            },

            "invalid_openid_response": {
                "status": 200,
                "data": {
                    "openid": "",  # 空openid
                    "nickname": "测试用户",
                    "headimgurl": "http://example.com/avatar.jpg"
                },
                "expected_result": "error",
                "expected_error": AuthenticationException
            },

            "special_chars_response": {
                "status": 200,
                "data": {
                    "openid": "ox1234567890@#$%^&*()",
                    "nickname": "测试用户<>&\"'",
                    "headimgurl": "http://example.com/avatar with spaces.jpg"
                },
                "expected_result": "success_or_warning"
            },

            "extreme_length_response": {
                "status": 200,
                "data": {
                    "openid": "ox" + "a" * 100,
                    "nickname": "x" * 1000,
                    "headimgurl": "http://example.com/" + "x" * 500
                },
                "expected_result": "truncated_or_error"
            },

            "api_error_response": {
                "status": 400,
                "data": {"error": "invalid_code"},
                "expected_result": "error",
                "expected_error": AuthenticationException
            },

            "network_error_response": {
                "status": 500,
                "data": None,
                "expected_result": "error",
                "expected_error": AuthenticationException
            }
        }

    @staticmethod
    def create_mock_wechat_api():
        """
        创建Mock微信API服务

        Returns:
            Mock: 配置好的微信API Mock对象
        """
        mock_api = Mock()

        # 获取测试响应数据
        responses = AuthTestDataFactory.create_wechat_api_responses()

        def get_user_info_success(code: str):
            """成功获取用户信息"""
            return responses["success_response"]["data"]

        def get_user_info_null(code: str):
            """返回None"""
            return responses["null_response"]["data"]

        def get_user_info_empty(code: str):
            """返回空对象"""
            return responses["empty_response"]["data"]

        def get_user_info_missing_openid(code: str):
            """返回缺少openid的对象"""
            return responses["missing_openid_response"]["data"]

        def get_user_info_invalid_openid(code: str):
            """返回无效openid的对象"""
            return responses["invalid_openid_response"]["data"]

        def get_user_info_api_error(code: str):
            """API错误"""
            raise AuthenticationException("微信API调用失败")

        # 设置默认行为
        mock_api.get_user_info.side_effect = get_user_info_success

        # 提供各种场景的方法
        mock_api.set_success_response = lambda: setattr(mock_api.get_user_info, 'side_effect', get_user_info_success)
        mock_api.set_null_response = lambda: setattr(mock_api.get_user_info, 'side_effect', get_user_info_null)
        mock_api.set_empty_response = lambda: setattr(mock_api.get_user_info, 'side_effect', get_user_info_empty)
        mock_api.set_missing_openid_response = lambda: setattr(mock_api.get_user_info, 'side_effect', get_user_info_missing_openid)
        mock_api.set_invalid_openid_response = lambda: setattr(mock_api.get_user_info, 'side_effect', get_user_info_invalid_openid)
        mock_api.set_api_error_response = lambda: setattr(mock_api.get_user_info, 'side_effect', get_user_info_api_error)

        return mock_api

    @staticmethod
    def create_batch_users(count: int, user_type: str = "mixed") -> List[UserData]:
        """
        批量创建用户数据

        Args:
            count: 创建数量
            user_type: 用户类型 ("guest", "wechat", "mixed")

        Returns:
            List[UserData]: 用户数据列表
        """
        users = []

        for i in range(count):
            if user_type == "guest":
                user = AuthTestDataFactory.create_guest_user(
                    wechat_openid=f"batch-guest-{i}" if i % 2 == 0 else None
                )
            elif user_type == "wechat":
                user = AuthTestDataFactory.create_wechat_user(
                    wechat_openid=f"batch-wechat-{i}"
                )
            else:  # mixed
                if i % 3 == 0:
                    user = AuthTestDataFactory.create_guest_user()
                else:
                    user = AuthTestDataFactory.create_wechat_user()

            users.append(user)

        return users

    @staticmethod
    def create_error_scenarios() -> Dict[str, Dict[str, Any]]:
        """
        创建错误场景测试数据

        Returns:
            Dict[str, Dict[str, Any]]: 各种错误场景
        """
        return {
            "user_not_found": {
                "input": str(uuid.uuid4()),
                "expected_error": UserNotFoundException,
                "error_message": "用户不存在"
            },

            "invalid_token": {
                "input": "invalid.token.value",
                "expected_error": TokenException,
                "error_message": "令牌无效"
            },

            "expired_token": {
                "input": "expired.token.value",
                "expected_error": TokenException,
                "error_message": "令牌已过期"
            },

            "validation_error": {
                "input": {"invalid_field": "value"},
                "expected_error": ValidationError,
                "error_message": "数据验证失败"
            },

            "authentication_error": {
                "input": "invalid_credentials",
                "expected_error": AuthenticationException,
                "error_message": "认证失败"
            }
        }

    @staticmethod
    def create_performance_test_data(sizes: List[int] = None) -> Dict[int, Dict[str, Any]]:
        """
        创建性能测试数据

        Args:
            sizes: 测试数据大小列表

        Returns:
            Dict[int, Dict[str, Any]]: 性能测试数据
        """
        if sizes is None:
            sizes = [10, 50, 100, 500, 1000]

        performance_data = {}

        for size in sizes:
            performance_data[size] = {
                "users": AuthTestDataFactory.create_batch_users(size, "mixed"),
                "expected_operations": size,
                "max_execution_time": size * 0.01,  # 每个操作最多10ms
                "max_memory_usage": size * 1024  # 每个用户最多1KB
            }

        return performance_data


# ===== 便捷函数 =====

def create_test_guest_user(**kwargs) -> UserData:
    """便捷函数：创建测试游客用户"""
    return AuthTestDataFactory.create_guest_user(**kwargs)


def create_test_wechat_user(**kwargs) -> UserData:
    """便捷函数：创建测试微信用户"""
    return AuthTestDataFactory.create_wechat_user(**kwargs)


def create_mock_wechat_api():
    """便捷函数：创建Mock微信API"""
    return AuthTestDataFactory.create_mock_wechat_api()


def create_boundary_test_data() -> Dict[str, List[Dict[str, Any]]]:
    """便捷函数：创建边界条件测试数据"""
    return AuthTestDataFactory.create_boundary_test_scenarios()


def create_performance_data(sizes: List[int] = None) -> Dict[int, Dict[str, Any]]:
    """便捷函数：创建性能测试数据"""
    return AuthTestDataFactory.create_performance_test_data(sizes)