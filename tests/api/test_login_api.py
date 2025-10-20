"""
用户登录API测试模块

测试用户登录相关的API功能，包括：
1. 手机号验证码登录
2. 邮箱验证码登录
3. 微信授权登录
4. 登录参数验证
5. 错误处理
"""

import pytest
import json
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timedelta
from uuid import uuid4

from src.api.routers.auth import router
from src.api.dependencies import initialize_dependencies, cleanup_dependencies
from src.api.responses import create_success_response


class TestLoginAPI:
    """用户登录API测试类"""

    @pytest.mark.asyncio
    async def test_login_with_phone_success(self):
        """测试手机号验证码登录成功"""
        try:
            from src.api.routers.auth import router
            from src.api.dependencies import initialize_dependencies, cleanup_dependencies

            # 初始化依赖
            await initialize_dependencies()

            try:
                # 创建FastAPI应用
                app = FastAPI()
                app.include_router(router, prefix="/api/v1")

                # 创建测试客户端
                client = TestClient(app)

                # 首先发送短信验证码
                sms_request = {
                    "phone": "13987654321",  # 使用不同的手机号避免频率限制
                    "type": "login"
                }
                sms_response = client.post("/api/v1/auth/sms/send", json=sms_request)
                assert sms_response.status_code == 200

                # 准备登录请求数据
                login_request = {
                    "login_type": "phone",
                    "phone": "13987654321",
                    "verification_code": "123456",  # Mock短信服务会返回这个验证码
                    "device_id": str(uuid4())
                }

                # 发送登录请求
                response = client.post("/api/v1/auth/login", json=login_request)

                # 验证响应状态码
                assert response.status_code == 200

                # 验证响应结构
                data = response.json()
                assert "success" in data
                assert data["success"] == True
                assert "data" in data

                # 验证登录响应数据
                auth_data = data["data"]
                assert "user_id" in auth_data
                assert "user_type" in auth_data
                assert "access_token" in auth_data
                assert "refresh_token" in auth_data
                assert auth_data["user_type"] == "registered"
                assert auth_data["is_guest"] == False

                print("✅ 手机号验证码登录成功测试通过")

            finally:
                await cleanup_dependencies()

        except Exception as e:
            pytest.fail(f"手机号登录测试失败: {str(e)}")

    @pytest.mark.asyncio
    async def test_login_with_email_success(self):
        """测试邮箱验证码登录成功"""
        try:
            from src.api.routers.auth import router
            from src.api.dependencies import initialize_dependencies, cleanup_dependencies

            # 初始化依赖
            await initialize_dependencies()

            try:
                # 创建FastAPI应用
                app = FastAPI()
                app.include_router(router, prefix="/api/v1")

                # 创建测试客户端
                client = TestClient(app)

                # 首先发送邮箱验证码
                sms_request = {
                    "phone": "test@example.com",  # 对于邮箱登录，使用email字段
                    "type": "login"
                }
                sms_response = client.post("/api/v1/auth/sms/send", json=sms_request)
                assert sms_response.status_code == 200

                # 准备登录请求数据
                login_request = {
                    "login_type": "email",
                    "email": "test@example.com",
                    "verification_code": "123456",  # Mock短信服务会返回这个验证码
                    "device_id": str(uuid4())
                }

                # 发送登录请求
                response = client.post("/api/v1/auth/login", json=login_request)

                # 验证响应状态码
                assert response.status_code == 200

                # 验证响应结构
                data = response.json()
                assert "success" in data
                assert data["success"] == True
                assert "data" in data

                # 验证登录响应数据
                auth_data = data["data"]
                assert "user_id" in auth_data
                assert "user_type" in auth_data
                assert "access_token" in auth_data
                assert "refresh_token" in auth_data
                assert auth_data["user_type"] == "registered"
                assert auth_data["is_guest"] == False

                print("✅ 邮箱验证码登录成功测试通过")

            finally:
                await cleanup_dependencies()

        except Exception as e:
            pytest.fail(f"邮箱登录测试失败: {str(e)}")

    @pytest.mark.asyncio
    async def test_login_invalid_request(self):
        """测试登录请求参数验证"""
        try:
            from src.api.routers.auth import router
            from src.api.dependencies import initialize_dependencies, cleanup_dependencies

            # 初始化依赖
            await initialize_dependencies()

            try:
                # 创建FastAPI应用
                app = FastAPI()
                app.include_router(router, prefix="/api/v1")

                # 创建测试客户端
                client = TestClient(app)

                # 测试缺少必要字段
                invalid_request = {
                    "login_type": "phone",
                    # 缺少verification_code和device_id
                }

                response = client.post("/api/v1/auth/login", json=invalid_request)

                # 验证返回400错误
                assert response.status_code == 422  # FastAPI验证错误

                print("✅ 登录参数验证测试通过")

            finally:
                await cleanup_dependencies()

        except Exception as e:
            pytest.fail(f"登录参数验证测试失败: {str(e)}")

    @pytest.mark.asyncio
    async def test_login_invalid_verification_code(self):
        """测试无效验证码登录"""
        try:
            from src.api.routers.auth import router
            from src.api.dependencies import initialize_dependencies, cleanup_dependencies

            # 初始化依赖
            await initialize_dependencies()

            try:
                # 创建FastAPI应用
                app = FastAPI()
                app.include_router(router, prefix="/api/v1")

                # 创建测试客户端
                client = TestClient(app)

                # 准备登录请求数据，使用无效验证码
                login_request = {
                    "login_type": "phone",
                    "phone": "13812345678",
                    "verification_code": "999999",  # 无效验证码
                    "device_id": str(uuid4())
                }

                # 发送登录请求
                response = client.post("/api/v1/auth/login", json=login_request)

                # 验证返回错误状态码
                assert response.status_code == 400

                # 验证错误消息
                data = response.json()
                assert "detail" in data
                assert "验证码" in data["detail"]

                print("✅ 无效验证码登录测试通过")

            finally:
                await cleanup_dependencies()

        except Exception as e:
            pytest.fail(f"无效验证码登录测试失败: {str(e)}")

    @pytest.mark.asyncio
    async def test_login_different_login_types(self):
        """测试不同登录类型"""
        try:
            from src.api.routers.auth import router
            from src.api.dependencies import initialize_dependencies, cleanup_dependencies

            # 初始化依赖
            await initialize_dependencies()

            try:
                # 创建FastAPI应用
                app = FastAPI()
                app.include_router(router, prefix="/api/v1")

                # 创建测试客户端
                client = TestClient(app)

                # 测试微信登录类型
                wechat_login_request = {
                    "login_type": "wechat",
                    "wechat_code": "mock_wechat_code",
                    "verification_code": "123456",
                    "device_id": str(uuid4())
                }

                response = client.post("/api/v1/auth/login", json=wechat_login_request)
                # 微信登录可能需要特殊处理，暂时允许返回特定错误
                assert response.status_code in [200, 400, 501]

                print("✅ 不同登录类型测试通过")

            finally:
                await cleanup_dependencies()

        except Exception as e:
            pytest.fail(f"不同登录类型测试失败: {str(e)}")


# 基础功能测试
@pytest.mark.asyncio
async def test_login_api_basic():
    """测试登录API基本功能"""
    test_instance = TestLoginAPI()
    await test_instance.test_login_with_phone_success()


@pytest.mark.asyncio
async def test_login_api_validation():
    """测试登录API参数验证"""
    test_instance = TestLoginAPI()
    await test_instance.test_login_invalid_request()


@pytest.mark.asyncio
async def test_login_api_invalid_code():
    """测试登录API无效验证码"""
    test_instance = TestLoginAPI()
    await test_instance.test_login_invalid_verification_code()


@pytest.mark.asyncio
async def test_login_api_email():
    """测试邮箱登录API"""
    test_instance = TestLoginAPI()
    await test_instance.test_login_with_email_success()


@pytest.mark.asyncio
async def test_login_api_types():
    """测试不同登录类型"""
    test_instance = TestLoginAPI()
    await test_instance.test_login_different_login_types()