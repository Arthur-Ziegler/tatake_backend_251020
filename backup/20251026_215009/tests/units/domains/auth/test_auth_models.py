"""
Auth领域模型测试

测试Auth和AuthLog模型的基本功能，包括：
1. 模型实例化
2. 字段验证
3. 关系映射
4. 数据类型验证

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.domains.auth.models import Auth, AuthLog


@pytest.mark.unit
class TestAuthModel:
    """Auth模型测试类"""

    def test_auth_model_creation(self):
        """测试Auth模型创建"""
        auth_id = str(uuid4())
        auth = Auth(
            id=auth_id,
            is_guest=True,
            wechat_openid=None,
            jwt_version=1
        )

        assert auth.id == auth_id
        assert auth.is_guest is True
        assert auth.wechat_openid is None
        assert auth.jwt_version == 1
        assert auth.created_at is not None
        assert auth.updated_at is not None

    def test_auth_model_with_wechat_user(self):
        """测试微信用户的Auth模型"""
        auth_id = str(uuid4())
        wechat_openid = "wx_test_12345"
        auth = Auth(
            id=auth_id,
            is_guest=False,
            wechat_openid=wechat_openid,
            jwt_version=1
        )

        assert auth.id == auth_id
        assert auth.is_guest is False
        assert auth.wechat_openid == wechat_openid
        assert auth.jwt_version == 1

    def test_auth_model_timestamps(self):
        """测试时间戳自动生成"""
        before_creation = datetime.now(timezone.utc)

        auth = Auth(
            is_guest=True,
            wechat_openid=None,
            jwt_version=1
        )

        after_creation = datetime.now(timezone.utc)

        assert auth.created_at is not None
        assert auth.updated_at is not None
        assert before_creation <= auth.created_at <= after_creation
        assert before_creation <= auth.updated_at <= after_creation

    def test_auth_model_string_representation(self):
        """测试Auth模型的字符串表示"""
        auth = Auth(
            is_guest=True,
            wechat_openid=None,
            jwt_version=1
        )

        str_repr = str(auth)
        # SQLModel的字符串表示包含字段值，而不是类名
        assert auth.id in str_repr
        assert "is_guest=True" in str_repr


@pytest.mark.unit
class TestAuthLogModel:
    """AuthLog模型测试类"""

    def test_auth_log_model_creation(self):
        """测试AuthLog模型创建"""
        user_id = str(uuid4())
        log_id = str(uuid4())

        auth_log = AuthLog(
            id=log_id,
            user_id=user_id,
            action="login",
            result="success",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0"
        )

        assert auth_log.id == log_id
        assert auth_log.user_id == user_id
        assert auth_log.action == "login"
        assert auth_log.result == "success"
        assert auth_log.ip_address == "192.168.1.1"
        assert auth_log.user_agent == "TestAgent/1.0"
        assert auth_log.created_at is not None

    def test_auth_log_different_actions(self):
        """测试不同的认证日志动作"""
        user_id = str(uuid4())

        actions = ["login", "logout", "register", "token_refresh"]

        for action in actions:
            auth_log = AuthLog(
                user_id=user_id,
                action=action,
                result="success",
                ip_address="192.168.1.1",
                user_agent="TestAgent/1.0"
            )

            assert auth_log.action == action
            assert auth_log.user_id == user_id

    def test_auth_log_optional_fields(self):
        """测试AuthLog的可选字段"""
        user_id = str(uuid4())

        # 最小必需字段
        auth_log = AuthLog(
            user_id=user_id,
            action="login",
            result="success"
        )

        assert auth_log.user_id == user_id
        assert auth_log.action == "login"
        assert auth_log.result == "success"
        assert auth_log.ip_address is None
        assert auth_log.user_agent is None
        assert auth_log.created_at is not None

    def test_auth_log_timestamps(self):
        """测试AuthLog时间戳"""
        before_creation = datetime.now(timezone.utc)
        user_id = str(uuid4())

        auth_log = AuthLog(
            user_id=user_id,
            action="login",
            result="success"
        )

        after_creation = datetime.now(timezone.utc)

        assert auth_log.created_at is not None
        assert before_creation <= auth_log.created_at <= after_creation

    def test_auth_log_string_representation(self):
        """测试AuthLog模型的字符串表示"""
        user_id = str(uuid4())
        auth_log = AuthLog(
            user_id=user_id,
            action="login",
            result="success",
            ip_address="192.168.1.1"
        )

        str_repr = str(auth_log)
        # SQLModel的字符串表示包含字段值，而不是类名
        assert user_id in str_repr
        assert "login" in str_repr
        assert "success" in str_repr