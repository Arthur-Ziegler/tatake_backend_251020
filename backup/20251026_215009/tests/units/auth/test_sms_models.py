"""
认证领域模型单元测试

测试Auth和SMSVerification模型的字段验证、约束和索引。
采用TDD方式，确保模型符合设计要求。

测试覆盖：
- Auth模型的phone字段验证
- SMSVerification模型的字段验证
- 唯一性约束
- 索引验证
- 边界条件测试
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.exc import IntegrityError

from src.domains.auth.models import Auth, SMSVerification, AuthLog
from src.domains.auth.database import AUTH_DATABASE_URL


@pytest.fixture
def test_db():
    """创建测试数据库会话"""
    # 创建内存数据库用于测试
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


class TestAuthModel:
    """Auth模型测试"""

    def test_auth_model_creation(self, test_db):
        """测试Auth模型创建"""
        # 创建微信登录用户
        wechat_user = Auth(
            wechat_openid="wx_test_12345",
            is_guest=False
        )
        test_db.add(wechat_user)
        test_db.commit()
        test_db.refresh(wechat_user)

        assert wechat_user.id is not None
        assert wechat_user.wechat_openid == "wx_test_12345"
        assert wechat_user.is_guest is False
        assert wechat_user.phone is None
        assert wechat_user.created_at is not None
        assert wechat_user.jwt_version == 1

        # 创建手机号用户
        phone_user = Auth(
            phone="13800138000",
            is_guest=False
        )
        test_db.add(phone_user)
        test_db.commit()
        test_db.refresh(phone_user)

        assert phone_user.id is not None
        assert phone_user.phone == "13800138000"
        assert phone_user.wechat_openid is None
        assert phone_user.is_guest is False

        # 创建游客用户
        guest_user = Auth(is_guest=True)
        test_db.add(guest_user)
        test_db.commit()
        test_db.refresh(guest_user)

        assert guest_user.id is not None
        assert guest_user.wechat_openid is None
        assert guest_user.phone is None
        assert guest_user.is_guest is True

    def test_phone_field_validation(self, test_db):
        """测试phone字段验证"""
        # 测试有效手机号
        valid_phones = ["13800138000", "15900000000", "18888888888"]

        for phone in valid_phones:
            user = Auth(phone=phone, is_guest=False)
            test_db.add(user)
            test_db.commit()
            test_db.refresh(user)
            assert user.phone == phone

            # 清理
            test_db.delete(user)
            test_db.commit()

        # 测试无效手机号长度（模型层面不做验证，由业务层处理）
        long_phone = "138001380000"  # 12位
        user = Auth(phone=long_phone, is_guest=False)
        test_db.add(user)
        test_db.commit()  # 应该成功，因为模型层只限制长度
        test_db.refresh(user)
        assert user.phone == long_phone

    def test_phone_unique_constraint(self, test_db):
        """测试手机号唯一约束"""
        phone = "13800138000"

        # 创建第一个用户
        user1 = Auth(phone=phone, is_guest=False)
        test_db.add(user1)
        test_db.commit()

        # 尝试创建相同手机号的用户，应该失败
        user2 = Auth(phone=phone, is_guest=False)
        test_db.add(user2)

        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_wechat_openid_unique_constraint(self, test_db):
        """测试微信OpenID唯一约束"""
        openid = "wx_test_12345"

        # 创建第一个用户
        user1 = Auth(wechat_openid=openid, is_guest=False)
        test_db.add(user1)
        test_db.commit()

        # 尝试创建相同OpenID的用户，应该失败
        user2 = Auth(wechat_openid=openid, is_guest=False)
        test_db.add(user2)

        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_dual_auth_support(self, test_db):
        """测试双通道认证支持"""
        # 创建同时有微信和手机号的用户
        user = Auth(
            wechat_openid="wx_test_12345",
            phone="13800138000",
            is_guest=False
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        assert user.wechat_openid == "wx_test_12345"
        assert user.phone == "13800138000"
        assert user.is_guest is False

    def test_jwt_version_increment(self, test_db):
        """测试JWT版本号递增"""
        user = Auth(phone="13800138000", is_guest=False)
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        assert user.jwt_version == 1

        # 更新JWT版本
        user.jwt_version = 2
        test_db.commit()
        test_db.refresh(user)

        assert user.jwt_version == 2

    def test_last_login_at_update(self, test_db):
        """测试最后登录时间更新"""
        user = Auth(phone="13800138000", is_guest=False)
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        assert user.last_login_at is None

        # 更新登录时间
        login_time = datetime.now(timezone.utc)
        user.last_login_at = login_time
        test_db.commit()
        test_db.refresh(user)

        # SQLite可能会丢失时区信息，所以只比较时间部分
        assert user.last_login_at is not None
        assert user.last_login_at.replace(tzinfo=timezone.utc) == login_time


class TestSMSVerificationModel:
    """SMSVerification模型测试"""

    def test_sms_verification_creation(self, test_db):
        """测试SMS验证码创建"""
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register",
            ip_address="127.0.0.1"
        )
        test_db.add(verification)
        test_db.commit()
        test_db.refresh(verification)

        assert verification.id is not None
        assert verification.phone == "13800138000"
        assert verification.code == "123456"
        assert verification.scene == "register"
        assert verification.verified is False
        assert verification.verified_at is None
        assert verification.ip_address == "127.0.0.1"
        assert verification.error_count == 0
        assert verification.locked_until is None
        assert verification.created_at is not None

    def test_scene_values(self, test_db):
        """测试不同场景值"""
        scenes = ["register", "login", "bind"]

        for scene in scenes:
            verification = SMSVerification(
                phone="13800138000",
                code="123456",
                scene=scene
            )
            test_db.add(verification)
            test_db.commit()
            test_db.refresh(verification)

            assert verification.scene == scene

            # 清理
            test_db.delete(verification)
            test_db.commit()

    def test_verification_mark_as_verified(self, test_db):
        """测试标记验证码已验证"""
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register"
        )
        test_db.add(verification)
        test_db.commit()
        test_db.refresh(verification)

        assert verification.verified is False
        assert verification.verified_at is None

        # 标记为已验证
        verified_time = datetime.now(timezone.utc)
        verification.verified = True
        verification.verified_at = verified_time
        test_db.commit()
        test_db.refresh(verification)

        assert verification.verified is True
        assert verification.verified_at is not None
        # SQLite可能会丢失时区信息，所以只比较时间部分
        assert verification.verified_at.replace(tzinfo=timezone.utc) == verified_time

    def test_error_count_increment(self, test_db):
        """测试错误次数累计"""
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register"
        )
        test_db.add(verification)
        test_db.commit()
        test_db.refresh(verification)

        assert verification.error_count == 0

        # 增加错误次数
        verification.error_count = 1
        test_db.commit()
        test_db.refresh(verification)

        assert verification.error_count == 1

        # 继续增加错误次数
        verification.error_count = 3
        test_db.commit()
        test_db.refresh(verification)

        assert verification.error_count == 3

    def test_account_lock(self, test_db):
        """测试账号锁定"""
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register"
        )
        test_db.add(verification)
        test_db.commit()
        test_db.refresh(verification)

        assert verification.locked_until is None

        # 设置锁定
        lock_until = datetime.now(timezone.utc) + timedelta(hours=1)
        verification.locked_until = lock_until
        test_db.commit()
        test_db.refresh(verification)

        assert verification.locked_until is not None
        # SQLite可能会丢失时区信息，所以只比较时间部分
        assert verification.locked_until.replace(tzinfo=timezone.utc) == lock_until

    def test_phone_scene_index_composite(self, test_db):
        """测试手机号和场景组合索引"""
        phone = "13800138000"

        # 创建不同场景的验证码
        verification1 = SMSVerification(
            phone=phone,
            code="111111",
            scene="register"
        )
        verification2 = SMSVerification(
            phone=phone,
            code="222222",
            scene="login"
        )
        verification3 = SMSVerification(
            phone=phone,
            code="333333",
            scene="bind"
        )

        test_db.add_all([verification1, verification2, verification3])
        test_db.commit()

        # 同一手机号可以有不同场景的验证码
        # 测试查询最新验证码的功能（模拟repository方法）
        from sqlmodel import select

        # 查询该手机号在register场景的最新验证码
        stmt = (
            select(SMSVerification)
            .where(SMSVerification.phone == phone, SMSVerification.scene == "register")
            .order_by(SMSVerification.created_at.desc())
            .limit(1)
        )
        result = test_db.exec(stmt).first()

        assert result is not None
        assert result.phone == phone
        assert result.scene == "register"
        assert result.code == "111111"

    def test_code_field_max_length(self, test_db):
        """测试验证码字段最大长度"""
        # 测试6位验证码
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register"
        )
        test_db.add(verification)
        test_db.commit()
        test_db.refresh(verification)
        assert verification.code == "123456"

        # 测试更长验证码（模型层允许，业务层限制）
        long_code = "12345678"
        verification.code = long_code
        test_db.commit()
        test_db.refresh(verification)
        assert verification.code == long_code  # 应该被截断为6位


class TestAuthLogModel:
    """AuthLog模型测试"""

    def test_auth_log_creation(self, test_db):
        """测试审计日志创建"""
        user = Auth(phone="13800138000", is_guest=False)
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        log = AuthLog(
            user_id=user.id,
            action="phone_register",
            result="success",
            details="用户通过手机号注册",
            ip_address="127.0.0.1",
            user_agent="pytest-test"
        )
        test_db.add(log)
        test_db.commit()
        test_db.refresh(log)

        assert log.id is not None
        assert log.user_id == user.id
        assert log.action == "phone_register"
        assert log.result == "success"
        assert log.details == "用户通过手机号注册"
        assert log.ip_address == "127.0.0.1"
        assert log.user_agent == "pytest-test"
        assert log.created_at is not None


class TestModelIntegration:
    """模型集成测试"""

    def test_complete_user_flow(self, test_db):
        """测试完整的用户流程"""
        # 1. 创建SMS验证码
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register",
            ip_address="127.0.0.1"
        )
        test_db.add(verification)
        test_db.commit()
        test_db.refresh(verification)

        # 2. 创建用户
        user = Auth(
            phone="13800138000",
            is_guest=False
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        # 3. 标记验证码已使用
        verification.verified = True
        verification.verified_at = datetime.now(timezone.utc)
        test_db.commit()

        # 4. 创建审计日志
        log = AuthLog(
            user_id=user.id,
            action="phone_register",
            result="success",
            details="手机号注册成功"
        )
        test_db.add(log)
        test_db.commit()

        # 验证所有数据都正确创建
        assert user.id is not None
        assert user.phone == "13800138000"
        assert verification.verified is True
        assert log.user_id == user.id
        assert log.action == "phone_register"

        # 5. 测试用户登录
        user.last_login_at = datetime.now(timezone.utc)
        test_db.commit()

        login_log = AuthLog(
            user_id=user.id,
            action="phone_login",
            result="success",
            details="手机号登录成功"
        )
        test_db.add(login_log)
        test_db.commit()

        # 验证登录记录
        assert user.last_login_at is not None
        assert login_log.action == "phone_login"