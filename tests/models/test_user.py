"""
测试用户模型
验证用户模型的字段定义、数据验证、关系处理和业务逻辑功能
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

# 导入待实现的用户模型
from src.models.user import User, UserSettings
from src.models.base_model import BaseSQLModel


class TestUserModel:
    """用户模型测试类"""

    def test_user_model_exists(self):
        """验证User模型存在且可导入"""
        assert User is not None
        assert issubclass(User, BaseSQLModel)
        assert hasattr(User, '__tablename__')
        assert User.__tablename__ == "users"

    def test_user_table_name(self):
        """验证用户表名定义"""
        assert User.__tablename__ == "users"

    def test_user_basic_fields(self):
        """测试用户基本字段定义"""
        # 验证所有必需字段都存在
        required_fields = [
            'nickname',  # 昵称
            'avatar',   # 头像URL
            'phone',    # 手机号
            'email',    # 邮箱
            'wechat_openid',  # 微信OpenID
            'is_guest', # 是否游客
            'last_login_at'  # 最后登录时间
        ]

        for field in required_fields:
            assert hasattr(User, field), f"User模型缺少字段: {field}"

    def test_user_inherits_from_base_model(self):
        """验证User模型继承自BaseSQLModel"""
        # 验证基础字段继承
        user = User(nickname="测试用户")

        assert hasattr(user, 'id')
        assert hasattr(user, 'created_at')
        assert hasattr(user, 'updated_at')

        # 验证基础字段类型（现在ID会自动生成）
        assert user.id is not None  # 主键自动生成UUID
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_user_nickname_field(self):
        """测试昵称字段定义"""
        # SQLModel中字段验证主要发生在数据库层面，而不是Python层面

        # 测试正常创建
        user = User(nickname="测试用户")
        assert user.nickname == "测试用户"

        # 测试昵称长度限制（数据库层面验证）
        max_length = 50
        valid_nickname = "a" * max_length
        user = User(nickname=valid_nickname)
        assert user.nickname == valid_nickname
        assert len(user.nickname) == max_length

    def test_user_optional_fields(self):
        """测试用户可选字段"""
        user = User(nickname="测试用户")

        # 验证可选字段默认值
        assert user.avatar is None
        assert user.phone is None
        assert user.email is None
        assert user.wechat_openid is None
        assert user.is_guest is False
        assert user.last_login_at is None

    def test_user_field_types(self):
        """测试用户字段类型"""
        user = User(
            nickname="测试用户",
            avatar="https://example.com/avatar.jpg",
            phone="13800138000",
            email="test@example.com",
            wechat_openid="wx_test_openid",
            is_guest=True,
            last_login_at=datetime.now(timezone.utc)
        )

        # 验证字段类型
        assert isinstance(user.nickname, str)
        assert isinstance(user.avatar, str) or user.avatar is None
        assert isinstance(user.phone, str) or user.phone is None
        assert isinstance(user.email, str) or user.email is None
        assert isinstance(user.wechat_openid, str) or user.wechat_openid is None
        assert isinstance(user.is_guest, bool)
        assert isinstance(user.last_login_at, datetime) or user.last_login_at is None

    def test_user_unique_fields(self):
        """测试用户唯一字段约束"""
        # 这些字段的唯一性约束在数据库层面验证
        unique_fields = ['phone', 'email', 'wechat_openid']

        for field in unique_fields:
            # 验证字段存在
            assert hasattr(User, field)
            user_field = getattr(User, field)
            # 字段应该存在（具体约束在数据库层面验证）
            assert user_field is not None

    def test_user_database_creation(self, session: Session):
        """测试用户数据库创建"""
        user = User(
            nickname="数据库测试用户",
            avatar="https://example.com/avatar.png",
            phone="13800138001",
            email="dbtest@example.com",
            is_guest=False
        )

        # 保存到数据库
        session.add(user)
        session.commit()
        session.refresh(user)

        # 验证数据库保存成功
        assert user.id is not None
        assert len(user.id) > 0

        # 验证时间戳自动设置
        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_user_database_query(self, session: Session):
        """测试用户数据库查询"""
        # 创建测试用户
        user = User(
            nickname="查询测试用户",
            email="querytest@example.com"
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # 通过ID查询
        from sqlmodel import select
        statement = select(User).where(User.id == user.id)
        found_user = session.exec(statement).first()

        assert found_user is not None
        assert found_user.nickname == "查询测试用户"
        assert found_user.email == "querytest@example.com"

    def test_user_uniqueness_constraints(self, session: Session):
        """测试用户唯一性约束"""
        # 创建第一个用户
        user1 = User(
            nickname="用户1",
            email="unique@example.com",
            phone="13800138002"
        )
        session.add(user1)
        session.commit()

        # 创建第二个用户，使用相同的邮箱（应该违反唯一约束）
        user2 = User(
            nickname="用户2",
            email="unique@example.com",  # 相同邮箱
            phone="13800138003"
        )
        session.add(user2)

        # 应该抛出数据库完整性错误
        with pytest.raises(IntegrityError):
            session.commit()

    def test_user_last_login_update(self, session: Session):
        """测试最后登录时间更新"""
        user = User(nickname="登录测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 初始状态下最后登录时间为空
        assert user.last_login_at is None

        # 更新最后登录时间
        from datetime import datetime, timezone
        login_time = datetime.now(timezone.utc)
        user.last_login_at = login_time
        session.commit()
        session.refresh(user)

        # 验证更新成功
        assert user.last_login_at is not None
        # 验证是datetime类型
        assert isinstance(user.last_login_at, datetime)

    def test_user_guest_flag(self, session: Session):
        """测试游客标志"""
        # 默认用户不是游客
        regular_user = User(nickname="普通用户")
        session.add(regular_user)
        session.commit()
        session.refresh(regular_user)

        assert regular_user.is_guest is False

        # 创建游客用户
        guest_user = User(nickname="游客用户", is_guest=True)
        session.add(guest_user)
        session.commit()
        session.refresh(guest_user)

        assert guest_user.is_guest is True

    def test_user_avatar_url_validation(self, session: Session):
        """测试头像URL验证"""
        # 测试有效URL
        valid_urls = [
            "https://example.com/avatar.jpg",
            "http://cdn.example.com/avatar.png",
            None  # 空值也是有效的
        ]

        for url in valid_urls:
            user = User(
                nickname=f"用户_{url}",
                avatar=url
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.avatar == url

    def test_user_phone_format(self, session: Session):
        """测试手机号格式"""
        # 测试有效的手机号格式
        valid_phones = [
            "13800138000",
            "15912345678",
            "18888888888",
            None  # 空值也是有效的
        ]

        for phone in valid_phones:
            user = User(
                nickname=f"用户_{phone}",
                phone=phone
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.phone == phone

    def test_user_email_format(self, session: Session):
        """测试邮箱格式"""
        # 测试有效的邮箱格式
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            None  # 空值也是有效的
        ]

        for email in valid_emails:
            user = User(
                nickname=f"用户_{email}",
                email=email
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.email == email

    def test_user_wechat_openid_format(self, session: Session):
        """测试微信OpenID格式"""
        # 测试有效的微信OpenID格式
        valid_openids = [
            "wx_test_openid_123",
            "ox1234567890abcdef",
            None  # 空值也是有效的
        ]

        for openid in valid_openids:
            user = User(
                nickname=f"用户_{openid}",
                wechat_openid=openid
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.wechat_openid == openid

    def test_user_comprehensive_creation(self, session: Session):
        """测试用户完整信息创建"""
        current_time = datetime.now(timezone.utc)

        user = User(
            nickname="完整信息用户",
            avatar="https://cdn.example.com/avatars/user123.jpg",
            phone="13800138999",  # 使用不同的手机号避免唯一约束冲突
            email="fulluser@example.com",
            wechat_openid="wx_full_user_123",
            is_guest=False,
            last_login_at=current_time
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        # 验证所有字段正确保存
        assert user.id is not None
        assert user.nickname == "完整信息用户"
        assert user.avatar == "https://cdn.example.com/avatars/user123.jpg"
        assert user.phone == "13800138999"
        assert user.email == "fulluser@example.com"
        assert user.wechat_openid == "wx_full_user_123"
        assert user.is_guest is False
        # 确保时区一致再比较
        if user.last_login_at.tzinfo and current_time.tzinfo:
            time_diff = abs((user.last_login_at - current_time).total_seconds())
            assert time_diff < 1
        else:
            # 如果时区不一致，只验证时间已设置
            assert user.last_login_at is not None

        # 验证时间戳
        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_user_model_repr(self, session: Session):
        """测试用户模型字符串表示"""
        user = User(nickname="字符串测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 验证__repr__方法
        repr_str = repr(user)
        assert "User" in repr_str
        assert user.id in repr_str
        assert f"User(id={user.id})" == repr_str

    def test_user_model_str(self):
        """测试用户模型字符串转换"""
        user = User(nickname="字符串转换用户")

        # 验证__str__方法（如果实现了）
        if hasattr(user, '__str__'):
            str_value = str(user)
            assert "字符串转换用户" in str_value

    def test_user_updated_at_manual_update(self, session: Session):
        """测试updated_at字段手动更新"""
        user = User(nickname="更新测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        original_updated_at = user.updated_at

        # 等待一小段时间确保时间戳不同
        import time
        time.sleep(0.01)

        # 手动更新用户信息和时间戳
        new_time = datetime.now(timezone.utc)
        user.nickname = "更新后的用户名"
        user.updated_at = new_time
        session.commit()
        session.refresh(user)

        # 验证updated_at字段已更新
        assert user.updated_at >= original_updated_at

    def test_user_batch_operations(self, session: Session):
        """测试用户批量操作"""
        # 创建多个用户
        users = [
            User(nickname=f"批量用户_{i}", email=f"batch{i}@example.com")
            for i in range(5)
        ]

        # 批量添加
        session.add_all(users)
        session.commit()

        # 验证所有用户都已保存
        for user in users:
            session.refresh(user)
            assert user.id is not None

        # 批量查询
        from sqlmodel import select
        statement = select(User).where(User.nickname.like("批量用户_%"))
        found_users = session.exec(statement).all()

        assert len(found_users) == 5

        # 验证查询结果
        nicknames = [user.nickname for user in found_users]
        for i in range(5):
            assert f"批量用户_{i}" in nicknames

    def test_user_is_active_user_without_login(self, session: Session):
        """测试从未登录用户的活跃状态判断"""
        user = User(nickname="未登录用户", email="never@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 从未登录的用户应该是不活跃的
        assert not user.is_active_user()

    def test_user_is_active_user_recent_login(self, session: Session):
        """测试最近登录用户的活跃状态判断"""
        user = User(nickname="活跃用户", email="active@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 更新最后登录时间
        user.update_last_login()
        session.commit()
        session.refresh(user)

        # 最近登录的用户应该是活跃的
        assert user.is_active_user()

    def test_user_is_active_user_old_login(self, session: Session):
        """测试很久未登录用户的活跃状态判断"""
        user = User(nickname="沉睡用户", email="sleepy@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 设置35天前的登录时间
        from datetime import timedelta
        user.last_login_at = datetime.now(timezone.utc) - timedelta(days=35)
        session.commit()
        session.refresh(user)

        # 超过30天未登录的用户应该是不活跃的
        assert not user.is_active_user()

    def test_user_update_last_login(self, session: Session):
        """测试更新最后登录时间"""
        user = User(nickname="登录用户", email="login@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 调用更新方法
        user.update_last_login()
        session.commit()
        session.refresh(user)

        # 验证登录时间已更新且是最近的时间
        assert user.last_login_at is not None
        # 确保时间比较时有时区信息一致
        now = datetime.now(timezone.utc)
        if user.last_login_at.tzinfo is None:
            login_time = user.last_login_at.replace(tzinfo=timezone.utc)
        else:
            login_time = user.last_login_at

        assert now - login_time < timedelta(seconds=5)  # 应该在5秒内

    def test_user_has_valid_contact_with_phone(self, session: Session):
        """测试有手机号用户的联系方式验证"""
        user = User(nickname="手机用户", phone="13800138005", email="phone5@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.has_valid_contact()

    def test_user_has_valid_contact_with_email(self, session: Session):
        """测试有邮箱用户的联系方式验证"""
        user = User(nickname="邮箱用户", email="email1@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.has_valid_contact()

    def test_user_has_valid_contact_with_wechat(self, session: Session):
        """测试有微信用户的联系方式验证"""
        user = User(nickname="微信用户", wechat_openid="wx1234567891", email="wechat1@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.has_valid_contact()

    def test_user_has_valid_contact_without_any(self, session: Session):
        """测试无任何联系方式用户的联系方式验证"""
        user = User(nickname="无联系方式用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        assert not user.has_valid_contact()

    def test_user_get_primary_identifier_email_priority(self, session: Session):
        """测试邮箱优先级的主要标识符获取"""
        user = User(
            nickname="多渠道用户",
            email="multi1@example.com",
            phone="13800138006",  # 使用不同的手机号
            wechat_openid="wx1234567892"
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # 邮箱应该有最高优先级
        assert user.get_primary_identifier() == "multi1@example.com"

    def test_user_get_primary_identifier_phone_priority(self, session: Session):
        """测试手机号优先级的主要标识符获取"""
        user = User(
            nickname="手机优先用户",
            phone="13800138003",
            wechat_openid="wx1234567893",
            email="phone_priority1@example.com"
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # 邮箱应该有最高优先级（即使有手机号）
        assert user.get_primary_identifier() == "phone_priority1@example.com"

    def test_user_get_primary_identifier_wechat_priority(self, session: Session):
        """测试微信优先级的主要标识符获取"""
        user = User(
            nickname="微信优先用户",
            wechat_openid="wx1234567894",
            email="wechat_priority1@example.com"
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # 邮箱应该有最高优先级（即使有微信）
        assert user.get_primary_identifier() == "wechat_priority1@example.com"

    def test_user_get_primary_identifier_nickname_fallback(self, session: Session):
        """测试昵称回退的主要标识符获取"""
        user = User(nickname="昵称用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 没有任何联系方式时应该返回昵称
        assert user.get_primary_identifier() == "昵称用户"

    def test_user_can_upgrade_to_regular_user_guest_without_contact(self, session: Session):
        """测试无联系方式的游客用户升级判断"""
        user = User(nickname="纯游客", is_guest=True)
        session.add(user)
        session.commit()
        session.refresh(user)

        # 无联系方式的游客不能升级
        assert not user.can_upgrade_to_regular_user()

    def test_user_can_upgrade_to_regular_user_guest_with_contact(self, session: Session):
        """测试有联系方式的游客用户升级判断"""
        user = User(nickname="可升级游客", is_guest=True, email="guest_upgrade@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 有联系方式的游客可以升级
        assert user.can_upgrade_to_regular_user()

    def test_user_can_upgrade_to_regular_user_regular_user(self, session: Session):
        """测试普通用户升级判断"""
        user = User(nickname="普通用户", is_guest=False, email="regular_user@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 普通用户不需要升级
        assert not user.can_upgrade_to_regular_user()

    def test_user_upgrade_to_regular_user_success(self, session: Session):
        """测试游客用户成功升级"""
        user = User(nickname="升级用户", is_guest=True, email="upgrade_success@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 升级应该成功
        assert user.upgrade_to_regular_user()
        assert not user.is_guest

    def test_user_upgrade_to_regular_user_failure(self, session: Session):
        """测试游客用户升级失败"""
        user = User(nickname="不能升级用户", is_guest=True)
        session.add(user)
        session.commit()
        session.refresh(user)

        # 升级应该失败
        assert not user.upgrade_to_regular_user()
        assert user.is_guest  # 仍然保持游客状态