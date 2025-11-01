"""
增强用户Profile更新端点单元测试

测试新的增强Profile更新API端点功能。

作者：TaKeKe团队
版本：1.0.0 - Profile功能增强
"""

import pytest
from datetime import datetime, date
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.api.main import app
from src.domains.user.models import User, UserSettings
from src.api.dependencies import get_current_user_id
from src.domains.user.schemas import EnhancedUpdateProfileRequest


class TestEnhancedProfileUpdate:
    """增强用户Profile更新端点测试类"""

    @pytest.fixture
    def mock_user_id(self):
        """模拟用户ID fixture"""
        return uuid4()

    @pytest.fixture
    def authenticated_client(self, mock_user_id):
        """已认证的测试客户端fixture"""
        # Mock认证依赖，使用固定的用户ID
        app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        try:
            yield TestClient(app)
        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    @pytest.fixture
    def mock_session(self, mock_user_id):
        """模拟数据库会话fixture"""
        session = Mock(spec=Session)

        # 模拟用户数据
        mock_user = Mock()
        mock_user.user_id = mock_user_id
        mock_user.nickname = "测试用户"
        mock_user.avatar_url = "https://example.com/avatar.jpg"
        mock_user.bio = "这是测试用户简介"
        mock_user.gender = "male"
        mock_user.birthday = date(1990, 5, 15)
        mock_user.is_active = True
        mock_user.created_at = datetime.utcnow()

        # 模拟用户设置
        mock_settings = Mock()
        mock_settings.theme = "light"
        mock_settings.language = "zh-CN"

        # 模拟Repository
        mock_repo = Mock()
        mock_repo.get_by_id_with_auth.return_value = {
            "user": mock_user,
            "auth": Mock()  # 模拟认证用户
        }

        # 模拟UserSettings查询
        session.exec.return_value.first.return_value = mock_settings

        return session, mock_repo, mock_user, mock_settings

    def test_update_enhanced_profile_success_basic_fields(self, authenticated_client, mock_session, mock_user_id):
        """
        测试成功更新基础字段

        Given: 有效的用户数据和认证客户端
        When: 调用PUT /user/profile/enhanced更新基础字段
        Then: 应该成功更新并返回更新后的数据
        """
        session, mock_repo, mock_user, mock_settings = mock_session

        # Override dependencies
        from src.domains.user.repository import UserRepository
        from src.database import get_db_session

        app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        app.dependency_overrides[get_db_session] = lambda: session

        try:
            with patch('src.domains.user.router.UserRepository') as mock_user_repo_class:
                mock_user_repo_class.return_value = mock_repo

                # 模拟更新后的用户
                updated_user = Mock()
                updated_user.user_id = mock_user_id
                updated_user.nickname = "新昵称"
                updated_user.avatar_url = "https://example.com/new-avatar.jpg"
                updated_user.bio = "新的用户简介"
                updated_user.gender = "male"
                updated_user.birthday = date(1990, 5, 15)
                updated_user.is_active = True
                updated_user.created_at = datetime.utcnow()

                mock_repo.update_user.return_value = updated_user

                # 更新数据
                update_data = {
                    "nickname": "新昵称",
                    "avatar_url": "https://example.com/new-avatar.jpg",
                    "bio": "新的用户简介"
                }

                response = authenticated_client.put("/user/profile/enhanced", json=update_data)

                assert response.status_code == 200
                data = response.json()

                assert data["code"] == 200
                assert data["message"] == "更新成功"

                profile_data = data["data"]
                assert profile_data["id"] == str(mock_user_id)
                assert profile_data["nickname"] == "新昵称"
                assert profile_data["avatar_url"] == "https://example.com/new-avatar.jpg"
                assert profile_data["bio"] == "新的用户简介"
                assert "updated_fields" in profile_data
                assert "updated_at" in profile_data

        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    def test_update_enhanced_profile_success_new_fields(self, authenticated_client, mock_session, mock_user_id):
        """
        测试成功更新新增字段

        Given: 有效的用户数据和认证客户端
        When: 调用PUT /user/profile/enhanced更新性别、生日等新字段
        Then: 应该成功更新并返回更新后的数据
        """
        session, mock_repo, mock_user, mock_settings = mock_session

        # Override dependencies
        from src.database import get_db_session
        app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        app.dependency_overrides[get_db_session] = lambda: session

        try:
            with patch('src.domains.user.router.UserRepository') as mock_user_repo_class:
                mock_user_repo_class.return_value = mock_repo

                # 模拟更新后的用户
                updated_user = Mock()
                updated_user.user_id = mock_user_id
                updated_user.nickname = "测试用户"
                updated_user.avatar_url = "https://example.com/avatar.jpg"
                updated_user.bio = "这是测试用户简介"
                updated_user.gender = "female"
                updated_user.birthday = date(1985, 8, 20)
                updated_user.is_active = True
                updated_user.created_at = datetime.utcnow()

                mock_repo.update_user.return_value = updated_user

                # 更新数据
                update_data = {
                    "gender": "female",
                    "birthday": "1985-08-20"
                }

                response = authenticated_client.put("/user/profile/enhanced", json=update_data)

                assert response.status_code == 200
                data = response.json()

                assert data["code"] == 200
                assert data["message"] == "更新成功"

                profile_data = data["data"]
                assert profile_data["id"] == str(mock_user_id)
                assert profile_data["gender"] == "female"
                assert profile_data["birthday"] == "1985-08-20"
                assert "gender" in profile_data["updated_fields"]
                assert "birthday" in profile_data["updated_fields"]

        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    def test_update_enhanced_profile_success_settings_fields(self, authenticated_client, mock_session, mock_user_id):
        """
        测试成功更新偏好设置字段

        Given: 有效的用户数据和认证客户端
        When: 调用PUT /user/profile/enhanced更新主题、语言等设置字段
        Then: 应该成功更新并返回更新后的数据
        """
        session, mock_repo, mock_user, mock_settings = mock_session

        # Override dependencies
        from src.database import get_db_session
        app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        app.dependency_overrides[get_db_session] = lambda: session

        try:
            with patch('src.domains.user.router.UserRepository') as mock_user_repo_class:
                mock_user_repo_class.return_value = mock_repo

                # 更新数据
                update_data = {
                    "theme": "dark",
                    "language": "en-US"
                }

                response = authenticated_client.put("/user/profile/enhanced", json=update_data)

                assert response.status_code == 200
                data = response.json()

                assert data["code"] == 200
                assert data["message"] == "更新成功"

                profile_data = data["data"]
                assert profile_data["id"] == str(mock_user_id)
                assert profile_data["theme"] == "dark"
                assert profile_data["language"] == "en-US"
                assert "theme" in profile_data["updated_fields"]
                assert "language" in profile_data["updated_fields"]

        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    def test_update_enhanced_profile_invalid_gender(self, authenticated_client, mock_session, mock_user_id):
        """
        测试无效性别值

        Given: 无效的性别值
        When: 调用PUT /user/profile/enhanced
        Then: 应该返回400错误
        """
        session, mock_repo, mock_user, mock_settings = mock_session

        # Override dependencies
        from src.database import get_db_session
        app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        app.dependency_overrides[get_db_session] = lambda: session

        try:
            with patch('src.domains.user.router.UserRepository') as mock_user_repo_class:
                mock_user_repo_class.return_value = mock_repo

                # 更新数据 - 无效的性别
                update_data = {
                    "gender": "invalid_gender"
                }

                response = authenticated_client.put("/user/profile/enhanced", json=update_data)

                assert response.status_code == 200
                data = response.json()

                assert data["code"] == 400
                assert "性别值无效" in data["message"]

        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    def test_update_enhanced_profile_invalid_birthday(self, authenticated_client, mock_session, mock_user_id):
        """
        测试无效生日格式

        Given: 无效的生日格式
        When: 调用PUT /user/profile/enhanced
        Then: 应该返回400错误
        """
        session, mock_repo, mock_user, mock_settings = mock_session

        # Override dependencies
        from src.database import get_db_session
        app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        app.dependency_overrides[get_db_session] = lambda: session

        try:
            with patch('src.domains.user.router.UserRepository') as mock_user_repo_class:
                mock_user_repo_class.return_value = mock_repo

                # 更新数据 - 无效的生日格式
                update_data = {
                    "birthday": "invalid_date"
                }

                response = authenticated_client.put("/user/profile/enhanced", json=update_data)

                assert response.status_code == 200
                data = response.json()

                assert data["code"] == 400
                assert "生日格式无效" in data["message"]

        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    def test_update_enhanced_profile_invalid_theme(self, authenticated_client, mock_session, mock_user_id):
        """
        测试无效主题值

        Given: 无效的主题值
        When: 调用PUT /user/profile/enhanced
        Then: 应该返回400错误
        """
        session, mock_repo, mock_user, mock_settings = mock_session

        # Override dependencies
        from src.database import get_db_session
        app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        app.dependency_overrides[get_db_session] = lambda: session

        try:
            with patch('src.domains.user.router.UserRepository') as mock_user_repo_class:
                mock_user_repo_class.return_value = mock_repo

                # 更新数据 - 无效的主题
                update_data = {
                    "theme": "invalid_theme"
                }

                response = authenticated_client.put("/user/profile/enhanced", json=update_data)

                assert response.status_code == 200
                data = response.json()

                assert data["code"] == 400
                assert "主题值无效" in data["message"]

        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    def test_update_enhanced_profile_invalid_language(self, authenticated_client, mock_session, mock_user_id):
        """
        测试无效语言格式

        Given: 无效的语言格式
        When: 调用PUT /user/profile/enhanced
        Then: 应该返回400错误
        """
        session, mock_repo, mock_user, mock_settings = mock_session

        # Override dependencies
        from src.database import get_db_session
        app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        app.dependency_overrides[get_db_session] = lambda: session

        try:
            with patch('src.domains.user.router.UserRepository') as mock_user_repo_class:
                mock_user_repo_class.return_value = mock_repo

                # 更新数据 - 无效的语言格式
                update_data = {
                    "language": "invalid_language"
                }

                response = authenticated_client.put("/user/profile/enhanced", json=update_data)

                assert response.status_code == 200
                data = response.json()

                assert data["code"] == 400
                assert "语言格式无效" in data["message"]

        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    def test_update_enhanced_profile_user_not_found(self, authenticated_client, mock_session, mock_user_id):
        """
        测试用户不存在的情况

        Given: 不存在的用户ID
        When: 调用PUT /user/profile/enhanced
        Then: 应该返回404错误
        """
        session, mock_repo, mock_user, mock_settings = mock_session

        # Override dependencies
        from src.database import get_db_session
        app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        app.dependency_overrides[get_db_session] = lambda: session

        try:
            with patch('src.domains.user.router.UserRepository') as mock_user_repo_class:
                # 模拟用户不存在
                mock_repo = Mock()
                mock_repo.get_by_id_with_auth.return_value = None
                mock_user_repo_class.return_value = mock_repo

                # 更新数据
                update_data = {
                    "nickname": "新昵称"
                }

                response = authenticated_client.put("/user/profile/enhanced", json=update_data)

                assert response.status_code == 200
                data = response.json()

                assert data["code"] == 404
                assert data["message"] == "用户不存在"

        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    def test_update_enhanced_profile_unauthorized(self):
        """
        测试未授权访问

        Given: 无认证的客户端
        When: 调用PUT /user/profile/enhanced
        Then: 应该返回401错误
        """
        from fastapi.testclient import TestClient

        client = TestClient(app)
        update_data = {
            "nickname": "新昵称"
        }

        response = client.put("/user/profile/enhanced", json=update_data)
        assert response.status_code == 401

    def test_update_enhanced_profile_endpoint_exists(self, authenticated_client):
        """
        测试增强更新端点是否存在

        Given: 应用实例
        When: 检查路由配置
        Then: 端点应该正确配置
        """
        from fastapi.routing import APIRoute

        # 检查路由是否存在
        routes = [route.path for route in app.routes if isinstance(route, APIRoute)]
        assert "/user/profile/enhanced" in routes

        # 检查PUT方法
        for route in app.routes:
            if isinstance(route, APIRoute) and route.path == "/user/profile/enhanced":
                assert "PUT" in route.methods
                break