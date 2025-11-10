"""
Auth微服务客户端

功能：与Auth-Service(20251)通信
接口：4个认证接口
"""
import httpx
from typing import Dict, Any
from src.config.microservices import get_microservice_config

config = get_microservice_config()


class AuthMicroserviceClient:
    """Auth微服务客户端"""

    def __init__(self):
        self.base_url = config.auth_service_url
        self.timeout = config.request_timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )

    async def wechat_login(self, wechat_openid: str) -> Dict[str, Any]:
        """微信登录"""
        response = await self.client.post(
            "/auth/wechat/login",
            json={"project": config.project, "wechat_openid": wechat_openid}
        )
        return response.json()

    async def wechat_register(self, wechat_openid: str) -> Dict[str, Any]:
        """微信注册"""
        response = await self.client.post(
            "/auth/wechat/register",
            json={"project": config.project, "wechat_openid": wechat_openid}
        )
        return response.json()

    async def phone_send_code(self, phone: str, scene: str = "login") -> Dict[str, Any]:
        """发送手机验证码

        Args:
            phone: 手机号
            scene: 场景，register/login/bind，默认login
        """
        response = await self.client.post(
            "/auth/phone/send-code",
            json={"project": config.project, "phone": phone, "scene": scene}
        )
        return response.json()

    async def phone_verify(self, phone: str, code: str, scene: str = "login") -> Dict[str, Any]:
        """验证手机验证码

        Args:
            phone: 手机号
            code: 验证码
            scene: 场景，register/login/bind，默认login
        """
        response = await self.client.post(
            "/auth/phone/verify",
            json={"project": config.project, "phone": phone, "code": code, "scene": scene}
        )
        return response.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """刷新token"""
        response = await self.client.post(
            "/auth/token/refresh",
            json={"project": config.project, "refresh_token": refresh_token}
        )
        return response.json()

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 全局单例
_auth_client = None


def get_auth_client() -> AuthMicroserviceClient:
    """获取Auth客户端单例"""
    global _auth_client
    if _auth_client is None:
        _auth_client = AuthMicroserviceClient()
    return _auth_client
