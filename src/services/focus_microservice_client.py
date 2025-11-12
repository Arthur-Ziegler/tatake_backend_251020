"""
Focus微服务客户端

功能：与Focus-Service(20255)通信
接口：专注会话管理
"""
import httpx
from typing import Dict, Any
from src.api.config import config


class FocusMicroserviceClient:
    """Focus微服务客户端"""

    def __init__(self):
        self.base_url = config.focus_service_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=config.focus_service_timeout,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20
            )
        )

    async def create_session(self, user_id: str, task_id: str, session_type: str = "focus") -> Dict[str, Any]:
        """创建专注会话

        Raises:
            HTTPException: 当Focus微服务返回错误时
        """
        response = await self.client.post(
            "/focus/sessions",
            params={"user_id": user_id},
            json={"task_id": task_id, "session_type": session_type}
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json()

    async def get_sessions(self, user_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """查询专注会话列表

        Raises:
            HTTPException: 当Focus微服务返回错误时
        """
        response = await self.client.get(
            "/focus/sessions",
            params={"user_id": user_id, "page": page, "page_size": page_size}
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json()

    async def pause_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """暂停专注会话

        Raises:
            HTTPException: 当Focus微服务返回错误时
        """
        response = await self.client.post(
            f"/focus/sessions/{session_id}/pause",
            params={"user_id": user_id}
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json()

    async def resume_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """恢复专注会话

        Raises:
            HTTPException: 当Focus微服务返回错误时
        """
        response = await self.client.post(
            f"/focus/sessions/{session_id}/resume",
            params={"user_id": user_id}
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json()

    async def complete_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """完成专注会话

        Raises:
            HTTPException: 当Focus微服务返回错误时
        """
        response = await self.client.post(
            f"/focus/sessions/{session_id}/complete",
            params={"user_id": user_id}
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
        """关闭连接"""
        await self.client.aclose()


# 全局单例
_focus_client = None


def get_focus_client() -> FocusMicroserviceClient:
    """获取Focus客户端单例"""
    global _focus_client
    if _focus_client is None:
        _focus_client = FocusMicroserviceClient()
    return _focus_client
