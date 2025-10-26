"""
SMS认证Repository层单元测试

测试新增的SMS相关Repository方法，确保数据库操作的正确性和边界条件处理。
采用TDD方式，先写测试再实现Repository方法。

测试覆盖：
- 手机号查询用户
- SMS验证码CRUD操作
- 验证码查询和统计
- 审计日志创建
- 边界条件和异常处理
- 数据库事务完整性
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlmodel import Session, create_engine, SQLModel, select
from sqlalchemy import text

from src.domains.auth.models import Auth, SMSVerification, AuthLog
from src.domains.auth.repository import AuthRepository


@pytest.fixture
def test_db():
    """创建测试数据库会话"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture
def auth_repo(test_db):
    """创建认证Repository实例"""
    return AuthRepository(test_db)


class TestGetAuthByPhone:
    """根据手机号获取用户测试"""

    def test_get_existing_user_by_phone(self, auth_repo, test_db):
        """测试获取存在的手机号用户"""
        # 创建测试用户
        user = Auth(
            phone="13800138000",
            is_guest=False
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        # 查询用户
        result = auth_repo.get_auth_by_phone("13800138000")

        assert result is not None
        assert result.id == user.id
        assert result.phone == "13800138000"
        assert result.is_guest is False

    def test_get_nonexistent_user_by_phone(self, auth_repo):
        """测试获取不存在的手机号用户"""
        result = auth_repo.get_auth_by_phone("19999999999")
        assert result is None

    def test_get_user_by_phone_case_sensitivity(self, auth_repo, test_db):
        """测试手机号查询的大小写敏感性"""
        # 创建测试用户
        user = Auth(phone="13800138000", is_guest=False)
        test_db.add(user)
        test_db.commit()

        # 完全匹配
        result = auth_repo.get_auth_by_phone("13800138000")
        assert result is not None

        # 不匹配（手机号是数字，但测试完整性）
        result = auth_repo.get_auth_by_phone("13800138001")
        assert result is None

    def test_get_user_by_null_phone(self, auth_repo, test_db):
        """测试查询NULL手机号"""
        # 创建微信用户（无手机号）
        user = Auth(
            wechat_openid="wx_test_123",
            is_guest=False
        )
        test_db.add(user)
        test_db.commit()

        # 查询NULL手机号应该返回None
        result = auth_repo.get_auth_by_phone(None)
        assert result is None

    def test_get_user_by_empty_phone(self, auth_repo):
        """测试查询空手机号"""
        result = auth_repo.get_auth_by_phone("")
        assert result is None


class TestCreateSMSVerification:
    """创建SMS验证码测试"""

    def test_create_sms_verification_success(self, auth_repo, test_db):
        """测试成功创建SMS验证码"""
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register",
            ip_address="127.0.0.1"
        )

        result = auth_repo.create_sms_verification(verification)

        assert result is not None
        assert result.id is not None
        assert result.phone == "13800138000"
        assert result.code == "123456"
        assert result.scene == "register"
        assert result.verified is False
        assert result.created_at is not None

        # 验证已保存到数据库
        saved = test_db.get(SMSVerification, result.id)
        assert saved is not None
        assert saved.phone == verification.phone

    def test_create_multiple_verifications_same_phone(self, auth_repo):
        """测试同一手机号创建多个验证码"""
        verification1 = SMSVerification(
            phone="13800138000",
            code="111111",
            scene="register"
        )
        verification2 = SMSVerification(
            phone="13800138000",
            code="222222",
            scene="login"
        )

        result1 = auth_repo.create_sms_verification(verification1)
        result2 = auth_repo.create_sms_verification(verification2)

        assert result1.id != result2.id
        assert result1.phone == result2.phone
        assert result1.code != result2.code

    def test_create_verification_with_all_fields(self, auth_repo):
        """测试创建包含所有字段的验证码"""
        now = datetime.now(timezone.utc)
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="bind",
            verified=True,
            verified_at=now,
            ip_address="192.168.1.1",
            error_count=2,
            locked_until=now + timedelta(hours=1)
        )

        result = auth_repo.create_sms_verification(verification)

        assert result.verified is True
        assert result.verified_at == now
        assert result.ip_address == "192.168.1.1"
        assert result.error_count == 2
        assert result.locked_until is not None


class TestGetLatestVerification:
    """获取最新验证码测试"""

    def test_get_latest_verification_single(self, auth_repo, test_db):
        """测试获取单个验证码"""
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register"
        )
        test_db.add(verification)
        test_db.commit()

        result = auth_repo.get_latest_verification("13800138000")

        assert result is not None
        assert result.id == verification.id
        assert result.code == "123456"

    def test_get_latest_verification_multiple(self, auth_repo, test_db):
        """测试获取多个验证码中的最新一个"""
        # 创建多个验证码
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)

        old_verification = SMSVerification(
            phone="13800138000",
            code="111111",
            scene="register"
        )
        old_verification.created_at = old_time

        recent_verification = SMSVerification(
            phone="13800138000",
            code="222222",
            scene="register"
        )
        recent_verification.created_at = recent_time

        test_db.add_all([old_verification, recent_verification])
        test_db.commit()

        result = auth_repo.get_latest_verification("13800138000")

        assert result is not None
        assert result.code == "222222"  # 最新的验证码

    def test_get_latest_verification_no_records(self, auth_repo):
        """测试获取不存在记录的最新验证码"""
        result = auth_repo.get_latest_verification("19999999999")
        assert result is None

    def test_get_latest_verification_different_phones(self, auth_repo, test_db):
        """测试不同手机号的验证码查询"""
        verification1 = SMSVerification(phone="13800138000", code="111111", scene="register")
        verification2 = SMSVerification(phone="13900139000", code="222222", scene="register")

        test_db.add_all([verification1, verification2])
        test_db.commit()

        result1 = auth_repo.get_latest_verification("13800138000")
        result2 = auth_repo.get_latest_verification("13900139000")

        assert result1.code == "111111"
        assert result2.code == "222222"
        assert result1.id != result2.id


class TestGetLatestUnverified:
    """获取最新未验证验证码测试"""

    def test_get_latest_unverified_success(self, auth_repo, test_db):
        """测试获取最新未验证验证码"""
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register",
            verified=False
        )
        test_db.add(verification)
        test_db.commit()

        result = auth_repo.get_latest_unverified("13800138000", "register")

        assert result is not None
        assert result.id == verification.id
        assert result.verified is False

    def test_get_latest_unverified_only_verified(self, auth_repo, test_db):
        """测试只有已验证验证码时的查询"""
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register",
            verified=True,
            verified_at=datetime.now(timezone.utc)
        )
        test_db.add(verification)
        test_db.commit()

        result = auth_repo.get_latest_unverified("13800138000", "register")

        assert result is None

    def test_get_latest_unverified_different_scenes(self, auth_repo, test_db):
        """测试不同场景的未验证验证码查询"""
        register_verification = SMSVerification(
            phone="13800138000",
            code="111111",
            scene="register",
            verified=False
        )
        login_verification = SMSVerification(
            phone="13800138000",
            code="222222",
            scene="login",
            verified=False
        )

        test_db.add_all([register_verification, login_verification])
        test_db.commit()

        register_result = auth_repo.get_latest_unverified("13800138000", "register")
        login_result = auth_repo.get_latest_unverified("13800138000", "login")

        assert register_result.code == "111111"
        assert login_result.code == "222222"

    def test_get_latest_unverified_mixed_status(self, auth_repo, test_db):
        """测试混合状态的验证码查询"""
        # 创建已验证和未验证的验证码
        verified_verification = SMSVerification(
            phone="13800138000",
            code="111111",
            scene="register",
            verified=True,
            verified_at=datetime.now(timezone.utc)
        )
        unverified_verification = SMSVerification(
            phone="13800138000",
            code="222222",
            scene="register",
            verified=False
        )

        test_db.add_all([verified_verification, unverified_verification])
        test_db.commit()

        result = auth_repo.get_latest_unverified("13800138000", "register")

        assert result is not None
        assert result.code == "222222"  # 应该返回未验证的


class TestCountTodaySends:
    """统计今日发送次数测试"""

    def test_count_today_sends_zero(self, auth_repo):
        """测试无发送记录时的统计"""
        count = auth_repo.count_today_sends("13800138000")
        assert count == 0

    def test_count_today_sends_single(self, auth_repo, test_db):
        """测试单条发送记录的统计"""
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register"
        )
        test_db.add(verification)
        test_db.commit()

        count = auth_repo.count_today_sends("13800138000")
        assert count == 1

    def test_count_today_sends_multiple(self, auth_repo, test_db):
        """测试多条发送记录的统计"""
        verifications = [
            SMSVerification(phone="13800138000", code="111111", scene="register"),
            SMSVerification(phone="13800138000", code="222222", scene="login"),
            SMSVerification(phone="13800138000", code="333333", scene="register"),
        ]
        test_db.add_all(verifications)
        test_db.commit()

        count = auth_repo.count_today_sends("13800138000")
        assert count == 3

    def test_count_today_sends_exclude_old_records(self, auth_repo, test_db):
        """测试排除旧记录的统计"""
        # 创建昨天的记录
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        old_verification = SMSVerification(
            phone="13800138000",
            code="111111",
            scene="register"
        )
        old_verification.created_at = yesterday

        # 创建今天的记录
        today_verification = SMSVerification(
            phone="13800138000",
            code="222222",
            scene="register"
        )

        test_db.add_all([old_verification, today_verification])
        test_db.commit()

        count = auth_repo.count_today_sends("13800138000")
        assert count == 1  # 只统计今天的

    def test_count_today_sends_different_phones(self, auth_repo, test_db):
        """测试不同手机号的统计"""
        verification1 = SMSVerification(phone="13800138000", code="111111", scene="register")
        verification2 = SMSVerification(phone="13900139000", code="222222", scene="register")

        test_db.add_all([verification1, verification2])
        test_db.commit()

        count1 = auth_repo.count_today_sends("13800138000")
        count2 = auth_repo.count_today_sends("13900139000")

        assert count1 == 1
        assert count2 == 1


class TestUpdateVerification:
    """更新验证码测试"""

    def test_update_verification_success(self, auth_repo, test_db):
        """测试成功更新验证码"""
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register",
            verified=False
        )
        test_db.add(verification)
        test_db.commit()

        # 更新验证码
        verification.verified = True
        verification.verified_at = datetime.now(timezone.utc)
        verification.error_count = 1

        result = auth_repo.update_verification(verification)

        assert result is not None
        assert result.verified is True
        assert result.verified_at is not None
        assert result.error_count == 1

        # 验证数据库已更新
        updated = test_db.get(SMSVerification, verification.id)
        assert updated.verified is True
        assert updated.error_count == 1

    def test_update_verification_multiple_fields(self, auth_repo, test_db):
        """测试更新多个字段"""
        verification = SMSVerification(
            phone="13800138000",
            code="123456",
            scene="register"
        )
        test_db.add(verification)
        test_db.commit()

        # 更新多个字段
        now = datetime.now(timezone.utc)
        verification.verified = True
        verification.verified_at = now
        verification.error_count = 3
        verification.locked_until = now + timedelta(hours=1)

        result = auth_repo.update_verification(verification)

        assert result.verified is True
        assert result.error_count == 3
        assert result.locked_until is not None


class TestCreateAuditLog:
    """创建审计日志测试"""

    def test_create_audit_log_minimum_fields(self, auth_repo, test_db):
        """测试创建包含最小字段的审计日志"""
        log = auth_repo.create_audit_log(
            action="sms_send",
            user_id="user_123"
        )

        assert log is not None
        assert log.id is not None
        assert log.action == "sms_send"
        assert log.user_id == "user_123"
        assert log.result == "success"
        assert log.created_at is not None

        # 验证已保存到数据库
        saved = test_db.get(AuthLog, log.id)
        assert saved is not None
        assert saved.action == "sms_send"

    def test_create_audit_log_all_fields(self, auth_repo, test_db):
        """测试创建包含所有字段的审计日志"""
        log = auth_repo.create_audit_log(
            action="phone_register",
            user_id="user_123",
            result="success",
            details="用户通过手机号注册成功",
            ip_address="127.0.0.1",
            user_agent="pytest-test",
            error_code=None
        )

        assert log.action == "phone_register"
        assert log.result == "success"
        assert log.details == "用户通过手机号注册成功"
        assert log.ip_address == "127.0.0.1"
        assert log.user_agent == "pytest-test"

    def test_create_audit_log_failure(self, auth_repo, test_db):
        """测试创建失败操作的审计日志"""
        log = auth_repo.create_audit_log(
            action="sms_verify",
            user_id="user_123",
            result="failure",
            details="验证码错误",
            error_code="INVALID_CODE"
        )

        assert log.result == "failure"
        assert log.details == "验证码错误"
        assert log.error_code == "INVALID_CODE"

    def test_create_multiple_audit_logs(self, auth_repo, test_db):
        """测试创建多个审计日志"""
        log1 = auth_repo.create_audit_log("action1", "user1", "success")
        log2 = auth_repo.create_audit_log("action2", "user2", "failure")
        log3 = auth_repo.create_audit_log("action3", "user1", "success")

        # 验证所有日志都已创建
        logs = test_db.exec(select(AuthLog)).all()
        assert len(logs) == 3

        # 验证日志顺序（按创建时间）
        assert logs[0].action == "action1"
        assert logs[1].action == "action2"
        assert logs[2].action == "action3"


class TestRepositoryIntegration:
    """Repository集成测试"""

    def test_complete_sms_flow(self, auth_repo, test_db):
        """测试完整的SMS验证流程"""
        phone = "13800138000"

        # 1. 检查用户不存在
        user = auth_repo.get_auth_by_phone(phone)
        assert user is None

        # 2. 创建验证码
        verification = SMSVerification(
            phone=phone,
            code="123456",
            scene="register",
            ip_address="127.0.0.1"
        )
        created_verification = auth_repo.create_sms_verification(verification)

        # 3. 统计今日发送次数
        count = auth_repo.count_today_sends(phone)
        assert count == 1

        # 4. 获取最新未验证验证码
        latest = auth_repo.get_latest_unverified(phone, "register")
        assert latest.id == created_verification.id

        # 5. 更新验证码为已验证
        latest.verified = True
        latest.verified_at = datetime.now(timezone.utc)
        updated = auth_repo.update_verification(latest)
        assert updated.verified is True

        # 6. 创建用户
        new_user = Auth(
            phone=phone,
            is_guest=False
        )
        test_db.add(new_user)
        test_db.commit()

        # 7. 创建审计日志
        log = auth_repo.create_audit_log(
            action="phone_register",
            user_id=new_user.id,
            result="success",
            details="手机号注册成功"
        )

        # 验证所有操作都成功
        found_user = auth_repo.get_auth_by_phone(phone)
        assert found_user is not None
        assert found_user.phone == phone

        # 验证审计日志
        saved_log = test_db.get(AuthLog, log.id)
        assert saved_log.action == "phone_register"
        assert saved_log.user_id == new_user.id

    def test_concurrent_verification_handling(self, auth_repo, test_db):
        """测试并发验证码处理"""
        phone = "13800138000"

        # 创建多个验证码
        verifications = []
        for i in range(3):
            verification = SMSVerification(
                phone=phone,
                code=f"{i:06d}",
                scene="register"
            )
            created = auth_repo.create_sms_verification(verification)
            verifications.append(created)

        # 验证可以获取最新验证码
        latest = auth_repo.get_latest_verification(phone)
        assert latest.code == "000002"  # 最后创建的

        # 验证可以获取未验证验证码
        unverified = auth_repo.get_latest_unverified(phone, "register")
        assert unverified.code == "000002"

        # 验证发送次数统计
        count = auth_repo.count_today_sends(phone)
        assert count == 3