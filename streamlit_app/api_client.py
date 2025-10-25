"""
Streamlit 测试面板 API 客户端

这个文件包含：
1. APIClient 类：自动注入 JWT Token 的 HTTP 客户端
2. 请求方法：GET, POST, PUT, DELETE
3. 错误处理：自动处理 401 认证错误

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
import requests
from typing import Dict, Any, Optional


class APIClient:
    """
    自动注入 JWT Token 的 HTTP 客户端

    这个客户端会自动从 streamlit session_state 中获取 token 并注入到请求头中
    """

    def __init__(self, base_url: str):
        """
        初始化 API 客户端

        Args:
            base_url: API 基础 URL，如 "http://localhost:8001"
        """
        self.base_url = base_url.rstrip('/')

    def _inject_auth_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        自动注入认证头

        Args:
            headers: 原始请求头

        Returns:
            包含认证头的请求头
        """
        if headers is None:
            headers = {}

        # 从 session_state 中获取 token
        if "token" in st.session_state and st.session_state.token:
            headers["Authorization"] = f"Bearer {st.session_state.token}"

        # 设置默认内容类型
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        return headers

    def request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        发送 HTTP 请求

        Args:
            method: HTTP 方法，如 "GET", "POST", "PUT", "DELETE"
            endpoint: API 端点，如 "/api/v1/tasks"
            **kwargs: requests.request 的其他参数

        Returns:
            API 响应数据，如果请求失败返回 None
        """
        try:
            # 注入认证头
            headers = self._inject_auth_headers(kwargs.get("headers"))
            kwargs["headers"] = headers

            # 发送请求
            response = requests.request(
                method,
                f"{self.base_url}{endpoint}",
                **kwargs
            )

            # 处理 401 认证错误
            if response.status_code == 401:
                st.error("❌ Token 已失效，请重新认证")
                return None

            # 检查响应状态
            if not response.ok:
                error_msg = f"❌ 请求失败: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('message', '未知错误')}"
                except:
                    error_msg += f" - {response.text}"
                st.error(error_msg)
                return None

            # 解析 JSON 响应
            try:
                return response.json()
            except ValueError:
                return {"data": response.text}

        except requests.exceptions.ConnectionError:
            st.error("❌ 无法连接到 API 服务器，请检查服务器是否运行")
            return None
        except requests.exceptions.Timeout:
            st.error("❌ 请求超时，请稍后重试")
            return None
        except Exception as e:
            st.error(f"❌ 请求发生错误: {str(e)}")
            return None

    def get(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        发送 GET 请求

        Args:
            endpoint: API 端点
            **kwargs: 其他请求参数

        Returns:
            API 响应数据
        """
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        发送 POST 请求

        Args:
            endpoint: API 端点
            **kwargs: 其他请求参数

        Returns:
            API 响应数据
        """
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        发送 PUT 请求

        Args:
            endpoint: API 端点
            **kwargs: 其他请求参数

        Returns:
            API 响应数据
        """
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        发送 DELETE 请求

        Args:
            endpoint: API 端点
            **kwargs: 其他请求参数

        Returns:
            API 响应数据
        """
        return self.request("DELETE", endpoint, **kwargs)