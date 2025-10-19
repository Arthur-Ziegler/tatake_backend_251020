# API层开发快速指南

## 概述

本文档为API层开发人员提供快速上手指南，展示如何正确集成和使用服务层，包括路由创建、依赖注入、异常处理、认证授权等。

## 🚀 快速开始

### 1. 基本项目结构

```
api/
├── v1/
│   ├── endpoints/
│   │   ├── auth.py      # 认证相关端点
│   │   ├── users.py     # 用户管理端点
│   │   ├── tasks.py     # 任务管理端点
│   │   ├── focus.py     # 专注管理端点
│   │   └── chat.py      # 聊天服务端点
│   ├── dependencies.py # 依赖注入
│   ├── middleware.py    # 中间件
│   └── schemas.py       # 数据模型
├── main.py             # FastAPI应用入口
└── config.py           # 配置管理
```

### 2. 最小化示例

```python
# main.py
from fastapi import FastAPI
from src.services.base import ServiceFactory
from src.repositories.user import UserRepository

app = FastAPI(title="Tatake Backend API", version="1.0.0")

# 全局服务实例
def get_user_service():
    return ServiceFactory.create_service(UserService)

@app.get("/")
async def root():
    return {"message": "Tatake Backend API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 🔌 依赖注入

### 1. 服务依赖

```python
# api/v1/dependencies.py
from fastapi import Depends
from src.services.base import ServiceFactory
from src.services.auth_service import AuthService
from src.services.user_service import UserService
from src.services.task_service import TaskService
from src.services.focus_service import FocusService
from src.services.reward_service import RewardService
from src.services.statistics_service import StatisticsService
from src.services.chat_service import ChatService

# 服务工厂函数
def get_auth_service() -> AuthService:
    """获取AuthService实例"""
    return ServiceFactory.create_service(AuthService)

def get_user_service() -> UserService:
    """获取UserService实例"""
    return ServiceFactory.create_service(UserService)

def get_task_service() -> TaskService:
    """获取TaskService实例"""
    return ServiceFactory.create_service(TaskService)

def get_focus_service() -> FocusService:
    """获取FocusService实例"""
    return ServiceFactory.create_service(FocusService)

def get_reward_service() -> RewardService:
    """获取RewardService实例"""
    return ServiceFactory.create_service(RewardService)

def get_statistics_service() -> StatisticsService:
    """获取StatisticsService实例"""
    return ServiceFactory.create_service(StatisticsService)

def get_chat_service() -> ChatService:
    """获取ChatService实例"""
    return ServiceFactory.create_service(ChatService)
```

### 2. 认证依赖

```python
# api/v1/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.services.auth_service import AuthService

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """获取当前认证用户"""
    try:
        token = credentials.credentials
        payload = auth_service.verify_token(token)

        return {
            "user_id": payload["user_id"],
            "device_id": payload.get("device_id"),
            "is_guest": payload.get("is_guest", False)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[dict]:
    """可选的当前用户（游客访问）"""
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = auth_service.verify_token(token)
        return {
            "user_id": payload["user_id"],
            "device_id": payload.get("device_id"),
            "is_guest": payload.get("is_guest", False)
        }
    except Exception:
        return None
```

### 3. 数据库会话依赖

```python
# api/v1/dependencies.py
from sqlalchemy.orm import Session
from src.database import get_db

def get_services_with_db(db: Session = Depends(get_db)):
    """获取带有数据库会话的服务实例"""
    return {
        "user_service": ServiceFactory.create_service_with_session(UserService, db),
        "task_service": ServiceFactory.create_service_with_session(TaskService, db),
        "focus_service": ServiceFactory.create_service_with_session(FocusService, db),
        # ... 其他服务
    }
```

## 📝 API端点开发

### 1. 用户管理端点

```python
# api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from ..dependencies import get_user_service, get_current_user
from ..schemas import (
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserSettingsResponse,
    UserSettingsUpdateRequest
)

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me/profile", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """获取当前用户资料"""
    try:
        profile = user_service.get_user_profile(current_user["user_id"])
        return UserProfileResponse(**profile)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户资料失败"
        )

@router.put("/me/profile", response_model=UserProfileResponse)
async def update_my_profile(
    profile_data: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """更新当前用户资料"""
    try:
        updated_profile = user_service.update_user_profile(
            current_user["user_id"],
            profile_data.dict(exclude_unset=True)
        )
        return UserProfileResponse(**updated_profile)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户资料失败"
        )

@router.get("/me/settings", response_model=UserSettingsResponse)
async def get_my_settings(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """获取用户设置"""
    try:
        settings = user_service.get_user_settings(current_user["user_id"])
        return UserSettingsResponse(**settings)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户设置失败"
        )

@router.put("/me/settings", response_model=UserSettingsResponse)
async def update_my_settings(
    settings_data: UserSettingsUpdateRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """更新用户设置"""
    try:
        updated_settings = user_service.update_user_settings(
            current_user["user_id"],
            settings_data.dict(exclude_unset=True)
        )
        return UserSettingsResponse(**updated_settings)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户设置失败"
        )
```

### 2. 任务管理端点

```python
# api/v1/endpoints/tasks.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from ..dependencies import get_task_service, get_current_user
from ..schemas import (
    TaskCreateRequest,
    TaskResponse,
    TaskUpdateRequest,
    TaskListResponse
)

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreateRequest,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """创建新任务"""
    try:
        # 添加用户ID到任务数据
        task_dict = task_data.dict()
        task_dict["user_id"] = current_user["user_id"]

        task = task_service.create_task(current_user["user_id"], task_dict)
        return TaskResponse(**task)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建任务失败"
        )

@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤"),
    priority: Optional[str] = Query(None, description="优先级过滤"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """获取任务列表"""
    try:
        # 构建过滤条件
        filters = {"user_id": current_user["user_id"]}
        if status:
            filters["status"] = status
        if priority:
            filters["priority"] = priority

        result = task_service.get_user_tasks(
            current_user["user_id"],
            limit=limit,
            offset=offset,
            **filters
        )

        return TaskListResponse(
            tasks=result["items"],
            total=result["total"],
            offset=result["offset"],
            limit=result["limit"],
            has_more=result["has_more"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务列表失败"
        )

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """获取任务详情"""
    try:
        task = task_service.get_task(task_id, current_user["user_id"])
        return TaskResponse(**task)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务详情失败"
        )

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdateRequest,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """更新任务"""
    try:
        updated_task = task_service.update_task(
            task_id,
            current_user["user_id"],
            task_data.dict(exclude_unset=True)
        )
        return TaskResponse(**updated_task)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新任务失败"
        )

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """删除任务"""
    try:
        task_service.delete_task(task_id, current_user["user_id"])
        return

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除任务失败"
        )

@router.post("/{task_id}/start", response_model=TaskResponse)
async def start_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """开始执行任务"""
    try:
        task = task_service.start_task(task_id, current_user["user_id"])
        return TaskResponse(**task)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="开始任务失败"
        )

@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: str,
    completion_data: dict = {},
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """完成任务"""
    try:
        task = task_service.complete_task(
            task_id,
            current_user["user_id"],
            completion_data
        )
        return TaskResponse(**task)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="完成任务失败"
        )
```

### 3. 专注管理端点

```python
# api/v1/endpoints/focus.py
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from ..dependencies import get_focus_service, get_current_user
from ..schemas import (
    FocusSessionCreateRequest,
    FocusSessionResponse,
    FocusSessionUpdateRequest
)

router = APIRouter(prefix="/focus", tags=["focus"])

@router.post("/sessions", response_model=FocusSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_focus_session(
    session_data: FocusSessionCreateRequest,
    current_user: dict = Depends(get_current_user),
    focus_service: FocusService = Depends(get_focus_service)
):
    """开始专注会话"""
    try:
        session = focus_service.start_focus_session(
            user_id=current_user["user_id"],
            task_id=session_data.task_id,
            planned_duration_minutes=session_data.planned_duration_minutes,
            session_type=session_data.session_type
        )
        return FocusSessionResponse(**session)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="开始专注会话失败"
        )

@router.get("/sessions/{session_id}", response_model=FocusSessionResponse)
async def get_focus_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    focus_service: FocusService = Depends(get_focus_service)
):
    """获取专注会话详情"""
    try:
        session = focus_service.get_focus_session(session_id, current_user["user_id"])
        return FocusSessionResponse(**session)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取专注会话失败"
        )

@router.post("/sessions/{session_id}/pause", response_model=FocusSessionResponse)
async def pause_focus_session(
    session_id: str,
    interruption_reason: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    focus_service: FocusService = Depends(get_focus_service)
):
    """暂停专注会话"""
    try:
        session = focus_service.pause_focus_session(
            session_id=session_id,
            user_id=current_user["user_id"],
            interruption_reason=interruption_reason
        )
        return FocusSessionResponse(**session)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="暂停专注会话失败"
        )

@router.post("/sessions/{session_id}/resume", response_model=FocusSessionResponse)
async def resume_focus_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    focus_service: FocusService = Depends(get_focus_service)
):
    """恢复专注会话"""
    try:
        session = focus_service.resume_focus_session(session_id, current_user["user_id"])
        return FocusSessionResponse(**session)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="恢复专注会话失败"
        )

@router.post("/sessions/{session_id}/complete", response_model=FocusSessionResponse)
async def complete_focus_session(
    session_id: str,
    completion_data: dict,
    current_user: dict = Depends(get_current_user),
    focus_service: FocusService = Depends(get_focus_service)
):
    """完成专注会话"""
    try:
        session = focus_service.complete_focus_session(
            session_id=session_id,
            user_id=current_user["user_id"],
            mood_feedback=completion_data.get("mood_feedback"),
            notes=completion_data.get("notes")
        )
        return FocusSessionResponse(**session)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="完成专注会话失败"
        )
```

## 📋 数据模型 (Schemas)

### 1. 用户相关模型

```python
# api/v1/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

class UserProfileResponse(BaseModel):
    id: str
    username: Optional[str]
    email: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    points: int
    fragments: int
    level: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserSettingsResponse(BaseModel):
    notification_enabled: bool
    focus_duration: int
    break_duration: int
    daily_goal: int
    theme: str
    language: str

class UserSettingsUpdateRequest(BaseModel):
    notification_enabled: Optional[bool] = None
    focus_duration: Optional[int] = None
    break_duration: Optional[int] = None
    daily_goal: Optional[int] = None
    theme: Optional[str] = None
    language: Optional[str] = None
```

### 2. 任务相关模型

```python
class TaskCreateRequest(BaseModel):
    title: str
    description: str
    priority: Optional[str] = "medium"
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    tags: Optional[list] = []

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    status: Optional[str] = None
    tags: Optional[list] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    status: str
    due_date: Optional[datetime]
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    tags: list

    class Config:
        from_attributes = True

class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
    offset: int
    limit: int
    has_more: bool
```

### 3. 专注相关模型

```python
class FocusSessionCreateRequest(BaseModel):
    task_id: str
    planned_duration_minutes: int = 25
    session_type: str = "focus"

class FocusSessionResponse(BaseModel):
    id: str
    task_id: str
    session_type: str
    planned_duration_minutes: int
    actual_duration_minutes: int
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    pause_time: Optional[datetime]
    resume_time: Optional[datetime]
    interruptions_count: int
    mood_feedback: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

## ⚠️ 异常处理

### 1. 全局异常处理器

```python
# api/v1/middleware.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from src.services.exceptions import BusinessException

async def business_exception_handler(request: Request, exc: BusinessException):
    """统一处理业务异常"""

    # 根据异常类型确定HTTP状态码
    status_code = get_status_code_for_exception(exc)

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.user_message,
                "details": exc.details,
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url)
            }
        }
    )

def get_status_code_for_exception(exc: BusinessException) -> int:
    """根据异常类型获取HTTP状态码"""
    status_map = {
        # 这里应该导入实际的异常类
        "AuthenticationException": 401,
        "AuthorizationException": 403,
        "ResourceNotFoundException": 404,
        "ValidationException": 422,
        "DuplicateResourceException": 409,
        "InsufficientBalanceException": 400,
    }

    exception_type = type(exc).__name__
    return status_map.get(exception_type, 400)
```

### 2. 路由级异常处理

```python
# 在每个路由文件中
from fastapi import HTTPException, status

@router.post("/tasks")
async def create_task(
    task_data: TaskCreateRequest,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    try:
        task = task_service.create_task(current_user["user_id"], task_data.dict())
        return {"success": True, "data": TaskResponse(**task)}

    except ValidationException as e:
        # 验证异常返回422状态码
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": e.error_code,
                    "message": e.user_message,
                    "field": e.details.get("field"),
                    "value": e.details.get("value")
                }
            }
        )

    except BusinessException as e:
        # 其他业务异常
        raise HTTPException(status_code=400, detail=e.user_message)

    except Exception as e:
        # 未预期的系统异常
        logger.error(f"Unexpected error in create_task: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
```

## 🔒 认证和授权

### 1. 认证端点

```python
# api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from src.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/guest", response_model=dict)
async def create_guest_account(
    device_id: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """创建游客账号"""
    try:
        result = auth_service.create_guest_account(device_id)
        return {
            "success": True,
            "data": {
                "user_id": result["user_id"],
                "is_guest": True,
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"]
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建游客账号失败"
        )

@router.post("/login", response_model=dict)
async def login(
    phone: str,
    code: str,
    device_id: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """手机号登录"""
    try:
        result = auth_service.login_with_phone(phone, code)
        return {
            "success": True,
            "data": {
                "user_id": result["user_id"],
                "is_guest": False,
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "expires_in": result["expires_in"]
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录失败，请检查手机号和验证码"
        )

@router.post("/refresh", response_model=dict)
async def refresh_token(
    refresh_token: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """刷新访问令牌"""
    try:
        result = auth_service.refresh_token(refresh_token)
        return {
            "success": True,
            "data": {
                "access_token": result["access_token"],
                "expires_in": result["expires_in"]
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌刷新失败"
        )
```

### 2. 权限检查

```python
# api/v1/dependencies.py
from fastapi import HTTPException, status
from functools import wraps

def require_permission(permission: str):
    """权限检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取current_user
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="需要登录"
                )

            # 这里可以添加权限检查逻辑
            # if not has_permission(current_user, permission):
            #     raise HTTPException(
            #         status_code=status.HTTP_403_FORBIDDEN,
            #         detail="权限不足"
            #     )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 使用示例
@router.put("/admin/users/{user_id}")
@require_permission("admin:user:update")
async def admin_update_user(
    user_id: str,
    user_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """管理员更新用户信息"""
    # 管理员操作逻辑
    pass
```

## 📊 中间件

### 1. 请求日志中间件

```python
# api/v1/middleware.py
import time
import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 记录请求开始
        start_time = time.time()

        # 记录请求信息
        logger.info(
            f"Request started: {request.method} {request.url}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "user_agent": request.headers.get("user-agent"),
                "remote_addr": request.client.host if request.client else None
            }
        )

        # 处理请求
        response = await call_next(request)

        # 计算处理时间
        process_time = (time.time() - start_time) * 1000

        # 记录响应信息
        logger.info(
            f"Request completed: {request.method} {request.url} - {response.status_code}",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time_ms": process_time
            }
        )

        # 添加响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        return response
```

### 2. CORS中间件配置

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🧪 测试

### 1. 单元测试示例

```python
# tests/api/test_users.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_my_profile():
    """测试获取用户资料"""
    # 模拟认证
    response = client.get(
        "/api/v1/users/me/profile",
        headers={"Authorization": "Bearer valid_token"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "username" in data

def test_update_my_profile():
    """测试更新用户资料"""
    update_data = {
        "display_name": "新昵称",
        "avatar_url": "https://example.com/avatar.jpg"
    }

    response = client.put(
        "/api/v1/users/me/profile",
        json=update_data,
        headers={"Authorization": "Bearer valid_token"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "新昵称"
    assert data["avatar_url"] == "https://example.com/avatar.jpg"

def test_unauthorized_access():
    """测试未授权访问"""
    response = client.get("/api/v1/users/me/profile")

    assert response.status_code == 401
```

### 2. 集成测试示例

```python
# tests/api/test_tasks_integration.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_task_lifecycle():
    """测试任务生命周期"""
    # 1. 创建任务
    task_data = {
        "title": "测试任务",
        "description": "这是一个测试任务",
        "priority": "high"
    }

    create_response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers={"Authorization": "Bearer valid_token"}
    )

    assert create_response.status_code == 201
    created_task = create_response.json()
    task_id = created_task["id"]

    # 2. 获取任务详情
    get_response = client.get(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": "Bearer valid_token"}
    )

    assert get_response.status_code == 200
    task_detail = get_response.json()
    assert task_detail["title"] == "测试任务"

    # 3. 开始任务
    start_response = client.post(
        f"/api/v1/tasks/{task_id}/start",
        headers={"Authorization": "Bearer valid_token"}
    )

    assert start_response.status_code == 200
    started_task = start_response.json()
    assert started_task["status"] == "in_progress"

    # 4. 完成任务
    complete_response = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        json={"completion_notes": "任务完成"},
        headers={"Authorization": "Bearer valid_token"}
    )

    assert complete_response.status_code == 200
    completed_task = complete_response.json()
    assert completed_task["status"] == "completed"
```

## 🚀 部署配置

### 1. 生产环境配置

```python
# config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # API配置
    API_TITLE: str = "Tatake Backend API"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # 安全配置
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 数据库配置
    DATABASE_URL: str

    # 日志配置
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

### 2. 启动脚本

```python
# main.py
import uvicorn
from config import settings
from fastapi import FastAPI
from api.v1.middleware import RequestLoggingMiddleware

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

# 添加中间件
app.add_middleware(RequestLoggingMiddleware)

# 注册路由
from api.v1.endpoints import auth, users, tasks, focus
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(users.router, prefix=settings.API_PREFIX)
app.include_router(tasks.router, prefix=settings.API_PREFIX)
app.include_router(focus.router, prefix=settings.API_PREFIX)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower()
    )
```

### 3. Docker配置

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/tatake
      - SECRET_KEY=your-secret-key
      - SERVICE_LOG_LEVEL=INFO
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=tatake
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 📈 性能优化

### 1. 缓存策略

```python
# api/v1/cache.py
import redis
import json
from functools import wraps
from typing import Optional

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_response(expire: int = 300):
    """缓存响应装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 尝试从缓存获取
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)

            # 执行函数
            result = await func(*args, **kwargs)

            # 存储到缓存
            redis_client.setex(
                cache_key,
                expire,
                json.dumps(result, default=str)
            )

            return result
        return wrapper
    return decorator

# 使用示例
@router.get("/statistics", response_model=dict)
@cache_response(expire=600)  # 缓存10分钟
async def get_statistics(
    current_user: dict = Depends(get_current_user),
    stats_service: StatisticsService = Depends(get_statistics_service)
):
    return stats_service.get_user_overview_statistics(current_user["user_id"])
```

### 2. 分页优化

```python
# api/v1/pagination.py
from pydantic import BaseModel
from typing import List, Generic, TypeVar

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool

def paginate_query(query_func, page: int, per_page: int, **filters):
    """通用分页查询"""
    offset = (page - 1) * per_page

    # 获取总数
    total = query_func(count_only=True, **filters)

    # 获取数据
    items = query_func(limit=per_page, offset=offset, **filters)

    # 计算分页信息
    pages = (total + per_page - 1) // per_page
    has_next = page < pages
    has_prev = page > 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        has_next=has_next,
        has_prev=has_prev
    )
```

## 🎯 最佳实践

### 1. 响应格式统一

```python
# 统一响应格式
def create_response(data=None, success=True, message=None, error=None):
    """创建统一响应格式"""
    response = {"success": success}

    if success:
        if data is not None:
            response["data"] = data
        if message:
            response["message"] = message
    else:
        response["error"] = error

    return response

# 使用示例
@router.get("/example")
async def example_endpoint():
    try:
        result = some_service_call()
        return create_response(data=result, message="操作成功")
    except BusinessException as e:
        return create_response(
            success=False,
            error={
                "code": e.error_code,
                "message": e.user_message
            }
        )
```

### 2. 输入验证

```python
# 使用Pydantic进行输入验证
from pydantic import BaseModel, validator
from typing import Optional

class TaskCreateRequest(BaseModel):
    title: str
    description: str
    priority: Optional[str] = "medium"
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None

    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('标题不能为空')
        if len(v) > 200:
            raise ValueError('标题长度不能超过200个字符')
        return v.strip()

    @validator('priority')
    def validate_priority(cls, v):
        if v and v not in ['low', 'medium', 'high']:
            raise ValueError('优先级必须是 low、medium 或 high')
        return v

    @validator('estimated_hours')
    def validate_estimated_hours(cls, v):
        if v is not None and (v <= 0 or v > 1000):
            raise ValueError('预估工时必须在0-1000小时之间')
        return v
```

### 3. 错误处理

```python
# 统一错误处理
def handle_service_error(service_func):
    """服务层错误处理装饰器"""
    @wraps(service_func)
    async def wrapper(*args, **kwargs):
        try:
            return await service_func(*args, **kwargs)
        except BusinessException as e:
            # 业务异常直接抛出，由全局异常处理器处理
            raise
        except Exception as e:
            # 系统异常记录日志并抛出
            logger.error(f"Unexpected error in {service_func.__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="内部服务器错误"
            )
    return wrapper
```

---

**最后更新**: 2025-10-20
**版本**: 1.0.0
**维护者**: 开发团队