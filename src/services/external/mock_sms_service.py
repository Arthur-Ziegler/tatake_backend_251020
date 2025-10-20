"""
Mock短信服务

模拟真实的短信发送服务，用于开发和测试环境。
包含验证码生成、发送频率限制、冷却时间等功能。
"""

import random
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..exceptions import (
    BusinessException,
    RateLimitException,
    ValidationException
)


@dataclass
class SMSRecord:
    """短信发送记录"""
    phone: str
    code: str
    type: str
    sent_at: datetime
    attempts: int = 1
    verified: bool = False
    ip_address: Optional[str] = None


@dataclass
class SMSConfig:
    """短信服务配置"""
    code_length: int = 6
    code_expiry_minutes: int = 5
    max_attempts_per_hour: int = 10
    max_attempts_per_day: int = 50
    cooldown_seconds: int = 60
    mock_success_rate: float = 1.0  # 模拟100%成功率（测试用）


class MockSMSService:
    """
    Mock短信服务类

    模拟真实的短信发送功能，用于开发和测试环境。
    包含完整的验证码生成、发送、验证逻辑，以及频率限制和安全检查。
    """

    def __init__(self, config: Optional[SMSConfig] = None):
        """
        初始化Mock短信服务

        Args:
            config: 短信服务配置，如果为None则使用默认配置
        """
        self.config = config or SMSConfig()

        # 存储短信记录（内存模拟）
        self._records: List[SMSRecord] = []
        self._ip_limits: Dict[str, List[datetime]] = {}

        # 统计信息
        self._stats = {
            'total_sent': 0,
            'total_verified': 0,
            'total_failed': 0,
            'last_reset': datetime.now(timezone.utc)
        }

    def generate_verification_code(self, length: int = None) -> str:
        """
        生成验证码

        Args:
            length: 验证码长度，默认使用配置中的长度

        Returns:
            生成的验证码字符串
        """
        code_length = length or self.config.code_length

        # 生成纯数字验证码
        code = ''.join(random.choices('0123456789', k=code_length))

        return code

    def _check_rate_limit(self, phone: str, ip_address: Optional[str] = None) -> None:
        """
        检查发送频率限制

        Args:
            phone: 手机号码
            ip_address: IP地址

        Raises:
            RateLimitException: 超出频率限制时抛出
        """
        now = datetime.now(timezone.utc)

        # 检查最近发送的短信记录
        recent_records = [
            record for record in self._records
            if record.phone == phone and record.sent_at > now - timedelta(hours=1)
        ]

        # 检查每小时限制
        if len(recent_records) >= self.config.max_attempts_per_hour:
            last_sent = max(record.sent_at for record in recent_records)
            cooldown_remaining = 3600 - int((now - last_sent).total_seconds())
            raise RateLimitException(
                f"发送过于频繁，请{cooldown_remaining // 60}分钟{cooldown_remaining % 60}秒后再试",
                error_code="RATE_LIMIT_EXCEEDED",
                cooldown_seconds=cooldown_remaining
            )

        # 检查每日限制
        daily_records = [
            record for record in self._records
            if record.phone == phone and record.sent_at > now - timedelta(days=1)
        ]

        if len(daily_records) >= self.config.max_attempts_per_day:
            raise RateLimitException(
                "今日发送次数已达上限，请明天再试",
                error_code="DAILY_LIMIT_EXCEEDED"
            )

        # 检查IP限制（如果提供IP地址）
        if ip_address:
            if ip_address not in self._ip_limits:
                self._ip_limits[ip_address] = []

            # 清理过期的IP记录
            self._ip_limits[ip_address] = [
                timestamp for timestamp in self._ip_limits[ip_address]
                if timestamp > now - timedelta(hours=1)
            ]

            # 检查IP频率限制
            if len(self._ip_limits[ip_address]) >= self.config.max_attempts_per_hour:
                raise RateLimitException(
                    "该IP地址发送过于频繁，请稍后再试",
                    error_code="IP_RATE_LIMIT_EXCEEDED"
                )

    def _check_cooldown(self, phone: str) -> None:
        """
        检查冷却时间

        Args:
            phone: 手机号码

        Raises:
            RateLimitException: 在冷却时间内抛出
        """
        now = datetime.now(timezone.utc)

        # 查找最近的发送记录
        recent_records = [
            record for record in self._records
            if record.phone == phone
        ]

        if recent_records:
            last_sent = max(record.sent_at for record in recent_records)
            time_since_last = (now - last_sent).total_seconds()

            if time_since_last < self.config.cooldown_seconds:
                cooldown_remaining = int(self.config.cooldown_seconds - time_since_last)
                raise RateLimitException(
                    f"发送间隔过短，请{cooldown_remaining}秒后再试",
                    error_code="COOLDOWN_ACTIVE",
                    cooldown_seconds=cooldown_remaining
                )

    def send_verification_code(
        self,
        phone: str,
        verification_type: str = "login",
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        发送验证码

        Args:
            phone: 手机号码
            verification_type: 验证码类型（login、register、reset_password等）
            ip_address: 客户端IP地址

        Returns:
            包含发送结果的字典

        Raises:
            ValidationException: 手机号码格式错误时抛出
            RateLimitException: 超出频率限制时抛出
            BusinessException: 其他业务错误时抛出
        """
        try:
            # 验证手机号码格式
            if not self._validate_phone_number(phone):
                raise ValidationException(
                    "手机号码格式不正确",
                    error_code="INVALID_PHONE_FORMAT"
                )

            # 检查频率限制
            self._check_rate_limit(phone, ip_address)

            # 检查冷却时间
            self._check_cooldown(phone)

            # 生成验证码
            code = self.generate_verification_code()

            # 模拟发送短信
            send_result = self._mock_send_sms(phone, code, verification_type)

            if not send_result['success']:
                self._stats['total_failed'] += 1
                raise BusinessException(
                    "SMS_SEND_FAILED",
                    "短信发送失败，请稍后重试"
                )

            # 记录发送信息
            record = SMSRecord(
                phone=phone,
                code=code,
                type=verification_type,
                sent_at=datetime.now(timezone.utc),
                ip_address=ip_address
            )
            self._records.append(record)

            # 记录IP发送时间
            if ip_address:
                if ip_address not in self._ip_limits:
                    self._ip_limits[ip_address] = []
                self._ip_limits[ip_address].append(record.sent_at)

            # 更新统计
            self._stats['total_sent'] += 1

            return {
                "success": True,
                "message": "验证码发送成功",
                "phone_masked": self._mask_phone_number(phone),
                "expiry_minutes": self.config.code_expiry_minutes,
                "request_id": f"sms_{int(time.time())}_{random.randint(1000, 9999)}"
            }

        except (ValidationException, RateLimitException, BusinessException):
            raise
        except Exception as e:
            self._stats['total_failed'] += 1
            raise BusinessException(
                "SMS_SERVICE_ERROR",
                f"短信发送异常: {str(e)}"
            )

    def verify_code(
        self,
        phone: str,
        code: str,
        verification_type: str = "login"
    ) -> Dict[str, Any]:
        """
        验证验证码

        Args:
            phone: 手机号码
            code: 验证码
            verification_type: 验证码类型

        Returns:
            包含验证结果的字典

        Raises:
            ValidationException: 验证码错误或过期时抛出
        """
        now = datetime.now(timezone.utc)

        # 查找匹配的记录
        matching_records = [
            record for record in self._records
            if (record.phone == phone and
                record.code == code and
                record.type == verification_type and
                not record.verified)
        ]

        if not matching_records:
            self._stats['total_failed'] += 1
            raise ValidationException(
                "验证码错误或已过期",
                error_code="INVALID_CODE"
            )

        # 获取最新的记录
        latest_record = max(matching_records, key=lambda r: r.sent_at)

        # 检查验证码是否过期
        expiry_time = latest_record.sent_at + timedelta(minutes=self.config.code_expiry_minutes)
        if now > expiry_time:
            self._stats['total_failed'] += 1
            raise ValidationException(
                "验证码已过期",
                error_code="CODE_EXPIRED"
            )

        # 标记为已验证
        for record in matching_records:
            record.verified = True

        # 更新统计
        self._stats['total_verified'] += 1

        return {
            "success": True,
            "message": "验证码验证成功",
            "verified_at": now.isoformat()
        }

    def get_send_history(
        self,
        phone: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        获取发送历史

        Args:
            phone: 手机号码
            days: 查询天数

        Returns:
            发送历史记录列表
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        records = [
            {
                "phone": self._mask_phone_number(record.phone),
                "type": record.type,
                "sent_at": record.sent_at.isoformat(),
                "verified": record.verified,
                "attempts": record.attempts
            }
            for record in self._records
            if record.phone == phone and record.sent_at > cutoff_date
        ]

        return sorted(records, key=lambda x: x["sent_at"], reverse=True)

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取服务统计信息

        Returns:
            统计信息字典
        """
        now = datetime.now(timezone.utc)

        # 计算今日统计
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_records = [
            record for record in self._records
            if record.sent_at >= today_start
        ]

        today_sent = len(today_records)
        today_verified = len([r for r in today_records if r.verified])

        return {
            "total_sent": self._stats['total_sent'],
            "total_verified": self._stats['total_verified'],
            "total_failed": self._stats['total_failed'],
            "today_sent": today_sent,
            "today_verified": today_verified,
            "success_rate": (
                self._stats['total_verified'] / max(self._stats['total_sent'], 1)
            ) * 100,
            "last_reset": self._stats['last_reset'].isoformat()
        }

    def _validate_phone_number(self, phone: str) -> bool:
        """
        验证手机号码格式

        Args:
            phone: 手机号码

        Returns:
            是否有效
        """
        # 简单的中国手机号验证
        import re
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))

    def _mask_phone_number(self, phone: str) -> str:
        """
        脱敏手机号码

        Args:
            phone: 手机号码

        Returns:
            脱敏后的手机号码
        """
        if len(phone) != 11:
            return phone

        return f"{phone[:3]}****{phone[-4:]}"

    def _mock_send_sms(
        self,
        phone: str,
        code: str,
        sms_type: str
    ) -> Dict[str, Any]:
        """
        模拟发送短信

        Args:
            phone: 手机号码
            code: 验证码
            sms_type: 短信类型

        Returns:
            发送结果字典
        """
        # 模拟95%的成功率
        if random.random() > self.config.mock_success_rate:
            return {
                "success": False,
                "error": "网络连接失败",
                "error_code": "NETWORK_ERROR"
            }

        # 模拟短信内容
        templates = {
            "login": f"【塔可】登录验证码：{code}，5分钟内有效，请勿泄露给他人。",
            "register": f"【塔可】注册验证码：{code}，5分钟内有效，请勿泄露给他人。",
            "reset_password": f"【塔可】密码重置验证码：{code}，5分钟内有效，请勿泄露给他人。",
            "default": f"【塔可】验证码：{code}，5分钟内有效，请勿泄露给他人。"
        }

        template = templates.get(sms_type, templates["default"])

        # 模拟发送延迟
        time.sleep(random.uniform(0.1, 0.3))

        return {
            "success": True,
            "message_id": f"msg_{int(time.time())}_{random.randint(10000, 99999)}",
            "content": template,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }

    def cleanup_expired_records(self) -> int:
        """
        清理过期记录

        Returns:
            清理的记录数量
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

        initial_count = len(self._records)
        self._records = [
            record for record in self._records
            if record.sent_at > cutoff_date
        ]

        # 清理IP限制记录
        for ip in list(self._ip_limits.keys()):
            self._ip_limits[ip] = [
                timestamp for timestamp in self._ip_limits[ip]
                if timestamp > cutoff_date
            ]
            if not self._ip_limits[ip]:
                del self._ip_limits[ip]

        return initial_count - len(self._records)