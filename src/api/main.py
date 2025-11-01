"""
TaKeKe API 主应用

基于FastAPI框架的综合API应用，提供认证和任务管理功能。
完全使用FastAPI的自然机制，不再干预OpenAPI生成。
"""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from .config import config
from .responses import create_success_response, create_error_response


class HTTPValidationError(Exception):
    """HTTP验证错误响应模型"""
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print(f"🚀 {config.app_name} v{config.app_version} 正在启动...")
    print(f"📝 环境: {'开发' if config.debug else '生产'}")
    print(f"🌐 API服务地址: http://{config.api_host}:{config.api_port}{config.api_prefix}")

    # 认证功能已迁移到微服务，无需本地数据库
    print("✅ 认证微服务集成完成")

    # Task数据库已迁移到微服务，无需本地初始化
    print("✅ Task微服务集成完成")

    # 奖励系统已迁移到微服务，无需本地数据库初始化
    print("✅ 奖励系统已迁移到微服务")

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
    description="TaKeKe API服务，提供认证、任务管理、聊天功能和奖励系统",
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


# API信息端点（仅保留用于用户要求的文档）
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
                "聊天系统": {
                    "base_url": f"{config.api_prefix}/chat",
                    "endpoints": [
                        {"path": "/chat/sessions", "method": "GET", "summary": "查询所有会话列表"},
                        {"path": "/chat/sessions/{{session_id}}/messages", "method": "GET", "summary": "查询聊天记录"},
                        {"path": "/chat/sessions/{{session_id}}", "method": "DELETE", "summary": "删除会话"},
                        {"path": "/chat/sessions/{{session_id}}/chat", "method": "POST", "summary": "聊天接口（流式）"}
                    ],
                    "features": ["会话管理", "消息记录", "流式对话"]
                },
                "任务管理": {
                    "base_url": f"{config.api_prefix}/tasks",
                    "endpoints": [
                        {"path": "/tasks", "method": "GET", "summary": "查询所有任务"},
                        {"path": "/tasks", "method": "POST", "summary": "创建任务"},
                        {"path": "/tasks/{{task_id}}", "method": "DELETE", "summary": "删除任务"},
                        {"path": "/tasks/{{task_id}}", "method": "PUT", "summary": "修改任务"},
                        {"path": "/tasks/special/top3", "method": "POST", "summary": "设置某日Top3"},
                        {"path": "/tasks/special/top3/{{date}}", "method": "GET", "summary": "查看某日top3"},
                        {"path": "/tasks/{{task_id}}/complete", "method": "POST", "summary": "任务完成按钮"},
                        {"path": "/tasks/focus-status", "method": "POST", "summary": "发送专注状态"},
                        {"path": "/tasks/pomodoro-count", "method": "GET", "summary": "查看我的番茄"}
                    ],
                    "type": "微服务代理"
                },
                "奖励系统": {
                    "base_url": f"{config.api_prefix}/rewards",
                    "endpoints": [
                        {"path": "/rewards/prizes", "method": "GET", "summary": "查看我的奖品"},
                        {"path": "/rewards/points", "method": "GET", "summary": "查看我的积分"},
                        {"path": "/rewards/redeem", "method": "POST", "summary": "充值界面"}
                    ],
                    "features": ["积分管理", "奖品兑换", "统计查询"]
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
                "任务完成会根据规则自动分发积分或奖品"
            ]
        },
        message="API文档信息 - 包含认证、聊天、任务管理和奖励系统"
    )


# 导入所有路由器
from src.api.auth import auth_router  # 使用新的微服务认证路由
from src.domains.task.router import router as task_router
from src.api.rewards import router as reward_router  # 使用新的奖励微服务路由器
from src.domains.top3.router import router as top3_router
from src.domains.chat.router import router as chat_router

# 使用微服务认证路由（不再需要前缀，因为路径已经包含/auth）
app.include_router(auth_router)

# 使用任务领域路由
app.include_router(task_router, prefix=config.api_prefix)

# 使用奖励系统API路由（微服务代理模式）
app.include_router(reward_router, prefix=config.api_prefix)

# 使用Top3系统API路由
app.include_router(top3_router, prefix=config.api_prefix)

# 使用聊天领域路由
app.include_router(chat_router, prefix=config.api_prefix)


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