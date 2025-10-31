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
    print(f"⚙️ 端口配置来源: {('环境变量' if os.getenv('API_PORT') else '默认配置')}")

    # 认证功能已迁移到微服务，无需本地数据库
    print("✅ 认证微服务集成完成")

    # Task数据库已迁移到微服务，无需本地初始化
    print("✅ Task微服务集成完成")

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

    # 聊天功能已启用，基于本地LLM实现
    print("✅ 聊天功能已启用（本地LLM实现）")

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
    from src.services.auth.client import AuthMicroserviceClient

    # 检查认证微服务
    auth_client = AuthMicroserviceClient()
    try:
        auth_response = await auth_client.health_check()
        is_auth_healthy = auth_response.get("data", {}).get("status") == "healthy"
    except Exception as e:
        print(f"认证微服务健康检查失败: {str(e)}")
        is_auth_healthy = False

    # 检查Task微服务
    from src.services.task_microservice_client import get_task_microservice_client
    task_client = get_task_microservice_client()
    try:
        is_task_healthy = await task_client.health_check()
    except Exception as e:
        print(f"Task微服务健康检查失败: {str(e)}")
        is_task_healthy = False
        task_db_info = {"status": "unhealthy", "type": "microservice"}
    else:
        task_db_info = {"status": "healthy", "type": "microservice"}

    # 聊天功能已启用
    is_chat_healthy = True

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
                "task": "microservice" if is_task_healthy else "disconnected",
                "chat": "connected" if is_chat_healthy else "disconnected"
            }
        },
        message="API服务健康" if overall_healthy else "API服务异常"
    )


# API信息
@app.get(f"{config.api_prefix}/info", tags=["系统"])
async def api_info():
    """API信息端点 - 显示微服务架构信息"""
    # Task数据库已迁移到微服务
    task_db_info = {"status": "migrated", "type": "microservice", "provider": "Task Service (http://127.0.0.1:20252)"}
    # 聊天功能暂时禁用
    chat_db_info = {"status": "disabled", "reason": "Task microservice migration dependency"}

    return create_success_response(
        data={
            "api_name": f"{config.app_name}",
            "api_version": config.app_version,
            "api_prefix": config.api_prefix,
            "service_type": "microservice-enabled-api",
            "domains": {
                "认证系统": {
                    "endpoints": 4,  # 简化后的认证端点数量
                    "status": "active",
                    "type": "microservice",
                    "provider": "Auth Service (http://45.152.65.130:20251)",
                    "features": ["微信认证", "手机认证", "智能检测", "自动注册", "JWT验证"]
                },
                "任务管理": {
                    "endpoints": 8,  # task微服务 + 本地接口
                    "status": "active",
                    "database": task_db_info
                },
                "番茄钟系统": {
                    "endpoints": 6,
                    "status": "active",
                    "features": ["专注会话管理", "番茄统计", "状态追踪"]
                },
                "Top3管理": {
                    "endpoints": 2,
                    "status": "active",
                    "features": ["设置Top3", "查看Top3"]
                },
                "奖励系统": {
                    "endpoints": 4,
                    "status": "active",
                    "features": ["积分管理", "奖品兑换", "统计查询"]
                }
            },
            "total_endpoints": 24,  # 4个auth + 8个task + 6个focus + 2个top3 + 4个reward
            "database": {
                "auth": "microservice",
                "task": task_db_info,
                "focus": "local",
                "top3": "local",
                "reward": "local"
            },
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
                "auth_service_docs": "http://45.152.65.130:20251/docs"
            },
            "status": "提供微服务认证、任务管理、番茄钟和奖励系统API服务"
        },
        message="API信息 - 微服务认证、任务管理、番茄钟和奖励系统服务"
    )


# API文档接口
@app.get(f"{config.api_prefix}/docs", tags=["系统"])
async def api_docs():
    """API文档接口 - 返回微服务所有自动生成的详细API文档信息"""
    return create_success_response(
        data={
            "title": f"{config.app_name} API文档",
            "version": config.app_version,
            "description": "完整的API文档，包含所有微服务接口的详细信息",
            "documentation_urls": {
                "swagger_ui": "/docs",
                "redoc": "/redoc",
                "openapi_json": "/openapi.json"
            },
            "api_domains": {
                "认证系统": {
                    "base_url": "/auth",
                    "endpoints": [
                        {
                            "path": "/auth/wechat/login",
                            "method": "POST",
                            "summary": "微信登录（自动注册）",
                            "description": "通过微信OpenID登录，自动处理新用户注册"
                        },
                        {
                            "path": "/auth/phone/send-code",
                            "method": "POST",
                            "summary": "发送手机验证码（智能检测）",
                            "description": "智能检测用户状态，自动选择登录或注册场景"
                        },
                        {
                            "path": "/auth/phone/verify",
                            "method": "POST",
                            "summary": "手机验证码登录（智能检测）",
                            "description": "智能检测用户状态，自动处理登录或注册"
                        },
                        {
                            "path": "/auth/token/refresh",
                            "method": "POST",
                            "summary": "刷新访问令牌",
                            "description": "使用刷新令牌获取新的访问令牌"
                        }
                    ],
                    "features": ["智能检测", "自动注册", "统一响应格式", "错误优化"]
                },
                "任务管理": {
                    "base_url": f"{config.api_prefix}/tasks",
                    "endpoints": [
                        {"path": "/tasks", "method": "POST", "summary": "创建任务"},
                        {"path": "/tasks/{{task_id}}", "method": "GET", "summary": "获取任务详情"},
                        {"path": "/tasks/{{task_id}}", "method": "PUT", "summary": "更新任务"},
                        {"path": "/tasks/{{task_id}}", "method": "DELETE", "summary": "删除任务"},
                        {"path": "/tasks", "method": "GET", "summary": "获取任务列表"},
                        {"path": "/tasks/{{task_id}}/complete", "method": "POST", "summary": "完成任务"},
                        {"path": "/tasks/{{task_id}}/uncomplete", "method": "POST", "summary": "取消完成任务"},
                        {"path": "/tasks/statistics", "method": "GET", "summary": "获取任务统计"}
                    ],
                    "type": "微服务代理"
                },
                "番茄钟系统": {
                    "base_url": f"{config.api_prefix}/focus",
                    "endpoints": [
                        {"path": "/focus/sessions", "method": "POST", "summary": "开始专注会话"},
                        {"path": "/focus/sessions/{{session_id}}/pause", "method": "POST", "summary": "暂停专注会话"},
                        {"path": "/focus/sessions/{{session_id}}/resume", "method": "POST", "summary": "恢复专注会话"},
                        {"path": "/focus/sessions/{{session_id}}/complete", "method": "POST", "summary": "完成专注会话"},
                        {"path": "/focus/sessions", "method": "GET", "summary": "获取专注会话列表"},
                        {"path": "/focus/pomodoro-count", "method": "GET", "summary": "查看我的番茄数量"}
                    ],
                    "features": ["会话管理", "状态追踪", "番茄统计", "25分钟规则"]
                },
                "Top3管理": {
                    "base_url": f"{config.api_prefix}/top3",
                    "endpoints": [
                        {"path": "/top3", "method": "POST", "summary": "设置某日Top3"},
                        {"path": "/top3/{{date}}", "method": "GET", "summary": "查看某日Top3"}
                    ],
                    "features": ["日期管理", "排名设置", "免费设置"]
                },
                "奖励系统": {
                    "base_url": f"{config.api_prefix}/rewards",
                    "endpoints": [
                        {"path": "/rewards", "method": "GET", "summary": "获取奖励列表"},
                        {"path": "/rewards/{{reward_id}}/redeem", "method": "POST", "summary": "兑换奖励"},
                        {"path": "/points", "method": "GET", "summary": "获取积分余额"},
                        {"path": "/points/transactions", "method": "GET", "summary": "获取积分流水"}
                    ],
                    "features": ["积分系统", "奖品兑换", "流水记录"]
                }
            },
            "authentication": {
                "type": "JWT Bearer Token",
                "header": "Authorization: Bearer <token>",
                "description": "所有需要认证的接口都需要在请求头中携带有效的JWT令牌"
            },
            "response_format": {
                "format": "UnifiedResponse",
                "structure": {
                    "code": "HTTP状态码或业务状态码",
                    "message": "响应消息",
                    "data": "响应数据"
                }
            },
            "usage_notes": [
                "所有POST/PUT/DELETE操作都需要携带有效的JWT令牌",
                "认证系统提供智能检测功能，自动处理用户注册流程",
                "番茄统计规则：focus会话时长超过25分钟算一个完整番茄",
                "Top3设置不消耗积分，每日可免费设置",
                "任务完成会根据规则自动分发积分或奖品"
            ]
        },
        message="API文档信息 - 完整的微服务接口文档"
    )


# 导入所有路由器
from src.api.auth import auth_router  # 使用新的微服务认证路由
from src.domains.task.router import router as task_router
from src.domains.reward.router import router as reward_router, points_router
from src.domains.top3.router import router as top3_router
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