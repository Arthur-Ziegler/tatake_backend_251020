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
        """微信登录

        Raises:
            HTTPException: 当Auth微服务返回错误时
        """
        response = await self.client.post(
            "/auth/wechat/login",
            json={"project": config.project, "wechat_openid": wechat_openid}
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json()

    async def wechat_register(self, wechat_openid: str) -> Dict[str, Any]:
        """微信注册

        Raises:
            HTTPException: 当Auth微服务返回错误时
        """
        response = await self.client.post(
            "/auth/wechat/register",
            json={"project": config.project, "wechat_openid": wechat_openid}
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json()

    async def phone_send_code(self, phone: str, scene: str = "login") -> Dict[str, Any]:
        """发送手机验证码

        Args:
            phone: 手机号
            scene: 场景，register/login/bind，默认login

        Raises:
            HTTPException: 当Auth微服务返回错误时
        """
        response = await self.client.post(
            "/auth/phone/send-code",
            json={"project": config.project, "phone": phone, "scene": scene}
        )

        # 检查HTTP状态码，非2xx时抛出HTTPException
        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json()

    async def phone_verify(self, phone: str, code: str, scene: str = "login") -> Dict[str, Any]:
        """验证手机验证码

        Args:
            phone: 手机号
            code: 验证码
            scene: 场景，register/login/bind，默认login

        Raises:
            HTTPException: 当Auth微服务返回错误时
        """
        response = await self.client.post(
            "/auth/phone/verify",
            json={"project": config.project, "phone": phone, "code": code, "scene": scene}
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """刷新token

        Raises:
            HTTPException: 当Auth微服务返回错误时
        """
        response = await self.client.post(
            "/auth/token/refresh",
            json={"project": config.project, "refresh_token": refresh_token}
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
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
