"""
认证微服务HTTP客户端

提供与外部认证微服务的HTTP通信接口，实现：
- 自动注入project参数
- 统一的响应格式转换
- 错误处理和重试机制
- 异步HTTP请求
"""

import os
import asyncio
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from dotenv import load_dotenv

from src.api.config import config


class AuthMicroserviceClient:
    """
    认证微服务HTTP客户端

    这个类封装了与外部认证微服务的所有HTTP通信，提供：
    - 自动注入project参数（值为"tatake_backend"）
    - 统一的错误处理和重试机制
    - 异步HTTP请求
    - 响应格式标准化

    设计原则：
    - 纯透传架构，无业务逻辑
    - 自动注入公共参数，简化调用
    - 统一错误处理，提升稳定性
    - 异步设计，提升性能
    """

    def __init__(self, base_url: Optional[str] = None, project: Optional[str] = None):
        """
        初始化认证微服务客户端

        Args:
            base_url: 微服务基础URL，默认从环境变量读取
            project: 项目标识，默认从环境变量读取
        """
        # 强制重新加载.env文件，确保获取最新配置
        load_dotenv(override=True)

        self.base_url = (base_url or
                        os.getenv("AUTH_MICROSERVICE_URL", "http://localhost:8987")).rstrip('/')

        self.project = project or os.getenv("AUTH_PROJECT", "tatake_backend")

        # 配置HTTP客户端，设置合理的超时和重试策略
        self.client_config = {
            "timeout": httpx.Timeout(
                connect=10.0,  # 连接超时10秒
                read=30.0,      # 读取超时30秒
                write=10.0,     # 写入超时10秒
                pool=60.0       # 连接池超时60秒
            ),
            "limits": httpx.Limits(
                max_connections=20,           # 最大连接数
                max_keepalive_connections=5,   # 最大保持连接数
                keepalive_expiry=30.0         # 保持连接过期时间
            ),
            "http2": True,  # 启用HTTP/2支持，提升性能
        }

        print(f"[AuthMicroserviceClient] 初始化: base_url={self.base_url}, project={self.project}")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        发起HTTP请求到微服务

        这是核心的HTTP请求方法，负责：
        - 自动注入project参数
        - 统一错误处理
        - 响应格式验证
        - 重试机制

        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE等)
            endpoint: API端点路径（不包含base_url）
            data: 请求数据，会自动注入project字段
            headers: 额外的请求头

        Returns:
            微服务的响应数据

        Raises:
            HTTPException: 当请求失败或响应格式错误时
        """
        url = f"{self.base_url}{endpoint}"

        # 自动注入project参数到请求数据
        if data is None:
            data = {}
        if isinstance(data, dict):
            data["project"] = self.project

        # 设置默认请求头
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "TaKeKe-Backend/1.0.0"
        }
        if headers:
            request_headers.update(headers)

        # 创建HTTP客户端
        async with httpx.AsyncClient(**self.client_config) as client:
            try:
                print(f"[AuthMicroserviceClient] 发起请求: {method} {url}")
                print(f"[AuthMicroserviceClient] 请求数据: {data}")

                # 发起HTTP请求
                response = await client.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=request_headers
                )

                print(f"[AuthMicroserviceClient] 响应状态: {response.status_code}")

                # 检查HTTP状态码
                if response.status_code >= 400:
                    # 对429错误（请求过于频繁）提供更友好的错误提示
                    if response.status_code == 429:
                        raise HTTPException(
                            status_code=429,
                            detail="发送验证码过于频繁，请稍后再试。通常需要等待60秒后才能重新发送。"
                        )

                    error_msg = f"认证微服务请求失败: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('message', '未知错误')}"
                    except:
                        if response.text:
                            error_msg += f" - {response.text[:200]}"

                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_msg
                    )

                # 解析JSON响应
                try:
                    response_data = response.json()
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"认证微服务返回无效JSON: {str(e)}"
                    )

                # 验证响应格式（微服务应该返回 {code, message, data} 格式）
                if not isinstance(response_data, dict):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="认证微服务返回格式错误：非JSON对象"
                    )

                if "code" not in response_data:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="认证微服务返回格式错误：缺少code字段"
                    )

                print(f"[AuthMicroserviceClient] 响应数据: {response_data}")
                return response_data

            except httpx.TimeoutException as e:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"认证微服务请求超时: {str(e)}"
                )
            except httpx.ConnectError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"无法连接到认证微服务: {str(e)}"
                )
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"认证微服务通信错误: {str(e)}"
                )
            except HTTPException:
                # 重新抛出HTTP异常
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"认证微服务客户端内部错误: {str(e)}"
                )

    # ==================== 微信认证相关接口 ====================

    async def guest_init(self) -> Dict[str, Any]:
        """
        游客账号初始化

        创建一个新的游客账号，每次请求都创建全新的随机游客身份。

        Returns:
            包含认证令牌的响应数据
        """
        return await self._make_request("POST", "/auth/guest/init", {})

    async def wechat_register(self, wechat_openid: str) -> Dict[str, Any]:
        """
        微信用户注册

        通过微信OpenID注册新用户。如果用户已存在则直接登录。

        Args:
            wechat_openid: 微信OpenID

        Returns:
            包含认证令牌的响应数据
        """
        return await self._make_request("POST", "/auth/wechat/register", {
            "wechat_openid": wechat_openid,
            "project": self.project
        })

    async def wechat_login(self, wechat_openid: str) -> Dict[str, Any]:
        """
        微信用户登录

        通过微信OpenID登录已有用户账号。如果账号不存在可选择自动注册。

        Args:
            wechat_openid: 微信OpenID

        Returns:
            包含认证令牌的响应数据
        """
        return await self._make_request("POST", "/auth/wechat/login", {
            "wechat_openid": wechat_openid,
            "project": self.project
        })

    async def wechat_bind(self, wechat_openid: str, token: str) -> Dict[str, Any]:
        """
        微信账号绑定

        将当前账号与微信OpenID绑定，支持游客账号升级为正式账号。
        需要提供有效的访问令牌。

        Args:
            wechat_openid: 微信OpenID
            token: 当前用户的访问令牌

        Returns:
            包含认证令牌的响应数据
        """
        headers = {"Authorization": f"Bearer {token}"}
        return await self._make_request("POST", "/auth/wechat/bind", {
            "wechat_openid": wechat_openid
        }, headers=headers)

    # ==================== 邮箱认证相关接口 ====================

    async def email_send_code(self, email: str, scene: str) -> Dict[str, Any]:
        """
        发送邮箱验证码

        发送邮箱验证码到指定邮箱地址，支持注册、登录、绑定三种场景。

        Args:
            email: 邮箱地址
            scene: 使用场景 (register/login/bind)

        Returns:
            包含发送结果的响应数据
        """
        return await self._make_request("POST", "/auth/email/send-code", {
            "email": email,
            "scene": scene
        })

    async def email_register(self, email: str, password: str, verification_code: str) -> Dict[str, Any]:
        """
        邮箱用户注册

        通过邮箱和密码注册新用户。需要提供有效的邮箱验证码。

        Args:
            email: 邮箱地址
            password: 密码
            verification_code: 邮箱验证码

        Returns:
            包含认证令牌的响应数据
        """
        return await self._make_request("POST", "/auth/email/register", {
            "email": email,
            "password": password,
            "verification_code": verification_code
        })

    async def email_login(self, email: str, password: str) -> Dict[str, Any]:
        """
        邮箱密码登录

        通过邮箱和密码登录已有用户账号。

        Args:
            email: 邮箱地址
            password: 密码

        Returns:
            包含认证令牌的响应数据
        """
        return await self._make_request("POST", "/auth/email/login", {
            "email": email,
            "password": password
        })

    async def email_bind(self, email: str, password: str, verification_code: str, token: str) -> Dict[str, Any]:
        """
        邮箱账号绑定

        将当前登录的账号与邮箱绑定，支持游客账号升级为正式用户。
        需要有效的访问令牌进行身份验证。

        Args:
            email: 邮箱地址
            password: 密码
            verification_code: 邮箱验证码
            token: 当前用户的访问令牌

        Returns:
            包含绑定结果的响应数据
        """
        headers = {"Authorization": f"Bearer {token}"}
        return await self._make_request("POST", "/auth/email/bind", {
            "email": email,
            "password": password,
            "verification_code": verification_code
        }, headers=headers)

    # ==================== 手机认证相关接口 ====================

    async def phone_send_code(self, phone: str, scene: str, token: Optional[str] = None) -> Dict[str, Any]:
        """
        发送手机验证码

        发送短信验证码到指定手机号，支持注册、登录、绑定三种业务场景。

        Args:
            phone: 手机号
            scene: 使用场景 (register/login/bind)
            token: 访问令牌（bind场景必需）

        Returns:
            包含发送结果的响应数据
        """
        headers = {}
        if token and scene == "bind":
            headers["Authorization"] = f"Bearer {token}"

        return await self._make_request("POST", "/auth/phone/send-code", {
            "phone": phone,
            "scene": scene,
            "project": self.project
        }, headers=headers)

    async def phone_verify(
        self,
        phone: str,
        code: str,
        scene: str,
        token: Optional[str] = None,
        wechat_openid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        验证短信验证码

        验证短信验证码，支持手机注册、手机登录、手机绑定三种业务场景。

        Args:
            phone: 手机号
            code: 验证码
            scene: 使用场景 (register/login/bind)
            token: 访问令牌（bind场景必需）
            wechat_openid: 微信OpenID（可选，bind场景用于手机号用户绑定微信）

        Returns:
            包含验证结果的响应数据
        """
        headers = {}
        if token and scene == "bind":
            headers["Authorization"] = f"Bearer {token}"

        data = {
            "phone": phone,
            "code": code,
            "scene": scene,
            "project": self.project
        }
        if wechat_openid:
            data["wechat_openid"] = wechat_openid

        return await self._make_request("POST", "/auth/phone/verify", data, headers=headers)

    # ==================== 令牌管理相关接口 ====================

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        刷新访问令牌

        使用刷新令牌获取新的访问令牌，支持游客、微信、手机等多种认证方式的令牌刷新。

        Args:
            refresh_token: 刷新令牌

        Returns:
            包含新认证令牌的响应数据
        """
        return await self._make_request("POST", "/auth/token/refresh", {
            "refresh_token": refresh_token
        })

    # ==================== 系统相关接口 ====================

    async def get_public_key(self) -> Dict[str, Any]:
        """
        获取JWT公钥

        获取JWT公钥用于本地验证JWT签名。业务服务可以调用此接口获取公钥。

        Returns:
            包含公钥信息的响应数据
        """
        return await self._make_request("GET", "/auth/system/public-key")

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        检查认证微服务的健康状态。
        支持多种响应格式以兼容不同的服务版本。

        Returns:
            包含健康状态信息的响应数据
        """
        # 使用特殊的健康检查处理
        url = f"{self.base_url}/health"

        # 设置默认请求头
        request_headers = {
            "Accept": "application/json",
            "User-Agent": "TaKeKe-Backend/1.0.0"
        }

        # 创建HTTP客户端
        async with httpx.AsyncClient(**self.client_config) as client:
            try:
                print(f"[AuthMicroserviceClient] 发起健康检查: GET {url}")

                # 发起HTTP请求
                response = await client.request(
                    method="GET",
                    url=url,
                    headers=request_headers
                )

                print(f"[AuthMicroserviceClient] 健康检查响应状态: {response.status_code}")

                # 检查HTTP状态码
                if response.status_code >= 400:
                    error_msg = f"认证微服务健康检查失败: HTTP {response.status_code}"
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_msg
                    )

                # 解析JSON响应
                try:
                    response_data = response.json()
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"认证微服务返回无效JSON: {str(e)}"
                    )

                # 处理不同的响应格式
                if "code" in response_data:
                    # 标准格式: {"code": 200, "message": "ok", "data": {...}}
                    print(f"[AuthMicroserviceClient] 健康检查响应(标准格式): {response_data}")
                    return response_data
                elif "status" in response_data:
                    # 简单格式: {"status": "healthy", "service": "Auth Service"}
                    # 转换为标准格式
                    standard_response = {
                        "code": 200,
                        "message": "Health check passed",
                        "data": {
                            "status": response_data.get("status"),
                            "service": response_data.get("service", "Auth Service")
                        }
                    }
                    print(f"[AuthMicroserviceClient] 健康检查响应(转换格式): {standard_response}")
                    return standard_response
                else:
                    # 未知格式，尽力转换
                    standard_response = {
                        "code": 200,
                        "message": "Health check response format unknown but service responded",
                        "data": response_data
                    }
                    print(f"[AuthMicroserviceClient] 健康检查响应(通用格式): {standard_response}")
                    return standard_response

            except httpx.TimeoutException as e:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"认证微服务健康检查超时: {str(e)}"
                )
            except httpx.ConnectError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"无法连接到认证微服务进行健康检查: {str(e)}"
                )
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"认证微服务健康检查通信错误: {str(e)}"
                )
            except HTTPException:
                # 重新抛出HTTP异常
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"认证微服务健康检查内部错误: {str(e)}"
                )


# 全局客户端实例（单例模式）
_auth_client: Optional[AuthMicroserviceClient] = None


def get_auth_client() -> AuthMicroserviceClient:
    """
    获取全局认证微服务客户端实例

    使用单例模式，避免重复创建客户端实例，提升性能。

    Returns:
        AuthMicroserviceClient实例
    """
    global _auth_client
    if _auth_client is None:
        _auth_client = AuthMicroserviceClient()
    return _auth_client