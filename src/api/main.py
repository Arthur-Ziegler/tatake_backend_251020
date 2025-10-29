"""
TaKeKe API 主应用

基于FastAPI框架的综合API应用，提供认证和任务管理功能。
完全使用FastAPI的自然机制，不再干预OpenAPI生成。
"""

import os
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv
from pydantic import ValidationError, BaseModel, Field
from typing import Dict, Any, List

# 加载环境变量
load_dotenv()

from .config import config
from .responses import create_success_response, create_error_response


class HTTPValidationError(BaseModel):
    """HTTP验证错误响应模型"""
    loc: List[str] = Field(description="错误位置")
    msg: str = Field(description="错误消息")
    type: str = Field(description="错误类型")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print(f"🚀 {config.app_name} v{config.app_version} 正在启动...")
    print(f"📝 环境: {'开发' if config.debug else '生产'}")
    print(f"🌐 API服务地址: http://{config.api_host}:{config.api_port}{config.api_prefix}")

    # 认证功能已迁移到微服务，无需本地数据库
    print("✅ 认证微服务集成完成")

    # 初始化任务数据库
    from src.domains.task.database import initialize_task_database
    try:
        initialize_task_database()
        print("✅ 任务数据库初始化完成")
    except Exception as e:
        print(f"❌ 任务数据库初始化失败: {e}")

    # 初始化奖励数据库
    from src.domains.reward.database import initialize_reward_database
    from src.database import get_db_session
    try:
        # 获取数据库会话并初始化
        session_gen = get_db_session()
        session = next(session_gen)
        try:
            initialize_reward_database(session)
            print("✅ 奖励数据库初始化完成")
        finally:
            session.close()
    except Exception as e:
        print(f"❌ 奖励数据库初始化失败: {e}")

    # 初始化聊天数据库
    from src.domains.chat.database import create_tables, check_connection
    try:
        if check_connection():
            create_tables()
            print("✅ 聊天数据库初始化完成")
        else:
            print("❌ 聊天数据库连接失败")
    except Exception as e:
        print(f"❌ 聊天数据库初始化失败: {e}")

    # 初始化Focus数据库
    from src.domains.focus.database import create_focus_tables
    try:
        create_focus_tables()
        print("✅ Focus数据库初始化完成")
    except Exception as e:
        print(f"❌ Focus数据库初始化失败: {e}")

    print("✅ API服务启动完成")

    yield

    # 关闭时执行
    print("🛑 API服务正在关闭...")
    print("✅ API服务已关闭")


# 创建FastAPI应用实例 - 完全自然配置
app = FastAPI(
    title=f"{config.app_name}",
    version=config.app_version,
    description="TaKeKe API服务，提供认证和任务管理功能",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 设置增强版OpenAPI - 确保所有Schema都被正确注册
from src.api.openapi import setup_openapi
setup_openapi(app)


# 添加CORS中间件 - 使用FastAPI原生方法，最宽松配置
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源
    allow_credentials=True,  # 允许认证凭据
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
    expose_headers=["*"],  # 暴露所有响应头
    max_age=86400,  # 预检请求缓存24小时（最长时间）
)


# 添加全局异常处理器
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """处理HTTP异常（404、405等）- 只返回code、message、data三个字段"""
    error_messages = {
        404: "请求的资源未找到",
        405: "请求方法不被允许",
        401: "未授权访问",
        403: "禁止访问",
        422: "请求参数验证失败"
    }

    message = error_messages.get(exc.status_code, exc.detail)

    return create_error_response(
        message=message,
        status_code=exc.status_code
    )


# 根路径
@app.get("/", tags=["系统"])
async def root():
    """根路径，返回API信息 - 只返回code、message、data三个字段"""
    return create_success_response(
        data={
            "name": f"{config.app_name}",
            "version": config.app_version,
            "description": "TaKeKe API服务，提供认证和任务管理功能",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "api_prefix": config.api_prefix,
            "domains": ["认证系统", "任务管理"]
        },
        message="API服务正常运行"
    )


# 健康检查
@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查端点 - 检查微服务和数据库状态"""
    from ...services.auth.client import AuthMicroserviceClient

    # 检查认证微服务
    auth_client = AuthMicroserviceClient()
    try:
        auth_response = await auth_client.health_check()
        is_auth_healthy = auth_response.get("status") == "healthy"
    except Exception as e:
        print(f"认证微服务健康检查失败: {str(e)}")
        is_auth_healthy = False

    # 检查任务数据库
    from src.domains.task.database import get_database_info as get_task_db_info
    task_db_info = get_task_db_info()
    is_task_healthy = task_db_info.get("status") == "healthy"

    # 检查聊天数据库
    from src.domains.chat.database import check_connection as check_chat_connection
    is_chat_healthy = check_chat_connection()

    overall_healthy = is_auth_healthy and is_task_healthy and is_chat_healthy

    return create_success_response(
        data={
            "status": "healthy" if overall_healthy else "unhealthy",
            "services": {
                "authentication": "healthy" if is_auth_healthy else "unhealthy",
                "task_management": "healthy" if is_task_healthy else "unhealthy",
                "chat_service": "healthy" if is_chat_healthy else "unhealthy"
            },
            "version": f"{config.app_name} v{config.app_version}",
            "database": {
                "auth": "microservice" if is_auth_healthy else "disconnected",
                "task": "connected" if is_task_healthy else "disconnected",
                "chat": "connected" if is_chat_healthy else "disconnected"
            }
        },
        message="API服务健康" if overall_healthy else "API服务异常"
    )


# API信息
@app.get(f"{config.api_prefix}/info", tags=["系统"])
async def api_info():
    """API信息端点 - 显示微服务架构信息"""
    from src.domains.task.database import get_database_info as get_task_db_info
    from src.domains.chat.database import get_database_info as get_chat_db_info

    task_db_info = get_task_db_info()
    chat_db_info = get_chat_db_info()

    return create_success_response(
        data={
            "api_name": f"{config.app_name}",
            "api_version": config.app_version,
            "api_prefix": config.api_prefix,
            "service_type": "microservice-enabled-api",
            "domains": {
                "认证系统": {
                    "endpoints": 12,  # 微服务提供的认证端点数量
                    "status": "active",
                    "type": "microservice",
                    "provider": "Auth Service (http://45.152.65.130:8987)",
                    "features": ["微信认证", "邮箱认证", "手机认证", "JWT验证"]
                },
                "任务管理": {
                    "endpoints": 5,
                    "status": "active",
                    "database": task_db_info
                },
                "智能聊天": {
                    "endpoints": 7,
                    "status": "active",
                    "database": chat_db_info
                }
            },
            "total_endpoints": 27,  # 12个auth + 5个task + 7个chat + 3个system
            "database": {
                "auth": "microservice",
                "task": task_db_info,
                "chat": chat_db_info
            },
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
                "auth_service_docs": "http://45.152.65.130:8987/docs"
            },
            "status": "提供微服务认证、任务管理和智能聊天API服务"
        },
        message="API信息 - 微服务认证、任务管理和智能聊天服务"
    )


# 导入所有路由器
from src.api.auth import auth_router  # 使用新的微服务认证路由
from src.domains.task.router import router as task_router
from src.domains.reward.router import router as reward_router, points_router
from src.domains.top3.api import router as top3_router
from src.domains.chat.router import router as chat_router
from src.domains.focus.router import router as focus_router
# from src.domains.user.router import router as user_router  # 临时禁用，待修复auth依赖

# 使用微服务认证路由（不再需要前缀，因为路径已经包含/auth）
app.include_router(auth_router)

# 使用任务领域路由
app.include_router(task_router, prefix=config.api_prefix)

# 使用奖励系统API路由
app.include_router(reward_router, prefix=config.api_prefix)
app.include_router(points_router, prefix=config.api_prefix)

# 使用Top3系统API路由
app.include_router(top3_router, prefix=config.api_prefix)

# 使用聊天领域路由
app.include_router(chat_router, prefix=config.api_prefix)

# 使用用户管理路由
# app.include_router(user_router, prefix=config.api_prefix)  # 临时禁用，待修复auth依赖

# 使用Focus番茄钟领域路由
app.include_router(focus_router, prefix=config.api_prefix)

# CORS 测试端点 - 验证 CORS 配置
@app.get("/test-cors", tags=["系统"])
async def test_cors():
    """测试 CORS 配置的专用端点"""
    return create_success_response(
        data={
            "cors_enabled": True,
            "message": "CORS 测试成功！",
            "access_from_anywhere": True,
            "all_origins_allowed": True,
            "server_time": "2025-10-25"
        },
        message="CORS 配置测试通过"
    )


# 手动注册所有Schema到OpenAPI - 解决泛型模型不自动注册的问题
# 必须在所有路由注册完成后执行
@app.on_event("startup")
async def register_schemas_on_startup():
    """在应用启动时注册所有Schema"""
    from src.api.schema_registry import register_all_schemas_to_openapi
    register_all_schemas_to_openapi(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )