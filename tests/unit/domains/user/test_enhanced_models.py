"""
增强用户模型单元测试

遵循TDD原则，先定义测试用例，然后实现最小功能。
测试覆盖新增的gender和birthday字段，以及增强的UserSettings。

作者：TaKeKe团队
版本：1.0.0 - Profile功能增强
"""

import pytest
from datetime import datetime, date
from uuid import uuid4
from typing import Optional

from sqlmodel import Session, select
from src.domains.user.models import User, UserSettings, UserStats
from src.database.connection import get_database_connection


class TestEnhancedUserModel:
    """增强用户模型测试类"""

    @pytest.fixture
    def db_session(self):
        """测试数据库会话fixture"""
        # 使用内存数据库进行测试
        db_connection = get_database_connection()
        db_connection.database_url = "sqlite:///:memory:"
        engine = db_connection.get_engine()

        # 创建所有表
        from src.domains.user.models import User, UserSettings, UserStats, UserPreferences
        User.metadata.create_all(engine)
        UserSettings.metadata.create_all(engine)
        UserStats.metadata.create_all(engine)
        UserPreferences.metadata.create_all(engine)

        with db_connection.get_session() as session:
            yield session

    @pytest.fixture
    def sample_user_data(self):
        """示例用户数据fixture"""
        return {
            "user_id": uuid4(),
            "nickname": "测试用户",
            "avatar_url": "https://example.com/avatar.jpg",
            "bio": "这是测试用户简介",
            "gender": "male",
            "birthday": date(1990, 5, 15)
        }

    def test_user_model_with_new_fields(self, db_session: Session, sample_user_data: dict):
        """
        测试User模型包含新的gender和birthday字段

        Given: 有效的用户数据包含新字段
        When: 创建User实例
        Then: 新字段应该正确存储和检索
        """
        # 创建用户
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # 验证新字段存在且正确
        assert user.gender == sample_user_data["gender"]
        assert user.birthday == sample_user_data["birthday"]
        assert user.nickname == sample_user_data["nickname"]
        assert user.user_id == sample_user_data["user_id"]

    def test_user_model_without_optional_fields(self, db_session: Session):
        """
        测试User模型不包含可选字段时的行为

        Given: 基本用户数据不包含可选字段
        When: 创建User实例
        Then: 可选字段应该为None
        """
        basic_user_data = {
            "user_id": uuid4(),
            "nickname": "基本用户"
        }

        user = User(**basic_user_data)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # 验证可选字段为None
        assert user.gender is None
        assert user.birthday is None
        assert user.avatar_url is None
        assert user.bio is None

    def test_gender_field_validation(self, db_session: Session, sample_user_data: dict):
        """
        测试gender字段的验证规则

        Given: 用户数据
        When: 设置不同的gender值
        Then: 应该接受有效值，拒绝无效值
        """
        valid_genders = ["male", "female", "other", None]

        for gender in valid_genders:
            sample_user_data["gender"] = gender
            user = User(**sample_user_data)
            db_session.add(user)
            db_session.commit()

            assert user.gender == gender

            # 清理
            db_session.delete(user)
            db_session.commit()

    def test_birthday_field_validation(self, db_session: Session, sample_user_data: dict):
        """
        测试birthday字段的验证规则

        Given: 用户数据
        When: 设置不同的birthday值
        Then: 应该接受有效日期，拒绝未来日期
        """
        # 有效生日
        valid_birthday = date(1990, 5, 15)
        sample_user_data["birthday"] = valid_birthday

        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()

        assert user.birthday == valid_birthday

        # 测试None值
        sample_user_data["birthday"] = None
        user2 = User(**sample_user_data)
        db_session.add(user2)
        db_session.commit()

        assert user2.birthday is None


class TestEnhancedUserSettingsModel:
    """增强用户设置模型测试类"""

    @pytest.fixture
    def sample_settings_data(self):
        """示例设置数据fixture"""
        return {
            "user_id": uuid4(),
            "theme": "dark",
            "language": "en-US",
            "notifications_enabled": True,
            "privacy_level": "private"
        }

    def test_extended_theme_options(self, db_session: Session, sample_settings_data: dict):
        """
        测试扩展的主题选项

        Given: 用户设置数据
        When: 设置不同的主题值
        Then: 应该支持light, dark, auto等主题
        """
        valid_themes = ["light", "dark", "auto", "system"]

        for theme in valid_themes:
            sample_settings_data["theme"] = theme
            settings = UserSettings(**sample_settings_data)
            db_session.add(settings)
            db_session.commit()

            assert settings.theme == theme

            # 清理
            db_session.delete(settings)
            db_session.commit()

    def test_extended_language_options(self, db_session: Session, sample_settings_data: dict):
        """
        测试扩展的语言选项

        Given: 用户设置数据
        When: 设置不同的语言值
        Then: 应该支持zh-CN, en-US等语言
        """
        valid_languages = ["zh-CN", "en-US", "ja-JP", "ko-KR"]

        for language in valid_languages:
            sample_settings_data["language"] = language
            settings = UserSettings(**sample_settings_data)
            db_session.add(settings)
            db_session.commit()

            assert settings.language == language

            # 清理
            db_session.delete(settings)
            db_session.commit()


class TestUserStatsIntegration:
    """用户统计数据集成测试类"""

    def test_user_stats_creation(self, db_session: Session):
        """
        测试用户统计数据创建

        Given: 用户ID
        When: 创建UserStats实例
        Then: 统计数据应该正确初始化
        """
        user_id = uuid4()
        stats = UserStats(
            user_id=user_id,
            tasks_completed=10,
            total_points=500,
            login_count=5
        )

        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.user_id == user_id
        assert stats.tasks_completed == 10
        assert stats.total_points == 500
        assert stats.login_count == 5
        assert stats.created_at is not None
        assert stats.updated_at is not None

    def test_user_stats_update(self, db_session: Session):
        """
        测试用户统计数据更新

        Given: 现有的用户统计数据
        When: 更新统计信息
        Then: 统计数据应该正确更新
        """
        user_id = uuid4()
        stats = UserStats(user_id=user_id)
        db_session.add(stats)
        db_session.commit()

        # 更新统计
        stats.tasks_completed = 20
        stats.total_points = 1000
        stats.login_count = 10
        db_session.commit()
        db_session.refresh(stats)

        assert stats.tasks_completed == 20
        assert stats.total_points == 1000
        assert stats.login_count == 10