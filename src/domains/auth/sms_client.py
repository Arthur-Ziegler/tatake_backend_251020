"""
SMS短信服务客户端

根据add-phone-sms-auth提案，提供短信发送功能的抽象接口和具体实现。
支持Mock和阿里云两种模式，通过环境变量SMS_MODE切换。

设计原则：
1. 抽象接口：定义统一的短信发送接口
2. 多实现支持：Mock用于测试，Aliyun用于生产
3. 工厂模式：通过配置选择具体实现
4. 错误处理：统一的异常处理机制
5. 异步支持：所有发送操作都是异步的

使用方法：
```python
from src.domains.auth.sms_client import get_sms_client

# 获取客户端（根据SMS_MODE环境变量）
client = get_sms_client()

# 发送验证码
result = await client.send_code("13800138000", "123456")
if result["success"]:
    print(f"发送成功，消息ID: {result['message_id']}")
```

环境变量：
- SMS_MODE: mock | aliyun（默认mock）
- ALIYUN_ACCESS_KEY_ID: 阿里云AccessKey ID
- ALIYUN_ACCESS_KEY_SECRET: 阿里云AccessKey Secret
- ALIYUN_SMS_SIGN_NAME: 短信签名
- ALIYUN_SMS_TEMPLATE_CODE: 短信模板代码
- ALIYUN_SMS_ENDPOINT: 阿里云服务端点
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any

# 延迟导入，只在需要时导入阿里云SDK


class SMSClientInterface(ABC):
    """SMS客户端接口

    定义短信发送的统一接口，所有实现必须继承此接口。
    """

    @abstractmethod
    async def send_code(self, phone: str, code: str) -> Dict[str, Any]:
        """
        发送短信验证码

        Args:
            phone: 手机号，11位数字
            code: 验证码，6位数字

        Returns:
            Dict: {
                "success": bool,  # 是否发送成功
                "message_id": str,  # 消息ID（成功时）
            }

        Raises:
            Exception: 发送失败时抛出具体异常
        """
        pass


class MockSMSClient(SMSClientInterface):
    """Mock SMS客户端

    用于测试和开发环境，不发送真实短信，只在控制台打印日志。
    总是返回成功结果，适合单元测试和功能测试。

    特性：
    - 控制台日志输出
    - 总是返回成功
    - 固定消息ID
    - 零成本，无网络依赖
    """

    async def send_code(self, phone: str, code: str) -> Dict[str, Any]:
        """
        模拟发送短信验证码

        Args:
            phone: 手机号
            code: 验证码

        Returns:
            Dict: 成功响应
        """
        # 控制台输出，便于测试调试
        print(f"📱 [MOCK SMS] {phone} -> {code}")

        return {"success": True, "message_id": "mock_123"}


class AliyunSMSClient(SMSClientInterface):
    """阿里云SMS客户端

    集成阿里云短信服务，用于生产环境发送真实短信。
    需要配置相关环境变量才能使用。

    配置要求：
    - ALIYUN_ACCESS_KEY_ID: 阿里云AccessKey ID
    - ALIYUN_ACCESS_KEY_SECRET: 阿里云AccessKey Secret
    - ALIYUN_SMS_SIGN_NAME: 已审核的短信签名
    - ALIYUN_SMS_TEMPLATE_CODE: 已审核的短信模板
    - ALIYUN_SMS_ENDPOINT: 服务端点（默认新加坡）

    特性：
    - 真实短信发送
    - 异步API调用
    - 统一错误处理
    - 完整的日志记录
    """

    def __init__(self):
        """初始化阿里云SMS客户端"""
        self._validate_config()
        self._client = self._create_client()

    def _validate_config(self) -> None:
        """验证配置是否完整"""
        required_vars = [
            "ALIYUN_ACCESS_KEY_ID",
            "ALIYUN_ACCESS_KEY_SECRET",
            "ALIYUN_SMS_SIGN_NAME",
            "ALIYUN_SMS_TEMPLATE_CODE",
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            raise Exception(
                f"阿里云SMS客户端缺少必要的环境变量: {', '.join(missing_vars)}"
            )

    def _create_client(self):
        """创建阿里云SDK客户端"""
        # 延迟导入阿里云SDK
        from alibabacloud_dysmsapi20180501.client import Client
        from alibabacloud_tea_openapi import models as openapi_models

        config = openapi_models.Config(
            access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID"),
            access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
        )

        # 设置服务端点
        endpoint = os.getenv(
            "ALIYUN_SMS_ENDPOINT", "dysmsapi.ap-southeast-1.aliyuncs.com"
        )
        config.endpoint = endpoint

        return Client(config)

    async def send_code(self, phone: str, code: str) -> Dict[str, Any]:
        """
        通过阿里云服务发送短信验证码

        Args:
            phone: 手机号，11位数字
            code: 验证码，6位数字

        Returns:
            Dict: 发送结果

        Raises:
            Exception: 网络异常、配置异常、API异常等
        """
        try:
            # 延迟导入模型
            from alibabacloud_dysmsapi20180501 import models as dysmsapi_models

            # 构建请求
            request = dysmsapi_models.SendMessageWithTemplateRequest(
                to=f"86{phone}",  # 中国区号
                from_=os.getenv("ALIYUN_SMS_SIGN_NAME"),
                template_code=os.getenv("ALIYUN_SMS_TEMPLATE_CODE"),
                template_param=json.dumps({"code": code}),
            )

            # 发送请求
            response = await self._client.send_message_with_template_async(request)

            # 处理响应
            success = response.response_code == "OK"
            result = {"success": success}

            if success and response.message_id:
                result["message_id"] = response.message_id

            return result

        except Exception as e:
            # 记录错误并重新抛出
            print(f"❌ 阿里云短信发送失败: {str(e)}")
            raise


def get_sms_client() -> SMSClientInterface:
    """
    获取SMS客户端实例

    根据SMS_MODE环境变量选择合适的客户端实现：
    - mock: MockSMSClient（默认）
    - aliyun: AliyunSMSClient

    Returns:
        SMSClientInterface: SMS客户端实例
    """
    mode = os.getenv("SMS_MODE", "mock").lower().strip()

    if mode == "aliyun":
        return AliyunSMSClient()
    else:
        # 默认使用Mock客户端，支持未知模式
        return MockSMSClient()


# 便捷函数，向后兼容
def create_sms_client() -> SMSClientInterface:
    """创建SMS客户端实例（向后兼容）"""
    return get_sms_client()
