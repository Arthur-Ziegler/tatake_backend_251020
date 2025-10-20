"""
外部服务模块

包含与外部服务集成的相关服务类，如短信服务、支付服务等。
"""

from .mock_sms_service import MockSMSService, SMSConfig

__all__ = [
    "MockSMSService",
    "SMSConfig"
]