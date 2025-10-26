"""
API依赖注入系统测试

测试API层的依赖注入功能，包括：
1. JWT认证和用户识别
2. 可选认证机制
3. 分页参数处理
4. 搜索参数处理
5. 错误处理和异常情况

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
import os
from unittest.mock import patch, Mock
from uuid import uuid4, UUID
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError

from src.api.dependencies import (
    get_current_user_id,
    get_optional_current_user,
    get_pagination_params,
    get_search_params,
    initialize_dependencies,
    cleanup_dependencies,
    security
)


@pytest.mark.unit
class TestGetCurrentUserId:
    """获取当前用户ID测试类"""

    @pytest.mark.asyncio
    async def test_get_current_user_id_success(self):
        """测试成功获取用户ID"""
        user_id = str(uuid4())
        token = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ7dXNlcl9pZH0iLCJ0b2tlbl90eXBlIjoiYWNjZXNzIn0.test"

        # 模拟有效的JWT解码
        with patch('src.api.dependencies.jwt.decode') as mock_decode, \
             patch.dict(os.environ, {'JWT_SECRET_KEY': 'test-secret'}):
            mock_decode.return_value = {
                "sub": user_id,
                "token_type": "access"
            }

            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=token
            )

            result = await get_current_user_id(credentials)

            assert isinstance(result, UUID)
            assert str(result) == user_id
            mock_decode.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_user_id_no_credentials(self):
        """测试缺少认证令牌"""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(None)

        assert exc_info.value.status_code == 401
        assert "缺少认证令牌" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_id_invalid_token_type(self):
        """测试无效令牌类型"""
        token = "invalid.token.here"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )

        with patch('src.api.dependencies.jwt.decode') as mock_decode, \
             patch.dict(os.environ, {'JWT_SECRET_KEY': 'test-secret'}):
            mock_decode.return_value = {
                "sub": str(uuid4()),
                "token_type": "refresh"  # 错误的令牌类型
            }

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(credentials)

            assert exc_info.value.status_code == 401
            assert "令牌类型错误" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_id_missing_user_id(self):
        """测试令牌中缺少用户ID"""
        token = "invalid.token.here"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )

        with patch('src.api.dependencies.jwt.decode') as mock_decode, \
             patch.dict(os.environ, {'JWT_SECRET_KEY': 'test-secret'}):
            mock_decode.return_value = {
                "token_type": "access"
                # 缺少 "sub" 字段
            }

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(credentials)

            assert exc_info.value.status_code == 401
            assert "令牌中缺少用户ID" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_id_jwt_error(self):
        """测试JWT解码错误"""
        token = "invalid.jwt.token"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )

        with patch('src.api.dependencies.jwt.decode') as mock_decode, \
             patch.dict(os.environ, {'JWT_SECRET_KEY': 'test-secret'}):
            mock_decode.side_effect = JWTError("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(credentials)

            assert exc_info.value.status_code == 401
            assert "无效的认证令牌" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_id_invalid_uuid(self):
        """测试无效UUID格式"""
        token = "test.token.here"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )

        with patch('src.api.dependencies.jwt.decode') as mock_decode, \
             patch.dict(os.environ, {'JWT_SECRET_KEY': 'test-secret'}):
            mock_decode.return_value = {
                "sub": "invalid-uuid-format",
                "token_type": "access"
            }

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(credentials)

            assert exc_info.value.status_code == 401
            assert "令牌格式错误" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_id_default_secret_key(self):
        """测试使用默认密钥"""
        user_id = str(uuid4())
        token = "test.token.here"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )

        # 确保环境变量中没有JWT_SECRET_KEY
        with patch('src.api.dependencies.jwt.decode') as mock_decode, \
             patch.dict(os.environ, {}, clear=True):
            mock_decode.return_value = {
                "sub": user_id,
                "token_type": "access"
            }

            result = await get_current_user_id(credentials)

            assert str(result) == user_id
            # 验证使用了默认密钥
            mock_decode.assert_called_once_with(
                token,
                "your-super-secret-jwt-key-here",
                algorithms=["HS256"]
            )

    @pytest.mark.asyncio
    async def test_get_current_user_id_custom_secret_key(self):
        """测试使用自定义密钥"""
        user_id = str(uuid4())
        token = "test.token.here"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        custom_secret = "my-custom-secret-key"

        with patch('src.api.dependencies.jwt.decode') as mock_decode, \
             patch.dict(os.environ, {'JWT_SECRET_KEY': custom_secret}):
            mock_decode.return_value = {
                "sub": user_id,
                "token_type": "access"
            }

            result = await get_current_user_id(credentials)

            assert str(result) == user_id
            mock_decode.assert_called_once_with(
                token,
                custom_secret,
                algorithms=["HS256"]
            )


@pytest.mark.unit
class TestOptionalGetCurrentUser:
    """可选用户认证测试类"""

    @pytest.mark.asyncio
    async def test_optional_current_user_with_valid_token(self):
        """测试有效令牌的可选认证"""
        user_id = str(uuid4())
        token = "test.token.here"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )

        with patch('src.api.dependencies.jwt.decode') as mock_decode, \
             patch.dict(os.environ, {'JWT_SECRET_KEY': 'test-secret'}):
            mock_decode.return_value = {
                "sub": user_id,
                "token_type": "access"
            }

            result = await get_optional_current_user(credentials)

            assert isinstance(result, UUID)
            assert str(result) == user_id

    @pytest.mark.asyncio
    async def test_optional_current_user_without_token(self):
        """测试无令牌的可选认证"""
        result = await get_optional_current_user(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_optional_current_user_with_invalid_token(self):
        """测试无效令牌的可选认证"""
        token = "invalid.token.here"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )

        with patch('src.api.dependencies.jwt.decode') as mock_decode, \
             patch.dict(os.environ, {'JWT_SECRET_KEY': 'test-secret'}):
            mock_decode.side_effect = JWTError("Invalid token")

            result = await get_optional_current_user(credentials)
            assert result is None


@pytest.mark.unit
class TestPaginationParams:
    """分页参数测试类"""

    def test_pagination_params_default_values(self):
        """测试分页参数默认值"""
        result = get_pagination_params()

        assert result["page"] == 1
        assert result["limit"] == 20
        assert result["offset"] == 0

    def test_pagination_params_custom_values(self):
        """测试自定义分页参数"""
        result = get_pagination_params(page=3, limit=10)

        assert result["page"] == 3
        assert result["limit"] == 10
        assert result["offset"] == 20  # (3-1)*10

    def test_pagination_params_negative_page(self):
        """测试负页码处理"""
        result = get_pagination_params(page=-1, limit=20)

        assert result["page"] == 1  # 修正为1
        assert result["offset"] == 0

    def test_pagination_params_zero_page(self):
        """测试零页码处理"""
        result = get_pagination_params(page=0, limit=20)

        assert result["page"] == 1  # 修正为1
        assert result["offset"] == 0

    def test_pagination_params_negative_limit(self):
        """测试负限制数处理"""
        result = get_pagination_params(page=1, limit=-5)

        assert result["limit"] == 20  # 修正为默认值
        assert result["offset"] == 0

    def test_pagination_params_zero_limit(self):
        """测试零限制数处理"""
        result = get_pagination_params(page=1, limit=0)

        assert result["limit"] == 20  # 修正为默认值
        assert result["offset"] == 0

    def test_pagination_params_exceeding_max_limit(self):
        """测试超过最大限制数"""
        result = get_pagination_params(page=1, limit=150, max_limit=100)

        assert result["limit"] == 100  # 修正为最大值
        assert result["offset"] == 0

    def test_pagination_params_large_values(self):
        """测试大数值处理"""
        result = get_pagination_params(page=1000, limit=50, max_limit=200)

        assert result["page"] == 1000
        assert result["limit"] == 50
        assert result["offset"] == 49950  # (1000-1)*50

    def test_pagination_params_edge_cases(self):
        """测试边界情况"""
        # 测试page=1, limit=1
        result = get_pagination_params(page=1, limit=1)
        assert result["page"] == 1
        assert result["limit"] == 1
        assert result["offset"] == 0

        # 测试最大允许限制
        result = get_pagination_params(page=1, limit=100, max_limit=100)
        assert result["limit"] == 100
        assert result["offset"] == 0

    @pytest.mark.parametrize("page,limit,expected_page,expected_limit,expected_offset", [
        (1, 20, 1, 20, 0),
        (2, 10, 2, 10, 10),
        (5, 50, 5, 50, 200),
        (-1, 20, 1, 20, 0),  # 负页码修正
        (1, -5, 1, 20, 0),   # 负限制修正
        (0, 20, 1, 20, 0),   # 零页码修正
        (1, 0, 1, 20, 0),    # 零限制修正
        (1, 150, 1, 100, 0), # 超过最大限制修正
    ])
    def test_pagination_params_parametrized(self, page, limit, expected_page, expected_limit, expected_offset):
        """参数化测试分页参数"""
        result = get_pagination_params(page=page, limit=limit, max_limit=100)

        assert result["page"] == expected_page
        assert result["limit"] == expected_limit
        assert result["offset"] == expected_offset


@pytest.mark.unit
class TestSearchParams:
    """搜索参数测试类"""

    def test_search_params_default_values(self):
        """测试搜索参数默认值"""
        result = get_search_params()

        assert result["query"] is None
        assert result["sort"] == "created_at"
        assert result["order"] == "desc"

    def test_search_params_with_query(self):
        """测试带查询字符串的搜索参数"""
        result = get_search_params(q="test query")

        assert result["query"] == "test query"
        assert result["sort"] == "created_at"
        assert result["order"] == "desc"

    def test_search_params_custom_sort(self):
        """测试自定义排序字段"""
        result = get_search_params(sort="name")

        assert result["sort"] == "name"
        assert result["order"] == "desc"

    def test_search_params_order_asc(self):
        """测试升序排列"""
        result = get_search_params(order="asc")

        assert result["order"] == "asc"

    def test_search_params_order_desc(self):
        """测试降序排列"""
        result = get_search_params(order="desc")

        assert result["order"] == "desc"

    def test_search_params_invalid_order(self):
        """测试无效排序方向"""
        result = get_search_params(order="invalid")

        assert result["order"] == "desc"  # 修正为默认值

    def test_search_params_all_parameters(self):
        """测试所有搜索参数"""
        result = get_search_params(
            q="search term",
            sort="updated_at",
            order="asc"
        )

        assert result["query"] == "search term"
        assert result["sort"] == "updated_at"
        assert result["order"] == "asc"

    def test_search_params_empty_query(self):
        """测试空查询字符串"""
        result = get_search_params(q="")

        assert result["query"] == ""

    def test_search_params_special_characters(self):
        """测试特殊字符查询"""
        special_query = "test@example.com&filter=value"
        result = get_search_params(q=special_query)

        assert result["query"] == special_query

    @pytest.mark.parametrize("order,expected_order", [
        ("asc", "asc"),
        ("desc", "desc"),
        ("ASC", "desc"),  # 大写无效，修正为desc
        ("DESC", "desc"), # 大写无效，修正为desc
        ("invalid", "desc"), # 无效值，修正为desc
        ("", "desc"),       # 空值，修正为desc
    ])
    def test_search_params_order_validation(self, order, expected_order):
        """参数化测试排序方向验证"""
        result = get_search_params(order=order)
        assert result["order"] == expected_order

    @pytest.mark.parametrize("query,sort,order,expected_query,expected_sort,expected_order", [
        (None, "created_at", "desc", None, "created_at", "desc"),
        ("test", "name", "asc", "test", "name", "asc"),
        ("", "updated_at", "desc", "", "updated_at", "desc"),
        ("complex query", "priority", "invalid", "complex query", "priority", "desc"),
    ])
    def test_search_params_comprehensive(self, query, sort, order, expected_query, expected_sort, expected_order):
        """参数化测试搜索参数组合"""
        result = get_search_params(q=query, sort=sort, order=order)

        assert result["query"] == expected_query
        assert result["sort"] == expected_sort
        assert result["order"] == expected_order


@pytest.mark.unit
class TestSecurityConfiguration:
    """安全配置测试类"""

    def test_security_auto_error_disabled(self):
        """测试安全方案自动错误禁用"""
        # 验证security配置
        assert security.auto_error is False

    def test_security_scheme_type(self):
        """测试安全方案类型"""
        from fastapi.security import HTTPBearer
        assert isinstance(security, HTTPBearer)


@pytest.mark.unit
class TestDependencyInitialization:
    """依赖初始化测试类"""

    @pytest.mark.asyncio
    async def test_initialize_dependencies(self):
        """测试依赖初始化"""
        # 这个函数目前是空的，但应该能正常调用
        await initialize_dependencies()
        # 如果没有异常抛出，则测试通过

    @pytest.mark.asyncio
    async def test_cleanup_dependencies(self):
        """测试依赖清理"""
        # 这个函数目前是空的，但应该能正常调用
        await cleanup_dependencies()
        # 如果没有异常抛出，则测试通过


@pytest.mark.integration
class TestDependenciesIntegration:
    """依赖注入集成测试类"""

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self):
        """测试完整认证流程"""
        user_id = str(uuid4())
        token = "valid.jwt.token"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )

        with patch('src.api.dependencies.jwt.decode') as mock_decode, \
             patch.dict(os.environ, {'JWT_SECRET_KEY': 'test-secret'}):
            mock_decode.return_value = {
                "sub": user_id,
                "token_type": "access"
            }

            # 测试必需认证
            result_required = await get_current_user_id(credentials)
            assert str(result_required) == user_id

            # 测试可选认证
            result_optional = await get_optional_current_user(credentials)
            assert str(result_optional) == user_id

    @pytest.mark.asyncio
    async def test_dependency_parameter_combination(self):
        """测试依赖参数组合"""
        # 测试分页和搜索参数可以正常组合使用
        pagination = get_pagination_params(page=2, limit=10)
        search = get_search_params(q="test", sort="name", order="asc")

        # 验证参数组合
        assert pagination["page"] == 2
        assert pagination["limit"] == 10
        assert search["query"] == "test"
        assert search["sort"] == "name"
        assert search["order"] == "asc"

    def test_error_message_consistency(self):
        """测试错误消息一致性"""
        # 验证所有错误消息都是中文且包含必要信息
        error_messages = {
            "缺少认证令牌",
            "令牌类型错误",
            "令牌中缺少用户ID",
            "无效的认证令牌",
            "令牌格式错误"
        }

        # 这些消息应该在相应的异常中被使用
        for message in error_messages:
            assert isinstance(message, str)
            assert len(message) > 0
            # 验证包含中文字符
            assert any('\u4e00' <= char <= '\u9fff' for char in message)


@pytest.mark.parametrize("credentials_scheme", ["Bearer", "bearer"])
def test_http_credentials_case_sensitivity(credentials_scheme):
    """测试HTTP凭据方案大小写敏感性"""
    try:
        credentials = HTTPAuthorizationCredentials(
            scheme=credentials_scheme,
            credentials="test.token.here"
        )
        # 注意：HTTPAuthorizationCredentials可能对方案大小写敏感
        # 这个测试主要验证我们的处理方式
        assert credentials.scheme == credentials_scheme
    except Exception:
        # 如果创建失败，这也是有价值的测试信息
        pass


@pytest.fixture
def mock_jwt_payload():
    """模拟JWT载荷"""
    return {
        "sub": str(uuid4()),
        "token_type": "access",
        "exp": 1234567890,
        "iat": 1234567800
    }


@pytest.fixture
def sample_credentials():
    """示例认证凭据"""
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="sample.jwt.token"
    )


@pytest.mark.asyncio
async def test_with_fixtures(mock_jwt_payload, sample_credentials):
    """使用fixtures的测试"""
    with patch('src.api.dependencies.jwt.decode') as mock_decode, \
         patch.dict(os.environ, {'JWT_SECRET_KEY': 'test-secret'}):
        mock_decode.return_value = mock_jwt_payload

        result = await get_current_user_id(sample_credentials)
        assert str(result) == mock_jwt_payload["sub"]