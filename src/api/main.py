"""
TaKeKe API 主应用

基于FastAPI框架的RESTful API应用，提供完整的用户任务管理服务。
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .config import config
from .middleware import (
    CORSMiddleware,
    LoggingMiddleware,
    ExceptionHandlerMiddleware,
    RateLimitMiddleware,
    SecurityMiddleware,
    AuthMiddleware
)
from .responses import create_success_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print(f"🚀 {config.app_name} v{config.app_version} 正在启动...")
    print(f"📝 环境: {'开发' if config.debug else '生产'}")
    print(f"🌐 服务地址: http://{config.api_host}:{config.api_port}{config.api_prefix}")

    # 初始化数据库连接
    # TODO: 添加数据库初始化逻辑

    # 初始化Redis连接
    # TODO: 添加Redis初始化逻辑

    print("✅ 服务启动完成")

    yield

    # 关闭时执行
    print("🛑 服务正在关闭...")

    # 清理资源
    # TODO: 添加资源清理逻辑

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
async def root():
    """根路径，返回API信息"""
    return create_success_response(
        data={
            "name": config.app_name,
            "version": config.app_version,
            "description": "TaKeKe任务管理API服务",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "api_prefix": config.api_prefix
        },
        message="API服务正常运行"
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
                "认证系统": 7,
                "AI对话系统": 4,
                "任务管理": 12,
                "番茄钟系统": 8,
                "奖励系统": 8,
                "统计系统": 3,
                "用户管理": 4
            },
            "total_endpoints": 46,
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json"
            }
        },
        message="API信息"
    )


# TODO: 添加API路由模块
# from .routers import auth, tasks, chat, focus, rewards, statistics, user
# app.include_router(auth.router, prefix=config.api_prefix, tags=["认证系统"])
# app.include_router(tasks.router, prefix=config.api_prefix, tags=["任务管理"])
# app.include_router(chat.router, prefix=config.api_prefix, tags=["AI对话"])
# app.include_router(focus.router, prefix=config.api_prefix, tags=["番茄钟"])
# app.include_router(rewards.router, prefix=config.api_prefix, tags=["奖励系统"])
# app.include_router(statistics.router, prefix=config.api_prefix, tags=["统计分析"])
# app.include_router(user.router, prefix=config.api_prefix, tags=["用户管理"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )