"""
Mock短信服务测试

测试MockSMSService的各种功能，包括验证码生成、发送、验证、频率限制等。
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.services.external.mock_sms_service import MockSMSService, SMSConfig
from src.services.exceptions import (
    RateLimitException,
    ValidationException,
    BusinessException
)


def test_sms_service_initialization():
    """测试短信服务初始化"""
    try:
        # 使用默认配置初始化
        service = MockSMSService()
        assert service.config.code_length == 6
        assert service.config.code_expiry_minutes == 5
        assert service.config.max_attempts_per_hour == 10
        assert service.config.max_attempts_per_day == 50
        assert service.config.cooldown_seconds == 60
        assert service.config.mock_success_rate == 0.95

        # 使用自定义配置初始化
        custom_config = SMSConfig(
            code_length=4,
            code_expiry_minutes=10,
            max_attempts_per_hour=5,
            mock_success_rate=0.8
        )
        custom_service = MockSMSService(custom_config)
        assert custom_service.config.code_length == 4
        assert custom_service.config.code_expiry_minutes == 10
        assert custom_service.config.max_attempts_per_hour == 5
        assert custom_service.config.mock_success_rate == 0.8

        print("✓ 短信服务初始化测试通过")

    except Exception as e:
        pytest.fail(f"短信服务初始化测试失败: {e}")


def test_verification_code_generation():
    """测试验证码生成"""
    try:
        service = MockSMSService()

        # 测试默认长度
        code1 = service.generate_verification_code()
        assert len(code1) == 6
        assert code1.isdigit()

        # 测试自定义长度
        code2 = service.generate_verification_code(4)
        assert len(code2) == 4
        assert code2.isdigit()

        # 测试生成的验证码不重复（连续生成100次）
        codes = [service.generate_verification_code() for _ in range(100)]
        unique_codes = set(codes)
        # 理论上可能重复，但概率很小
        assert len(unique_codes) > 90  # 至少90%不重复

        print("✓ 验证码生成测试通过")

    except Exception as e:
        pytest.fail(f"验证码生成测试失败: {e}")


def test_phone_number_validation():
    """测试手机号码验证"""
    try:
        service = MockSMSService()

        # 测试有效手机号
        valid_phones = [
            "13812345678",
            "15987654321",
            "18611112222",
            "19123456789"
        ]

        for phone in valid_phones:
            assert service._validate_phone_number(phone) == True

        # 测试无效手机号
        invalid_phones = [
            "12345678",      # 位数不够
            "123456789012", # 位数过多
            "12812345678",  # 不以1开头
            "1381234567x",  # 包含非数字字符
            "",             # 空字符串
            "abcdefghijk"   # 全字母
        ]

        for phone in invalid_phones:
            assert service._validate_phone_number(phone) == False

        print("✓ 手机号码验证测试通过")

    except Exception as e:
        pytest.fail(f"手机号码验证测试失败: {e}")


def test_phone_number_masking():
    """测试手机号码脱敏"""
    try:
        service = MockSMSService()

        # 测试正常手机号脱敏
        masked = service._mask_phone_number("13812345678")
        assert masked == "138****5678"

        # 测试短号码（非11位）
        short_masked = service._mask_phone_number("123456")
        assert short_masked == "123456"

        print("✓ 手机号码脱敏测试通过")

    except Exception as e:
        pytest.fail(f"手机号码脱敏测试失败: {e}")


def test_sms_send_success():
    """测试短信发送成功"""
    try:
        service = MockSMSService()

        # 模拟发送验证码
        result = service.send_verification_code(
            phone="13812345678",
            verification_type="login",
            ip_address="127.0.0.1"
        )

        # 验证返回结果
        assert result["success"] == True
        assert result["message"] == "验证码发送成功"
        assert "phone_masked" in result
        assert result["phone_masked"] == "138****5678"
        assert "expiry_minutes" in result
        assert "request_id" in result
        assert result["expiry_minutes"] == 5

        # 验证记录被保存
        assert len(service._records) == 1
        record = service._records[0]
        assert record.phone == "13812345678"
        assert record.type == "login"
        assert record.ip_address == "127.0.0.1"
        assert not record.verified

        # 验证统计更新
        assert service._stats["total_sent"] == 1

        print("✓ 短信发送成功测试通过")

    except Exception as e:
        pytest.fail(f"短信发送成功测试失败: {e}")


def test_sms_send_invalid_phone():
    """测试无效手机号发送"""
    try:
        service = MockSMSService()

        # 测试无效手机号
        with pytest.raises(ValidationException) as exc_info:
            service.send_verification_code(
                phone="12345678",  # 无效手机号
                verification_type="login"
            )

        assert exc_info.value.error_code == "INVALID_PHONE_FORMAT"
        assert "手机号码格式不正确" in str(exc_info.value)

        print("✓ 无效手机号发送测试通过")

    except Exception as e:
        pytest.fail(f"无效手机号发送测试失败: {e}")


def test_cooldown_limit():
    """测试冷却时间限制"""
    try:
        service = MockSMSSService()

        # 第一次发送应该成功
        service.send_verification_code(
            phone="13812345678",
            verification_type="login"
        )

        # 立即再次发送应该触发冷却时间
        with pytest.raises(RateLimitException) as exc_info:
            service.send_verification_code(
                phone="13812345678",
                verification_type="login"
            )

        assert exc_info.value.error_code == "COOLDOWN_ACTIVE"
        assert "发送间隔过短" in str(exc_info.value)
        assert exc_info.value.details["cooldown_seconds"] <= 60

        print("✓ 冷却时间限制测试通过")

    except Exception as e:
        pytest.fail(f"冷却时间限制测试失败: {e}")


def test_hourly_rate_limit():
    """测试每小时频率限制"""
    try:
        # 使用较低的频率限制进行测试
        config = SMSConfig(max_attempts_per_hour=2)
        service = MockSMSService(config)

        # 发送第一条短信
        service.send_verification_code("13812345678", "login")
        # 发送第二条短信
        service.send_verification_code("13812345678", "login")

        # 第三条短信应该触发频率限制
        with pytest.raises(RateLimitException) as exc_info:
            service.send_verification_code("13812345678", "login")

        assert exc_info.value.error_code == "RATE_LIMIT_EXCEEDED"
        assert "发送过于频繁" in str(exc_info.value)

        print("✓ 每小时频率限制测试通过")

    except Exception as e:
        pytest.fail(f"每小时频率限制测试失败: {e}")


def test_verification_code_verify_success():
    """测试验证码验证成功"""
    try:
        service = MockSMSService()

        # 先发送验证码
        send_result = service.send_verification_code(
            phone="13812345678",
            verification_type="login"
        )

        # 获取发送的验证码
        record = service._records[-1]
        correct_code = record.code

        # 验证验证码
        verify_result = service.verify_code(
            phone="13812345678",
            code=correct_code,
            verification_type="login"
        )

        # 验证返回结果
        assert verify_result["success"] == True
        assert verify_result["message"] == "验证码验证成功"
        assert "verified_at" in verify_result

        # 验证记录被标记为已验证
        assert record.verified == True

        # 验证统计更新
        assert service._stats["total_verified"] == 1

        print("✓ 验证码验证成功测试通过")

    except Exception as e:
        pytest.fail(f"验证码验证成功测试失败: {e}")


def test_verification_code_verify_invalid():
    """测试验证码验证失败"""
    try:
        service = MockSMSService()

        # 先发送验证码
        service.send_verification_code(
            phone="13812345678",
            verification_type="login"
        )

        # 使用错误的验证码
        with pytest.raises(ValidationException) as exc_info:
            service.verify_code(
                phone="13812345678",
                code="000000",
                verification_type="login"
            )

        assert exc_info.value.error_code == "INVALID_CODE"
        assert "验证码错误或已过期" in str(exc_info.value)

        print("✓ 验证码验证失败测试通过")

    except Exception as e:
        pytest.fail(f"验证码验证失败测试失败: {e}")


def test_verification_code_expired():
    """测试验证码过期"""
    try:
        # 使用较短的过期时间进行测试
        config = SMSConfig(code_expiry_minutes=0.01)  # 0.6秒过期
        service = MockSMSService(config)

        # 发送验证码
        service.send_verification_code(
            phone="13812345678",
            verification_type="login"
        )

        # 获取发送的验证码
        record = service._records[-1]
        correct_code = record.code

        # 等待验证码过期
        time.sleep(1)

        # 尝试验证过期的验证码
        with pytest.raises(ValidationException) as exc_info:
            service.verify_code(
                phone="13812345678",
                code=correct_code,
                verification_type="login"
            )

        assert exc_info.value.error_code == "CODE_EXPIRED"
        assert "验证码已过期" in str(exc_info.value)

        print("✓ 验证码过期测试通过")

    except Exception as e:
        pytest.fail(f"验证码过期测试失败: {e}")


def test_sms_send_history():
    """测试发送历史查询"""
    try:
        service = MockSMSService()

        # 发送多条短信
        phones = ["13812345678", "15987654321", "18611112222"]
        for phone in phones:
            service.send_verification_code(phone, "login")

        # 查询第一个手机号的历史
        history = service.get_send_history(phones[0])

        # 验证历史记录
        assert len(history) == 1
        assert history[0]["phone"] == "138****5678"
        assert history[0]["type"] == "login"
        assert history[0]["verified"] == False

        # 标记验证码为已验证
        record = [r for r in service._records if r.phone == phones[0]][0]
        record.verified = True

        # 再次查询历史
        updated_history = service.get_send_history(phones[0])
        assert updated_history[0]["verified"] == True

        print("✓ 发送历史查询测试通过")

    except Exception as e:
        pytest.fail(f"发送历史查询测试失败: {e}")


def test_service_statistics():
    """测试服务统计"""
    try:
        service = MockSMSService()

        # 初始统计
        stats = service.get_statistics()
        assert stats["total_sent"] == 0
        assert stats["total_verified"] == 0
        assert stats["total_failed"] == 0
        assert stats["success_rate"] == 0.0

        # 发送几条短信
        for i in range(3):
            service.send_verification_code(f"1381234567{i}", "login")

        # 验证几条
        service.verify_code("13812345670", service._records[0].code, "login")
        service.verify_code("13812345671", service._records[1].code, "login")

        # 更新统计
        updated_stats = service.get_statistics()
        assert updated_stats["total_sent"] == 3
        assert updated_stats["total_verified"] == 2
        assert updated_stats["success_rate"] == (2 / 3) * 100
        assert updated_stats["today_sent"] == 3
        assert updated_stats["today_verified"] == 2

        print("✓ 服务统计测试通过")

    except Exception as e:
        pytest.fail(f"服务统计测试失败: {e}")


def test_mock_sms_success_rate():
    """测试模拟短信成功率"""
    try:
        # 设置50%成功率
        config = SMSConfig(mock_success_rate=0.5)
        service = MockSMSSService(config)

        # 发送多条短信
        success_count = 0
        fail_count = 0
        for _ in range(10):
            try:
                service.send_verification_code("13812345678", "login")
                success_count += 1
            except BusinessException:
                fail_count += 1

        # 验证成功率大约为50%（允许一定偏差）
        total = success_count + fail_count
        actual_success_rate = success_count / total * 100

        # 允许20%的偏差（50% ± 20%）
        assert 30 <= actual_success_rate <= 70

        print(f"✓ 模拟短信成功率测试通过 (实际成功率: {actual_success_rate:.1f}%)")

    except Exception as e:
        pytest.fail(f"模拟短信成功率测试失败: {e}")


def test_cleanup_expired_records():
    """测试清理过期记录"""
    try:
        service = MockSMSSService()

        # 添加一些记录
        old_count = len(service._records)

        # 添加过期记录（7天前）
        past_date = datetime.now(timezone.utc) - timedelta(days=8)
        old_record = service._records[0]._replace(sent_at=past_date)
        service._records.append(old_record)

        # 清理过期记录
        cleaned_count = service.cleanup_expired_records()

        # 验证清理结果
        assert cleaned_count == 1
        assert len(service._records) == old_count

        print("✓ 清理过期记录测试通过")

    except Exception as e:
        pytest.fail(f"清理过期记录测试失败: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])