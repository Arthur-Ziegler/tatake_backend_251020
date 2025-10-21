"""
TaKeKe API 主应用

基于FastAPI框架的RESTful API应用，提供完整的用户任务管理服务。
"""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.config import config
from src.api.middleware import (
    CORSMiddleware,
    LoggingMiddleware,
    ExceptionHandlerMiddleware,
    RateLimitMiddleware,
    SecurityMiddleware,
    AuthMiddleware
)
from src.api.responses import create_success_response, create_error_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print(f"🚀 {config.app_name} v{config.app_version} 正在启动...")
    print(f"📝 环境: {'开发' if config.debug else '生产'}")
    print(f"🌐 服务地址: http://{config.api_host}:{config.api_port}{config.api_prefix}")

    # 初始化依赖注入系统
    from .dependencies import initialize_dependencies
    await initialize_dependencies()
    print("✅ 依赖注入系统初始化完成")

    print("✅ 服务启动完成")

    yield

    # 关闭时执行
    print("🛑 服务正在关闭...")

    # 清理依赖注入系统
    from .dependencies import cleanup_dependencies
    await cleanup_dependencies()
    print("✅ 依赖注入系统已清理")

    print("✅ 服务已关闭")


# 创建FastAPI应用实例
app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description="TaKeKe任务管理API服务",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# 设置OpenAPI文档配置
from .openapi import setup_openapi
setup_openapi(app)

# 添加全局异常处理器
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """处理HTTP异常（404、405等）"""
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
        status_code=exc.status_code,
        error_code=f"HTTP_{exc.status_code}"
    )


# 添加中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)  # 启用响应压缩
app.add_middleware(SecurityMiddleware)  # 安全中间件
app.add_middleware(CORSMiddleware)  # CORS中间件
app.add_middleware(LoggingMiddleware)  # 日志中间件
app.add_middleware(RateLimitMiddleware)  # 限流中间件
app.add_middleware(ExceptionHandlerMiddleware)  # 异常处理中间件
app.add_middleware(AuthMiddleware)  # 认证中间件


# 根路径
@app.get("/", tags=["系统"])
async def root(request: Request):
    """根路径，返回API信息"""
    # 获取请求ID
    trace_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    return create_success_response(
        data={
            "name": config.app_name,
            "version": config.app_version,
            "description": "TaKeKe任务管理API服务",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "api_prefix": config.api_prefix
        },
        message="API服务正常运行",
        trace_id=trace_id
    )


# 健康检查
@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查端点"""
    return create_success_response(
        data={
            "status": "healthy",
            "timestamp": time.time(),
            "version": config.app_name + " v" + config.app_version
        },
        message="服务健康"
    )


# API信息
@app.get(f"{config.api_prefix}/info", tags=["系统"])
async def api_info():
    """API信息端点"""
    return create_success_response(
        data={
            "api_name": config.app_name,
            "api_version": config.app_version,
            "api_prefix": config.api_prefix,
            "endpoints": {
                "认证系统": 7
            },
            "total_endpoints": 7,
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json"
            },
            "status": "认证领域已完成，其他领域开发中"
        },
        message="API信息 - 当前仅包含认证系统"
    )


# 添加API路由模块
# from src.api.routers import user, tasks, chat, focus, rewards_new, statistics_new
from src.domains.auth.router import router as auth_router

# 使用新的认证领域路由
app.include_router(auth_router, prefix=config.api_prefix, tags=["认证系统"])

# 其他路由暂时注释掉，等待DDD架构实现
# app.include_router(user.router, prefix=config.api_prefix, tags=["用户管理"])
# app.include_router(tasks.router, prefix=config.api_prefix, tags=["任务管理"])
# app.include_router(chat.router, prefix=config.api_prefix, tags=["AI对话"])
# app.include_router(focus.router, prefix=f"{config.api_prefix}/focus", tags=["专注系统"])
# app.include_router(rewards_new.router, prefix=f"{config.api_prefix}/rewards", tags=["奖励系统"])
# app.include_router(rewards_new.router, prefix=f"{config.api_prefix}/points", tags=["积分系统"])
# app.include_router(statistics_new.router, prefix=f"{config.api_prefix}/statistics", tags=["统计分析"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )