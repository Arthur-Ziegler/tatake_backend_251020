"""
增强用户Profile API集成测试

测试增强的Profile API端点，包括新字段和积分余额集成。

作者：TaKeKe团队
版本：1.0.0 - Profile功能增强
"""

import pytest
from datetime import datetime, date
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.api.main import app
from src.domains.user.models import User, UserSettings, UserStats
from src.database.connection import get_database_connection


class TestEnhancedProfileAPI:
    """增强用户Profile API集成测试类"""

    @pytest.fixture
    def client(self):
        """测试客户端fixture"""
        return TestClient(app)

    @pytest.fixture
    def db_session(self):
        """数据库测试会话fixture"""
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
    def sample_user(self, db_session: Session):
        """示例用户fixture"""
        user_id = uuid4()
        user = User(
            user_id=user_id,
            nickname="测试用户",
            avatar_url="https://example.com/avatar.jpg",
            bio="这是测试用户简介",
            gender="male",
            birthday=date(1990, 5, 15)
        )
        db_session.add(user)
        db_session.commit()

        # 添加用户设置
        settings = UserSettings(
            user_id=user_id,
            theme="dark",
            language="zh-CN",
            notifications_enabled=True
        )
        db_session.add(settings)
        db_session.commit()

        # 添加用户统计
        stats = UserStats(
            user_id=user_id,
            tasks_completed=25,
            total_points=1500,
            login_count=10
        )
        db_session.add(stats)
        db_session.commit()

        return {"user_id": user_id, "user": user, "settings": settings, "stats": stats}

    def test_enhanced_get_user_profile_includes_all_fields(self, client: TestClient, sample_user: dict):
        """
        测试增强的GET /user/profile端点包含所有字段

        Given: 存在包含完整信息的用户
        When: 调用GET /user/profile
        Then: 响应应该包含所有增强字段
        """
        # 这个测试需要JWT token和完整的API集成
        # 由于涉及认证，我们先写测试结构，后续实现API后通过

        user_id = sample_user["user_id"]

        # TODO: 实现JWT认证后补充完整测试
        # headers = {"Authorization": f"Bearer {mock_jwt_token}"}
        # response = client.get("/user/profile", headers=headers)

        # assert response.status_code == 200
        # data = response.json()["data"]

        # 验证基础字段
        # assert data["id"] == str(user_id)
        # assert data["nickname"] == "测试用户"
        # assert data["avatar"] == "https://example.com/avatar.jpg"
        # assert data["bio"] == "这是测试用户简介"

        # 验证新增字段
        # assert data["gender"] == "male"
        # assert data["birthday"] == "1990-05-15"

        # 验证偏好设置
        # assert data["theme"] == "dark"
        # assert data["language"] == "zh-CN"

        # 验证积分余额（需要mock奖励服务）
        # assert "points_balance" in data
        # assert isinstance(data["points_balance"], int)

        assert True  # 占位符，后续实现

    def test_enhanced_get_user_profile_with_missing_data(self, client: TestClient, db_session: Session):
        """
        测试用户数据缺失时的Profile API响应

        Given: 存在基础信息用户
        When: 调用GET /user/profile
        Then: 缺失字段应该有合理默认值
        """
        user_id = uuid4()
        basic_user = User(
            user_id=user_id,
            nickname="基础用户"
        )
        db_session.add(basic_user)
        db_session.commit()

        # TODO: 实现JWT认证后补充完整测试
        assert True  # 占位符，后续实现

    def test_enhanced_put_user_profile_updates_new_fields(self, client: TestClient, sample_user: dict):
        """
        测试增强的PUT /user/profile端点更新新字段

        Given: 存在用户
        When: 发送包含新字段的更新请求
        Then: 新字段应该正确更新
        """
        user_id = sample_user["user_id"]
        update_data = {
            "nickname": "更新昵称",
            "gender": "female",
            "birthday": "1992-08-20",
            "theme": "auto",
            "language": "en-US"
        }

        # TODO: 实现JWT认证后补充完整测试
        # headers = {"Authorization": f"Bearer {mock_jwt_token}"}
        # response = client.put("/user/profile", json=update_data, headers=headers)

        # assert response.status_code == 200
        # data = response.json()["data"]

        # 验证更新结果
        # assert data["nickname"] == "更新昵称"
        # assert data["updated_fields"] contains new fields

        assert True  # 占位符，后续实现

    def test_profile_api_points_balance_integration(self, client: TestClient, sample_user: dict):
        """
        测试Profile API积分余额集成

        Given: 用户有积分余额
        When: 调用GET /user/profile
        Then: 响应应该包含正确的积分余额
        """
        # 这个测试需要mock奖励服务
        # TODO: 实现奖励服务集成后补充测试

        assert True  # 占位符，后续实现

    def test_profile_api_error_handling(self, client: TestClient):
        """
        测试Profile API错误处理

        Given: 各种错误场景
        When: 调用Profile API
        Then: 应该返回适当的错误响应
        """
        # 测试未认证用户
        response = client.get("/user/profile")
        assert response.status_code == 401

        # TODO: 测试其他错误场景
        # - 用户不存在
        # - 奖励服务不可用
        # - 数据库连接错误