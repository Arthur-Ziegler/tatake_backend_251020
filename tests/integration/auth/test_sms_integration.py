"""
SMS认证系统集成测试

测试SMS认证系统的端到端功能，包括：
1. 完整的注册流程（发送验证码 -> 验证 -> 用户创建）
2. 完整的登录流程（发送验证码 -> 验证 -> 获取令牌）
3. 完整的绑定流程（认证用户 -> 发送验证码 -> 绑定手机号）
4. 错误场景和边界情况
5. 与现有认证系统的集成

采用真实数据库和服务进行集成测试，确保系统在真实环境中的正确性。
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from src.api.main import app
from src.domains.auth.models import Auth, SMSVerification
from src.domains.auth.service import AuthService
from src.domains.auth.repository import AuthRepository
from src.domains.auth.database import get_auth_db


class TestSMSIntegration:
    """SMS认证系统集成测试"""

    @pytest.fixture(scope="function")
    def test_db_session(self):
        """创建测试数据库会话"""
        # 使用内存SQLite数据库进行集成测试
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            echo=False
        )

        # 创建所有表
        from src.domains.auth.models import Auth, SMSVerification, AuthLog
        Auth.metadata.create_all(engine)
        SMSVerification.metadata.create_all(engine)
        AuthLog.metadata.create_all(engine)

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()

        yield session

        session.close()

    @pytest.fixture
    def test_client(self, test_db_session):
        """创建测试客户端，使用测试数据库"""
        # 覆盖数据库依赖
        def override_get_auth_db():
            try:
                yield test_db_session
            finally:
                pass

        app.dependency_overrides[get_auth_db] = override_get_auth_db

        with TestClient(app) as client:
            yield client

        # 清理依赖覆盖
        app.dependency_overrides.clear()

    @pytest.fixture
    def mock_sms_client(self):
        """Mock SMS客户端，避免实际发送短信"""
        with patch('src.domains.auth.service.get_sms_client') as mock_get_client:
            from src.domains.auth.sms_client import MockSMSClient
            mock_client = MockSMSClient()
            mock_get_client.return_value = mock_client
            yield mock_client

    def test_complete_registration_flow(self, test_client, mock_sms_client, test_db_session):
        """测试完整的手机号注册流程"""
        phone = "13800138000"

        # 步骤1: 发送注册验证码
        send_response = test_client.post("/auth/sms/send", json={
            "phone": phone,
            "scene": "register"
        })

        assert send_response.status_code == 200
        send_data = send_response.json()
        assert send_data["code"] == 200
        assert send_data["data"]["expires_in"] == 300
        assert send_data["data"]["retry_after"] == 60

        # 验证SMS验证码记录已创建
        verification_repo = AuthRepository(test_db_session)
        verification = verification_repo.get_latest_unverified(phone, "register")
        assert verification is not None
        assert verification.phone == phone
        assert verification.scene == "register"
        assert verification.verified is False

        # 步骤2: 验证验证码并完成注册
        verify_response = test_client.post("/auth/sms/verify", json={
            "phone": phone,
            "code": verification.code,  # 使用实际生成的验证码
            "scene": "register"
        })

        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["code"] == 200
        assert verify_data["data"]["access_token"] is not None
        assert verify_data["data"]["refresh_token"] is not None
        assert verify_data["data"]["user_id"] is not None
        assert verify_data["data"]["is_new_user"] is True

        # 验证用户已创建
        user = verification_repo.get_auth_by_phone(phone)
        assert user is not None
        assert user.phone == phone
        assert user.is_guest is False
        assert user.wechat_openid is None  # 纯手机号用户

        # 验证验证码已标记为已验证
        updated_verification = verification_repo.get_latest_unverified(phone, "register")
        assert updated_verification is None  # 已验证，不应再返回

    def test_complete_login_flow(self, test_client, mock_sms_client, test_db_session):
        """测试完整的手机号登录流程"""
        phone = "13800138001"

        # 预先创建用户
        auth_repo = AuthRepository(test_db_session)
        user = Auth(
            phone=phone,
            is_guest=False,
            wechat_openid=None,
            jwt_version=1
        )
        auth_repo.create(user)
        test_db_session.commit()

        # 步骤1: 发送登录验证码
        send_response = test_client.post("/auth/sms/send", json={
            "phone": phone,
            "scene": "login"
        })

        assert send_response.status_code == 200

        # 步骤2: 验证验证码并登录
        verification = auth_repo.get_latest_unverified(phone, "login")
        verify_response = test_client.post("/auth/sms/verify", json={
            "phone": phone,
            "code": verification.code,
            "scene": "login"
        })

        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["code"] == 200
        assert verify_data["data"]["is_new_user"] is False  # 老用户登录
        assert verify_data["data"]["access_token"] is not None

    def test_complete_phone_binding_flow(self, test_client, mock_sms_client, test_db_session):
        """测试完整的手机号绑定流程"""
        # 预先创建微信用户
        auth_repo = AuthRepository(test_db_session)
        wechat_user = Auth(
            phone=None,
            is_guest=False,
            wechat_openid="test_wechat_openid_123",
            jwt_version=1
        )
        auth_repo.create(wechat_user)
        test_db_session.commit()

        # 步骤1: 用户登录获取JWT令牌
        login_response = test_client.post("/auth/login", json={
            "wechat_openid": "test_wechat_openid_123"
        })

        assert login_response.status_code == 200
        login_data = login_response.json()
        access_token = login_data["data"]["access_token"]

        # 步骤2: 发送绑定验证码
        bind_phone = "13800138002"
        send_response = test_client.post("/auth/sms/send", json={
            "phone": bind_phone,
            "scene": "bind"
        })

        assert send_response.status_code == 200

        # 步骤3: 验证验证码并绑定手机号
        verification = auth_repo.get_latest_unverified(bind_phone, "bind")
        verify_response = test_client.post("/auth/sms/verify", json={
            "phone": bind_phone,
            "code": verification.code,
            "scene": "bind"
        }, headers={"Authorization": f"Bearer {access_token}"})

        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["code"] == 200
        assert verify_data["data"]["upgraded"] is True
        assert verify_data["data"]["user_id"] == str(wechat_user.id)

        # 验证用户手机号已更新
        updated_user = auth_repo.get_by_id(wechat_user.id)
        assert updated_user.phone == bind_phone

    def test_rate_limiting_integration(self, test_client, mock_sms_client):
        """测试频率限制的集成效果"""
        phone = "13800138003"

        # 第一次发送应该成功
        response1 = test_client.post("/auth/sms/send", json={
            "phone": phone,
            "scene": "register"
        })
        assert response1.status_code == 200

        # 立即第二次发送应该被频率限制
        response2 = test_client.post("/auth/sms/send", json={
            "phone": phone,
            "scene": "register"
        })
        assert response2.status_code == 429
        error_data = response2.json()
        assert error_data["detail"]["error_code"] == "SMS_RATE_LIMIT"

    def test_daily_limit_integration(self, test_client, mock_sms_client):
        """测试每日限制的集成效果"""
        phone = "13800138004"

        # 发送5次验证码（达到每日限制）
        for i in range(5):
            response = test_client.post("/auth/sms/send", json={
                "phone": phone,
                "scene": "register"
            })
            if i < 4:  # 前4次应该成功
                assert response.status_code == 200
            else:  # 第5次应该被限制
                assert response.status_code == 429
                error_data = response.json()
                assert error_data["detail"]["error_code"] == "SMS_DAILY_LIMIT"

    def test_verification_code_expiration(self, test_client, mock_sms_client, test_db_session):
        """测试验证码过期机制"""
        phone = "13800138005"

        # 发送验证码
        send_response = test_client.post("/auth/sms/send", json={
            "phone": phone,
            "scene": "register"
        })
        assert send_response.status_code == 200

        # 手动修改验证码的创建时间，模拟过期
        auth_repo = AuthRepository(test_db_session)
        verification = auth_repo.get_latest_unverified(phone, "register")
        verification.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)  # 10分钟前
        test_db_session.commit()

        # 尝试验证过期的验证码
        verify_response = test_client.post("/auth/sms/verify", json={
            "phone": phone,
            "code": verification.code,
            "scene": "register"
        })

        assert verify_response.status_code == 400
        error_data = verify_response.json()
        assert error_data["detail"]["error_code"] == "VERIFICATION_EXPIRED"

    def test_wrong_verification_code_lockout(self, test_client, mock_sms_client, test_db_session):
        """测试验证码错误锁定机制"""
        phone = "13800138006"

        # 发送验证码
        send_response = test_client.post("/auth/sms/send", json={
            "phone": phone,
            "scene": "register"
        })
        assert send_response.status_code == 200

        # 连续输入错误验证码3次
        for i in range(3):
            verify_response = test_client.post("/auth/sms/verify", json={
                "phone": phone,
                "code": "wrong_code",
                "scene": "register"
            })
            assert verify_response.status_code == 400
            error_data = verify_response.json()
            if i < 2:  # 前2次是验证码错误
                assert error_data["detail"]["error_code"] == "INVALID_VERIFICATION_CODE"
            else:  # 第3次应该触发锁定
                assert error_data["detail"]["error_code"] == "ACCOUNT_LOCKED"

        # 验证账号已被锁定
        auth_repo = AuthRepository(test_db_session)
        verification = auth_repo.get_latest_unverified(phone, "register")
        assert verification.locked_until is not None
        assert verification.locked_until > datetime.now(timezone.utc)

    def test_phone_already_exists_error(self, test_client, mock_sms_client, test_db_session):
        """测试手机号已存在错误"""
        phone = "13800138007"

        # 预先创建用户
        auth_repo = AuthRepository(test_db_session)
        existing_user = Auth(
            phone=phone,
            is_guest=False,
            wechat_openid=None,
            jwt_version=1
        )
        auth_repo.create(existing_user)
        test_db_session.commit()

        # 尝试为已存在的手机号发送注册验证码
        send_response = test_client.post("/auth/sms/send", json={
            "phone": phone,
            "scene": "register"
        })

        assert send_response.status_code == 400
        error_data = send_response.json()
        assert error_data["detail"]["error_code"] == "PHONE_ALREADY_EXISTS"

    def test_phone_not_found_error(self, test_client, mock_sms_client):
        """测试手机号不存在错误"""
        phone = "13800138008"

        # 尝试为不存在的手机号发送登录验证码
        send_response = test_client.post("/auth/sms/send", json={
            "phone": phone,
            "scene": "login"
        })

        assert send_response.status_code == 400
        error_data = send_response.json()
        assert error_data["detail"]["error_code"] == "PHONE_NOT_FOUND"

    def test_phone_already_bound_error(self, test_client, mock_sms_client, test_db_session):
        """测试手机号已被绑定错误"""
        phone = "13800138009"
        wechat_openid = "existing_wechat_user"

        # 预先创建已绑定手机号的用户
        auth_repo = AuthRepository(test_db_session)
        bound_user = Auth(
            phone=phone,
            is_guest=False,
            wechat_openid="different_wechat_user",
            jwt_version=1
        )
        auth_repo.create(bound_user)

        # 创建尝试绑定的用户
        new_user = Auth(
            phone=None,
            is_guest=False,
            wechat_openid=wechat_openid,
            jwt_version=1
        )
        auth_repo.create(new_user)
        test_db_session.commit()

        # 新用户登录获取令牌
        login_response = test_client.post("/auth/login", json={
            "wechat_openid": wechat_openid
        })
        access_token = login_response.json()["data"]["access_token"]

        # 尝试绑定已被其他用户绑定的手机号
        send_response = test_client.post("/auth/sms/send", json={
            "phone": phone,
            "scene": "bind"
        }, headers={"Authorization": f"Bearer {access_token}"})

        assert send_response.status_code == 400
        error_data = send_response.json()
        assert error_data["detail"]["error_code"] == "PHONE_ALREADY_BOUND"

    def test_guest_upgrade_flow(self, test_client, mock_sms_client, test_db_session):
        """测试游客账号升级流程"""
        # 步骤1: 创建游客账号
        guest_response = test_client.post("/auth/guest/init")
        assert guest_response.status_code == 200
        guest_data = guest_response.json()
        guest_token = guest_data["data"]["access_token"]
        guest_user_id = guest_data["data"]["user_id"]

        # 步骤2: 发送升级验证码
        upgrade_phone = "13800138010"
        send_response = test_client.post("/auth/sms/send", json={
            "phone": upgrade_phone,
            "scene": "bind"  # 使用bind场景进行升级
        }, headers={"Authorization": f"Bearer {guest_token}"})

        assert send_response.status_code == 200

        # 步骤3: 验证验证码并升级
        auth_repo = AuthRepository(test_db_session)
        verification = auth_repo.get_latest_unverified(upgrade_phone, "bind")

        upgrade_response = test_client.post("/auth/guest/upgrade", json={
            "wechat_openid": f"guest_upgrade_{upgrade_phone}"  # 使用手机号作为微信OpenID
        }, headers={"Authorization": f"Bearer {guest_token}"})

        # 注意：这里使用的是原有的guest/upgrade端点，而不是SMS验证
        # 在实际应用中，可能需要结合SMS验证和guest升级流程

        assert upgrade_response.status_code == 200

    def test_concurrent_verification_handling(self, test_client, mock_sms_client, test_db_session):
        """测试并发验证处理"""
        phone = "13800138011"

        # 发送两次验证码（模拟并发请求）
        send_response1 = test_client.post("/auth/sms/send", json={
            "phone": phone,
            "scene": "register"
        })
        send_response2 = test_client.post("/auth/sms/send", json={
            "phone": phone,
            "scene": "register"
        })

        # 两次请求都应该成功（但第二次会被频率限制）
        assert send_response1.status_code == 200
        assert send_response2.status_code == 429  # 频率限制

        # 验证只有一个有效的验证码
        auth_repo = AuthRepository(test_db_session)
        verification = auth_repo.get_latest_unverified(phone, "register")
        assert verification is not None

        # 验证最新的验证码有效
        verify_response = test_client.post("/auth/sms/verify", json={
            "phone": phone,
            "code": verification.code,
            "scene": "register"
        })

        assert verify_response.status_code == 200

    def test_jwt_token_validation_after_sms_auth(self, test_client, mock_sms_client, test_db_session):
        """测试SMS认证后JWT令牌的有效性"""
        phone = "13800138012"

        # 完成SMS注册流程
        send_response = test_client.post("/auth/sms/send", json={
            "phone": phone,
            "scene": "register"
        })

        auth_repo = AuthRepository(test_db_session)
        verification = auth_repo.get_latest_unverified(phone, "register")

        verify_response = test_client.post("/auth/sms/verify", json={
            "phone": phone,
            "code": verification.code,
            "scene": "register"
        })

        assert verify_response.status_code == 200
        token_data = verify_response.json()["data"]
        access_token = token_data["access_token"]

        # 使用令牌访问需要认证的端点
        refresh_response = test_client.post("/auth/refresh", json={
            "refresh_token": token_data["refresh_token"]
        })

        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert refresh_data["code"] == 200
        assert refresh_data["data"]["access_token"] is not None
        assert refresh_data["data"]["access_token"] != access_token  # 新的访问令牌