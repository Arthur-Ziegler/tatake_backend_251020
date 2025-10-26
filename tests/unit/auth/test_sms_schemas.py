"""
SMS认证Schema单元测试

测试新增的SMS认证相关Schema，确保数据验证、字段类型和约束的正确性。
采用TDD方式，先写测试再实现Schema。

测试覆盖：
- SMSSendRequest请求模型验证
- SMSVerifyRequest请求模型验证
- SMSSendResponse响应模型验证
- SMSVerifyResponse响应模型验证
- PhoneBindResponse响应模型验证
- 字段类型验证和约束检查
- 序列化和反序列化测试
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from src.domains.auth.schemas import (
    # 请求模型
    SMSSendRequest,
    SMSVerifyRequest,
    # 响应模型
    SMSSendResponse,
    SMSVerifyResponse,
    PhoneBindResponse
)


class TestSMSSendRequest:
    """SMSSendRequest请求模型测试"""

    def test_valid_send_request(self):
        """测试有效的发送请求"""
        request = SMSSendRequest(
            phone="13800138000",
            scene="register"
        )

        assert request.phone == "13800138000"
        assert request.scene == "register"

    def test_valid_scene_values(self):
        """测试有效的场景值"""
        valid_scenes = ["register", "login", "bind"]

        for scene in valid_scenes:
            request = SMSSendRequest(
                phone="13900139000",
                scene=scene
            )
            assert request.scene == scene

    def test_invalid_phone_format(self):
        """测试无效的手机号格式"""
        invalid_phones = [
            "123",                    # 太短
            "123456789012",          # 太长
            "abcdefghijk",           # 非数字
            "138-0013-8000",         # 带分隔符
            "138 0013 8000",         # 带空格
            "+8613800138000",        # 带国际号码
            "",                      # 空字符串
        ]

        for phone in invalid_phones:
            with pytest.raises(ValidationError):
                SMSSendRequest(phone=phone, scene="register")

    def test_invalid_scene_values(self):
        """测试无效的场景值"""
        invalid_scenes = [
            "invalid",
            "REGISTER",  # 大写
            "login ",
            " register",
            "reg",
            ""
        ]

        for scene in invalid_scenes:
            with pytest.raises(ValidationError):
                SMSSendRequest(phone="13800138000", scene=scene)

    def test_missing_required_fields(self):
        """测试缺少必需字段"""
        # 缺少phone
        with pytest.raises(ValidationError):
            SMSSendRequest(scene="register")

        # 缺少scene
        with pytest.raises(ValidationError):
            SMSSendRequest(phone="13800138000")

        # 两个都缺少
        with pytest.raises(ValidationError):
            SMSSendRequest()

    def test_phone_length_validation(self):
        """测试手机号长度验证"""
        # 正确长度11位
        valid_request = SMSSendRequest(phone="13800138000", scene="register")
        assert valid_request.phone == "13800138000"

        # 错误长度10位
        with pytest.raises(ValidationError):
            SMSSendRequest(phone="1380013800", scene="register")

        # 错误长度12位
        with pytest.raises(ValidationError):
            SMSSendRequest(phone="138001380000", scene="register")

    def test_extra_fields_are_rejected(self):
        """测试拒绝额外字段"""
        with pytest.raises(ValidationError):
            SMSSendRequest(
                phone="13800138000",
                scene="register",
                extra_field="not_allowed"
            )


class TestSMSVerifyRequest:
    """SMSVerifyRequest请求模型测试"""

    def test_valid_verify_request(self):
        """测试有效的验证请求"""
        request = SMSVerifyRequest(
            phone="13800138000",
            code="123456",
            scene="register"
        )

        assert request.phone == "13800138000"
        assert request.code == "123456"
        assert request.scene == "register"

    def test_valid_code_formats(self):
        """测试有效的验证码格式"""
        valid_codes = ["000000", "123456", "999999"]

        for code in valid_codes:
            request = SMSVerifyRequest(
                phone="13800138000",
                code=code,
                scene="login"
            )
            assert request.code == code

    def test_invalid_code_formats(self):
        """测试无效的验证码格式"""
        invalid_codes = [
            "12345",    # 5位
            "1234567",  # 7位
            "abcdef",  # 非数字
            "12 345",  # 带空格
            "123-456", # 带分隔符
            "",        # 空字符串
        ]

        for code in invalid_codes:
            with pytest.raises(ValidationError):
                SMSVerifyRequest(
                    phone="13800138000",
                    code=code,
                    scene="register"
                )

    def test_invalid_verify_scenes(self):
        """测试无效的验证场景"""
        invalid_scenes = ["invalid", "REGISTER", "login ", " register", "reg", ""]

        for scene in invalid_scenes:
            with pytest.raises(ValidationError):
                SMSVerifyRequest(
                    phone="13800138000",
                    code="123456",
                    scene=scene
                )

    def test_missing_verify_fields(self):
        """测试缺少验证必需字段"""
        # 缺少phone
        with pytest.raises(ValidationError):
            SMSVerifyRequest(code="123456", scene="register")

        # 缺少code
        with pytest.raises(ValidationError):
            SMSVerifyRequest(phone="13800138000", scene="register")

        # 缺少scene
        with pytest.raises(ValidationError):
            SMSVerifyRequest(phone="13800138000", code="123456")

    def test_code_length_validation(self):
        """测试验证码长度验证"""
        # 正确长度6位
        valid_request = SMSVerifyRequest(
            phone="13800138000",
            code="123456",
            scene="register"
        )
        assert valid_request.code == "123456"

        # 错误长度5位
        with pytest.raises(ValidationError):
            SMSVerifyRequest(
                phone="13800138000",
                code="12345",
                scene="register"
            )

        # 错误长度7位
        with pytest.raises(ValidationError):
            SMSVerifyRequest(
                phone="13800138000",
                code="1234567",
                scene="register"
            )


class TestSMSSendResponse:
    """SMSSendResponse响应模型测试"""

    def test_valid_send_response(self):
        """测试有效的发送响应"""
        response = SMSSendResponse(
            expires_in=300,
            retry_after=60
        )

        assert response.expires_in == 300
        assert response.retry_after == 60

    def test_default_values(self):
        """测试默认值"""
        response = SMSSendResponse()

        assert response.expires_in == 300  # 默认5分钟
        assert response.retry_after == 60   # 默认60秒

    def test_custom_values(self):
        """测试自定义值"""
        response = SMSSendResponse(
            expires_in=600,  # 10分钟
            retry_after=120  # 2分钟
        )

        assert response.expires_in == 600
        assert response.retry_after == 120

    def test_negative_values_are_rejected(self):
        """测试拒绝负数值"""
        with pytest.raises(ValidationError):
            SMSSendResponse(expires_in=-1)

        with pytest.raises(ValidationError):
            SMSSendResponse(retry_after=-1)

    def test_zero_values_are_rejected(self):
        """测试拒绝零值"""
        with pytest.raises(ValidationError):
            SMSSendResponse(expires_in=0)

        with pytest.raises(ValidationError):
            SMSSendResponse(retry_after=0)

    def test_serialization(self):
        """测试序列化"""
        response = SMSSendResponse(
            expires_in=300,
            retry_after=60
        )

        data = response.model_dump()
        assert data["expires_in"] == 300
        assert data["retry_after"] == 60

    def test_deserialization(self):
        """测试反序列化"""
        data = {
            "expires_in": 300,
            "retry_after": 60
        }

        response = SMSSendResponse(**data)
        assert response.expires_in == 300
        assert response.retry_after == 60


class TestSMSVerifyResponse:
    """SMSVerifyResponse响应模型测试"""

    def test_valid_verify_response_register(self):
        """测试有效的验证响应（注册）"""
        response = SMSVerifyResponse(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            user_id="test_user_id",
            is_new_user=True
        )

        assert response.access_token == "test_access_token"
        assert response.refresh_token == "test_refresh_token"
        assert response.user_id == "test_user_id"
        assert response.is_new_user is True

    def test_valid_verify_response_login(self):
        """测试有效的验证响应（登录）"""
        response = SMSVerifyResponse(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            user_id="existing_user_id",
            is_new_user=False
        )

        assert response.is_new_user is False

    def test_default_is_new_user(self):
        """测试默认is_new_user值"""
        response = SMSVerifyResponse(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            user_id="test_user_id"
        )

        assert response.is_new_user is False  # 默认为False

    def test_missing_required_fields(self):
        """测试缺少必需字段"""
        # 缺少access_token
        with pytest.raises(ValidationError):
            SMSVerifyResponse(
                refresh_token="test_refresh_token",
                user_id="test_user_id"
            )

        # 缺少refresh_token
        with pytest.raises(ValidationError):
            SMSVerifyResponse(
                access_token="test_access_token",
                user_id="test_user_id"
            )

        # 缺少user_id
        with pytest.raises(ValidationError):
            SMSVerifyResponse(
                access_token="test_access_token",
                refresh_token="test_refresh_token"
            )

    def test_token_validation(self):
        """测试令牌格式验证"""
        # JWT令牌应该有足够的长度
        valid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

        response = SMSVerifyResponse(
            access_token=valid_token,
            refresh_token=valid_token,
            user_id="test_user_id"
        )

        assert len(response.access_token) > 20
        assert len(response.refresh_token) > 20

    def test_serialization_with_boolean(self):
        """测试包含布尔值的序列化"""
        response = SMSVerifyResponse(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            user_id="test_user_id",
            is_new_user=True
        )

        data = response.model_dump()
        assert data["is_new_user"] is True

    def test_complete_response_structure(self):
        """测试完整的响应结构"""
        response = SMSVerifyResponse(
            access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature",
            refresh_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.refresh.signature",
            user_id="550e8400-e29b-41d4-a716-446655440000",
            is_new_user=False
        )

        # 验证所有字段都有值
        assert response.access_token is not None
        assert response.refresh_token is not None
        assert response.user_id is not None
        assert isinstance(response.is_new_user, bool)


class TestPhoneBindResponse:
    """PhoneBindResponse响应模型测试"""

    def test_valid_bind_response(self):
        """测试有效的绑定响应"""
        response = PhoneBindResponse(
            user_id="test_user_id",
            phone="13800138000",
            upgraded=True
        )

        assert response.user_id == "test_user_id"
        assert response.phone == "13800138000"
        assert response.upgraded is True

    def test_bind_response_false_upgrade(self):
        """测试未升级的绑定响应"""
        response = PhoneBindResponse(
            user_id="test_user_id",
            phone="13800138000",
            upgraded=False
        )

        assert response.upgraded is False

    def test_default_upgraded_value(self):
        """测试默认upgraded值"""
        response = PhoneBindResponse(
            user_id="test_user_id",
            phone="13800138000"
        )

        assert response.upgraded is False  # 默认为False

    def test_missing_required_fields(self):
        """测试缺少必需字段"""
        # 缺少user_id
        with pytest.raises(ValidationError):
            PhoneBindResponse(phone="13800138000")

        # 缺少phone
        with pytest.raises(ValidationError):
            PhoneBindResponse(user_id="test_user_id")

    def test_invalid_phone_format_in_response(self):
        """测试响应中的无效手机号格式"""
        with pytest.raises(ValidationError):
            PhoneBindResponse(
                user_id="test_user_id",
                phone="invalid_phone"
            )

    def test_user_id_format_validation(self):
        """测试用户ID格式验证"""
        # UUID格式
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        response = PhoneBindResponse(
            user_id=valid_uuid,
            phone="13800138000"
        )
        assert response.user_id == valid_uuid

        # 字符串格式也允许
        response = PhoneBindResponse(
            user_id="simple_string_id",
            phone="13800138000"
        )
        assert response.user_id == "simple_string_id"

    def test_bind_response_serialization(self):
        """测试绑定响应序列化"""
        response = PhoneBindResponse(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            phone="13800138000",
            upgraded=True
        )

        data = response.model_dump()
        assert data["user_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert data["phone"] == "13800138000"
        assert data["upgraded"] is True

    def test_bind_response_complete_flow(self):
        """测试完整的绑定流程响应"""
        # 模拟绑定成功后的响应
        response = PhoneBindResponse(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            phone="13800138000",
            upgraded=True
        )

        # 验证所有字段
        assert response.user_id is not None
        assert response.phone is not None
        assert isinstance(response.upgraded, bool)

        # 验证字段内容
        assert len(response.user_id) > 0
        assert len(response.phone) == 11
        assert response.phone.startswith("1")  # 中国手机号以1开头


class TestSchemaIntegration:
    """Schema集成测试"""

    def test_complete_sms_flow_schemas(self):
        """测试完整SMS流程的Schema"""
        # 1. 发送请求Schema
        send_request = SMSSendRequest(
            phone="13800138000",
            scene="register"
        )

        # 2. 发送响应Schema
        send_response = SMSSendResponse(
            expires_in=300,
            retry_after=60
        )

        # 3. 验证请求Schema
        verify_request = SMSVerifyRequest(
            phone="13800138000",
            code="123456",
            scene="register"
        )

        # 4. 验证响应Schema（新用户）
        verify_response = SMSVerifyResponse(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            user_id="new_user_id",
            is_new_user=True
        )

        # 验证所有Schema都正确创建
        assert send_request.scene == "register"
        assert send_response.expires_in == 300
        assert verify_request.code == "123456"
        assert verify_response.is_new_user is True

    def test_bind_flow_schemas(self):
        """测试绑定流程的Schema"""
        # 1. 发送请求Schema（绑定场景）
        bind_send_request = SMSSendRequest(
            phone="13800138000",
            scene="bind"
        )

        # 2. 验证请求Schema（绑定场景）
        bind_verify_request = SMSVerifyRequest(
            phone="13800138000",
            code="123456",
            scene="bind"
        )

        # 3. 绑定响应Schema
        bind_response = PhoneBindResponse(
            user_id="existing_user_id",
            phone="13800138000",
            upgraded=True
        )

        # 验证绑定流程的Schema
        assert bind_send_request.scene == "bind"
        assert bind_verify_request.scene == "bind"
        assert bind_response.upgraded is True
        assert bind_response.phone == "13800138000"

    def test_schema_error_handling(self):
        """测试Schema错误处理"""
        # 测试请求Schema错误
        with pytest.raises(ValidationError) as exc_info:
            SMSSendRequest(
                phone="invalid_phone",
                scene="invalid_scene"
            )

        # 验证错误信息
        errors = exc_info.value.errors()
        assert len(errors) >= 2  # phone和scene都有错误

        # 测试响应Schema错误
        with pytest.raises(ValidationError) as exc_info:
            SMSVerifyResponse(
                access_token="",
                refresh_token="test_refresh_token",
                user_id="test_user_id"
            )

        errors = exc_info.value.errors()
        assert any("access_token" in str(error) for error in errors)