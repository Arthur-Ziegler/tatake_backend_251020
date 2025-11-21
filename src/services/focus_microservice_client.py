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

    async def record_focus_status(
        self,
        user_id: str,
        focus_status: str,
        duration_minutes: int,
        task_id: str
    ) -> Dict[str, Any]:
        """记录专注状态（创建专注会话）

        Args:
            user_id: 用户ID
            focus_status: 专注状态（focused/break）
            duration_minutes: 持续时长（分钟）
            task_id: 关联任务ID

        Returns:
            Dict[str, Any]: 会话创建结果

        Raises:
            HTTPException: 当Focus微服务返回错误时
        """
        # 映射focus_status到Focus微服务期望的session_type
        # 兼容多种输入格式：focused->focus, break->break
        session_type_map = {
            "focused": "focus",
            "focus": "focus",
            "break": "break",
            "long_break": "long_break",
            "pause": "pause"
        }
        session_type = session_type_map.get(focus_status.lower(), "focus")

        response = await self.client.post(
            "/focus/sessions",
            params={"user_id": user_id},
            json={
                "task_id": task_id,
                "session_type": session_type,
                "duration_minutes": duration_minutes
            }
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json()

    async def get_pomodoro_count(
        self,
        user_id: str,
        date_filter: str = "today"
    ) -> Dict[str, Any]:
        """获取番茄钟计数

        通过查询专注会话列表，统计指定时间范围内的番茄钟数量

        Args:
            user_id: 用户ID
            date_filter: 日期筛选（today/week/month）

        Returns:
            Dict[str, Any]: 包含count字段的统计结果

        Raises:
            HTTPException: 当Focus微服务返回错误时
        """
        # 调用get_sessions获取会话列表
        # 注意：Focus微服务应该支持date_filter参数，如果不支持则需要在这里进行筛选
        response = await self.client.get(
            "/focus/sessions",
            params={
                "user_id": user_id,
                "date_filter": date_filter,
                "page": 1,
                "page_size": 100  # 最大100（Focus微服务限制）
            }
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        # 解析响应并统计番茄钟数量
        result = response.json()

        # 如果微服务已经提供了count字段，直接返回
        if "data" in result and isinstance(result["data"], dict) and "count" in result["data"]:
            return result

        # 否则，统计sessions中session_type为"focused"的数量
        sessions = result.get("data", {}).get("sessions", []) if isinstance(result.get("data"), dict) else []
        count = len([s for s in sessions if s.get("session_type") == "focused"])

        return {
            "code": 200,
            "success": True,
            "message": "番茄钟计数查询成功",
            "data": {
                "count": count,
                "period": date_filter
            }
        }

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
