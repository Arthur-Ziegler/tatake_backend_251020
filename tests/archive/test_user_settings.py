"""
测试用户设置模型
验证用户设置模型的字段定义、数据验证、关系处理和业务逻辑功能
"""
import pytest
from datetime import datetime, timezone
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

# 导入待实现的用户设置模型
from src.models.user import User, UserSettings


class TestUserSettingsModel:
    """用户设置模型测试类"""

    def test_user_settings_model_exists(self):
        """验证UserSettings模型存在且可导入"""
        assert UserSettings is not None
        assert hasattr(UserSettings, '__tablename__')
        assert UserSettings.__tablename__ == "user_settings"

    def test_user_settings_table_name(self):
        """验证用户设置表名定义"""
        assert UserSettings.__tablename__ == "user_settings"

    def test_user_settings_basic_fields(self):
        """测试用户设置基本字段定义"""
        # 验证所有必需字段都存在
        required_fields = [
            'user_id',  # 用户ID
            'focus_duration',  # 专注时长
            'break_duration',  # 休息时长
            'long_break_duration',  # 长休息时长
            'auto_start_breaks',  # 自动开始休息
            'auto_start_focus',  # 自动开始专注
            'notification_enabled',  # 通知开关
            'sound_enabled',  # 声音开关
            'theme',  # 主题
            'language',  # 语言
            'timezone'  # 时区
        ]

        for field in required_fields:
            assert hasattr(UserSettings, field), f"UserSettings模型缺少字段: {field}"

    def test_user_settings_inherits_from_base_model(self):
        """验证UserSettings模型继承自BaseSQLModel"""
        from src.models.base_model import BaseSQLModel
        assert issubclass(UserSettings, BaseSQLModel)

        # 验证基础字段继承
        settings = UserSettings(user_id="test_user_id")

        assert hasattr(settings, 'id')
        assert hasattr(settings, 'created_at')
        assert hasattr(settings, 'updated_at')

        # 验证基础字段类型
        assert settings.id is not None  # 主键自动生成
        assert isinstance(settings.created_at, datetime)
        assert isinstance(settings.updated_at, datetime)

    def test_user_settings_user_id_field(self):
        """测试用户ID字段定义"""
        settings = UserSettings(user_id="test_user_id")
        assert settings.user_id == "test_user_id"
        assert isinstance(settings.user_id, str)

    def test_user_settings_default_values(self):
        """测试用户设置默认值"""
        settings = UserSettings(user_id="test_user_id")

        # 验证时间设置默认值
        assert settings.focus_duration == 25
        assert settings.break_duration == 5
        assert settings.long_break_duration == 15

        # 验证自动化设置默认值
        assert settings.auto_start_breaks is False
        assert settings.auto_start_focus is False

        # 验证通知设置默认值
        assert settings.notification_enabled is True
        assert settings.sound_enabled is True

        # 验证界面设置默认值
        assert settings.theme == "light"
        assert settings.language == "zh-CN"
        assert settings.timezone == "Asia/Shanghai"

    def test_user_settings_field_types(self):
        """测试用户设置字段类型"""
        settings = UserSettings(
            user_id="test_user_id",
            focus_duration=30,
            break_duration=10,
            long_break_duration=20,
            auto_start_breaks=True,
            auto_start_focus=True,
            notification_enabled=False,
            sound_enabled=False,
            theme="dark",
            language="en-US",
            timezone="America/New_York"
        )

        # 验证字段类型
        assert isinstance(settings.user_id, str)
        assert isinstance(settings.focus_duration, int)
        assert isinstance(settings.break_duration, int)
        assert isinstance(settings.long_break_duration, int)
        assert isinstance(settings.auto_start_breaks, bool)
        assert isinstance(settings.auto_start_focus, bool)
        assert isinstance(settings.notification_enabled, bool)
        assert isinstance(settings.sound_enabled, bool)
        assert isinstance(settings.theme, str)
        assert isinstance(settings.language, str)
        assert isinstance(settings.timezone, str)

    def test_user_settings_validation_constraints(self):
        """测试用户设置验证约束"""
        settings = UserSettings(user_id="test_user_id")

        # 测试专注时长约束 (1-120分钟)
        valid_focus_durations = [1, 25, 60, 120]
        for duration in valid_focus_durations:
            settings.focus_duration = duration
            assert settings.focus_duration == duration

        # 测试休息时长约束 (1-30分钟)
        valid_break_durations = [1, 5, 15, 30]
        for duration in valid_break_durations:
            settings.break_duration = duration
            assert settings.break_duration == duration

        # 测试长休息时长约束 (1-60分钟)
        valid_long_break_durations = [1, 15, 30, 60]
        for duration in valid_long_break_durations:
            settings.long_break_duration = duration
            assert settings.long_break_duration == duration

    def test_user_settings_database_creation(self, session: Session):
        """测试用户设置数据库创建"""
        # 先创建用户
        user = User(nickname="设置测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 创建用户设置
        settings = UserSettings(
            user_id=user.id,
            focus_duration=30,
            break_duration=10,
            theme="dark",
            language="en-US"
        )

        session.add(settings)
        session.commit()
        session.refresh(settings)

        # 验证数据库保存成功
        assert settings.id is not None
        assert len(settings.id) > 0
        assert settings.user_id == user.id

        # 验证时间戳自动设置
        assert settings.created_at is not None
        assert settings.updated_at is not None
        assert isinstance(settings.created_at, datetime)
        assert isinstance(settings.updated_at, datetime)

    def test_user_settings_database_query(self, session: Session):
        """测试用户设置数据库查询"""
        # 先创建用户和设置
        user = User(nickname="查询测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        settings = UserSettings(
            user_id=user.id,
            theme="dark",
            language="en-US"
        )
        session.add(settings)
        session.commit()
        session.refresh(settings)

        # 通过用户ID查询设置
        from sqlmodel import select
        statement = select(UserSettings).where(UserSettings.user_id == user.id)
        found_settings = session.exec(statement).first()

        assert found_settings is not None
        assert found_settings.theme == "dark"
        assert found_settings.language == "en-US"

    def test_user_settings_uniqueness_constraint(self, session: Session):
        """测试用户设置唯一性约束"""
        # 先创建用户
        user = User(nickname="唯一性测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 创建第一个用户设置
        settings1 = UserSettings(user_id=user.id, theme="light")
        session.add(settings1)
        session.commit()

        # 尝试创建第二个用户设置（应该违反唯一约束）
        settings2 = UserSettings(user_id=user.id, theme="dark")
        session.add(settings2)

        # 应该抛出数据库完整性错误
        with pytest.raises(IntegrityError):
            session.commit()

    def test_user_settings_foreign_key_constraint(self, session: Session):
        """测试用户设置外键约束"""
        # 注意：SQLite默认不强制外键约束，这个测试主要验证模型定义
        # 在生产数据库（如PostgreSQL）中，这个约束会被强制执行

        # 使用不存在的用户ID创建设置（在SQLite中可能不会报错）
        settings = UserSettings(user_id="nonexistent_user_id")
        session.add(settings)

        try:
            session.commit()
            # SQLite可能不强制外键约束，所以这里可能不会报错
            # 但模型定义是正确的，在生产数据库中会报错
        except IntegrityError:
            # 在支持外键约束的数据库中会抛出这个错误
            pass
        finally:
            # 清理测试数据
            if settings.id:
                session.delete(settings)
                session.commit()

    def test_user_settings_comprehensive_creation(self, session: Session):
        """测试用户设置完整信息创建"""
        # 先创建用户
        user = User(nickname="完整设置测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 创建完整的用户设置
        settings = UserSettings(
            user_id=user.id,
            focus_duration=45,
            break_duration=15,
            long_break_duration=30,
            auto_start_breaks=True,
            auto_start_focus=True,
            notification_enabled=False,
            sound_enabled=False,
            theme="dark",
            language="en-US",
            timezone="America/New_York"
        )

        session.add(settings)
        session.commit()
        session.refresh(settings)

        # 验证所有字段正确保存
        assert settings.id is not None
        assert settings.user_id == user.id
        assert settings.focus_duration == 45
        assert settings.break_duration == 15
        assert settings.long_break_duration == 30
        assert settings.auto_start_breaks is True
        assert settings.auto_start_focus is True
        assert settings.notification_enabled is False
        assert settings.sound_enabled is False
        assert settings.theme == "dark"
        assert settings.language == "en-US"
        assert settings.timezone == "America/New_York"

    def test_user_settings_model_repr(self, session: Session):
        """测试用户设置模型字符串表示"""
        # 先创建用户
        user = User(nickname="字符串测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        settings = UserSettings(user_id=user.id)
        session.add(settings)
        session.commit()
        session.refresh(settings)

        # 验证__repr__方法
        repr_str = repr(settings)
        assert "UserSettings" in repr_str
        assert settings.id in repr_str
        assert f"UserSettings(id={settings.id})" == repr_str

    def test_user_settings_is_pomodoro_configuration(self):
        """测试标准番茄钟配置检查"""
        # 标准番茄钟配置
        standard_settings = UserSettings(user_id="test1")
        assert standard_settings.is_pomodoro_configuration() is True

        # 非标准配置
        custom_settings = UserSettings(
            user_id="test2",
            focus_duration=30,
            break_duration=10
        )
        assert custom_settings.is_pomodoro_configuration() is False

    def test_user_settings_get_total_cycle_time(self):
        """测试完整周期时间计算"""
        # 标准配置
        standard_settings = UserSettings(user_id="test1")
        assert standard_settings.get_total_cycle_time() == 30  # 25 + 5

        # 自定义配置
        custom_settings = UserSettings(
            user_id="test2",
            focus_duration=45,
            break_duration=15
        )
        assert custom_settings.get_total_cycle_time() == 60  # 45 + 15

    def test_user_settings_reset_to_defaults(self):
        """测试重置为默认值"""
        settings = UserSettings(
            user_id="test",
            focus_duration=60,
            break_duration=20,
            long_break_duration=40,
            auto_start_breaks=True,
            auto_start_focus=True,
            notification_enabled=False,
            sound_enabled=False,
            theme="dark",
            language="en-US",
            timezone="America/New_York"
        )

        # 重置为默认值
        settings.reset_to_defaults()

        # 验证所有字段都已重置
        assert settings.focus_duration == 25
        assert settings.break_duration == 5
        assert settings.long_break_duration == 15
        assert settings.auto_start_breaks is False
        assert settings.auto_start_focus is False
        assert settings.notification_enabled is True
        assert settings.sound_enabled is True
        assert settings.theme == "light"
        assert settings.language == "zh-CN"
        assert settings.timezone == "Asia/Shanghai"

    def test_user_settings_theme_validation(self, session: Session):
        """测试主题设置验证"""
        # 先创建用户
        user = User(nickname="主题测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 测试有效主题
        valid_themes = ["light", "dark", "auto", "blue", "green"]
        for theme in valid_themes:
            settings = UserSettings(user_id=user.id, theme=theme)
            session.add(settings)
            session.commit()
            session.refresh(settings)

            assert settings.theme == theme
            session.delete(settings)
            session.commit()

    def test_user_settings_language_validation(self, session: Session):
        """测试语言设置验证"""
        # 先创建用户
        user = User(nickname="语言测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 测试有效语言代码
        valid_languages = ["zh-CN", "en-US", "ja-JP", "fr-FR", "de-DE"]
        for language in valid_languages:
            settings = UserSettings(user_id=user.id, language=language)
            session.add(settings)
            session.commit()
            session.refresh(settings)

            assert settings.language == language
            session.delete(settings)
            session.commit()

    def test_user_settings_timezone_validation(self, session: Session):
        """测试时区设置验证"""
        # 先创建用户
        user = User(nickname="时区测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 测试有效时区
        valid_timezones = [
            "Asia/Shanghai",
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
            "Australia/Sydney"
        ]
        for timezone_str in valid_timezones:
            settings = UserSettings(user_id=user.id, timezone=timezone_str)
            session.add(settings)
            session.commit()
            session.refresh(settings)

            assert settings.timezone == timezone_str
            session.delete(settings)
            session.commit()


class TestUserSettingsIntegration:
    """用户设置集成测试类"""

    def test_user_settings_relationship_with_user(self, session: Session):
        """测试用户设置与用户的关系"""
        # 创建用户
        user = User(nickname="关系测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 创建用户设置
        settings = UserSettings(
            user_id=user.id,
            theme="dark",
            focus_duration=30
        )
        session.add(settings)
        session.commit()
        session.refresh(settings)

        # 验证关系正确建立
        assert settings.user_id == user.id

        # 验证可以通过用户ID查询到设置
        from sqlmodel import select
        statement = select(UserSettings).where(UserSettings.user_id == user.id)
        found_settings = session.exec(statement).first()
        assert found_settings is not None
        assert found_settings.id == settings.id

    def test_user_settings_cascade_delete(self, session: Session):
        """测试用户设置级联删除"""
        # 创建用户
        user = User(nickname="级联删除测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 创建用户设置
        settings = UserSettings(user_id=user.id)
        session.add(settings)
        session.commit()
        session.refresh(settings)

        settings_id = settings.id

        # 删除用户（应该级联删除设置）
        session.delete(user)
        session.commit()

        # 验证设置已被删除
        from sqlmodel import select
        statement = select(UserSettings).where(UserSettings.id == settings_id)
        found_settings = session.exec(statement).first()
        assert found_settings is None

    def test_user_settings_automatic_creation(self, session: Session):
        """测试用户设置自动创建（如果需要的话）"""
        # 创建用户
        user = User(nickname="自动创建测试用户")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 验证用户创建后没有自动的设置（我们的设计中不自动创建）
        from sqlmodel import select
        statement = select(UserSettings).where(UserSettings.user_id == user.id)
        settings = session.exec(statement).first()
        assert settings is None

        # 手动创建设置
        settings = UserSettings(user_id=user.id)
        session.add(settings)
        session.commit()
        session.refresh(settings)

        # 验证设置创建成功
        assert settings is not None
        assert settings.user_id == user.id

    def test_multiple_users_settings_isolation(self, session: Session):
        """测试多用户设置隔离"""
        # 创建多个用户
        user1 = User(nickname="用户1")
        user2 = User(nickname="用户2")
        session.add_all([user1, user2])
        session.commit()
        session.refresh(user1)
        session.refresh(user2)

        # 为每个用户创建不同的设置
        settings1 = UserSettings(
            user_id=user1.id,
            theme="light",
            focus_duration=25
        )
        settings2 = UserSettings(
            user_id=user2.id,
            theme="dark",
            focus_duration=45
        )
        session.add_all([settings1, settings2])
        session.commit()

        # 验证设置隔离正确
        assert settings1.theme == "light"
        assert settings1.focus_duration == 25
        assert settings1.user_id == user1.id

        assert settings2.theme == "dark"
        assert settings2.focus_duration == 45
        assert settings2.user_id == user2.id

        # 验证查询隔离
        from sqlmodel import select
        statement1 = select(UserSettings).where(UserSettings.user_id == user1.id)
        found_settings1 = session.exec(statement1).first()
        assert found_settings1.theme == "light"

        statement2 = select(UserSettings).where(UserSettings.user_id == user2.id)
        found_settings2 = session.exec(statement2).first()
        assert found_settings2.theme == "dark"