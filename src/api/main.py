"""
TaKeKe API 主应用

基于FastAPI框架的综合API应用，提供认证和任务管理服务。
包含两个核心领域：认证系统（auth）和任务管理（task）。
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.config import config
from src.api.responses import create_success_response, create_error_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print(f"🚀 {config.app_name} v{config.app_version} 正在启动...")
    print(f"📝 环境: {'开发' if config.debug else '生产'}")
    print(f"🌐 API服务地址: http://{config.api_host}:{config.api_port}{config.api_prefix}")

    # 初始化认证数据库
    from src.domains.auth.database import create_tables, check_connection
    if check_connection():
        create_tables()
        print("✅ 认证数据库初始化完成")
    else:
        print("❌ 认证数据库连接失败")

    # 初始化任务数据库
    from src.domains.task.database import initialize_task_database
    try:
        initialize_task_database()
        print("✅ 任务数据库初始化完成")
    except Exception as e:
        print(f"❌ 任务数据库初始化失败: {e}")

    print("✅ API服务启动完成")

    yield

    # 关闭时执行
    print("🛑 API服务正在关闭...")
    print("✅ API服务已关闭")


# 创建FastAPI应用实例
app = FastAPI(
    title=f"{config.app_name}",
    version=config.app_version,
    description="TaKeKe API服务，提供认证和任务管理功能",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

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


# 根路径
@app.get("/", tags=["系统"])
async def root():
    """根路径，返回API信息"""
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
    """认证服务健康检查端点"""
    from src.domains.auth.database import check_connection

    # 检查认证数据库
    is_auth_healthy = check_connection()

    # 检查任务数据库
    from src.domains.task.database import get_database_info as get_task_db_info
    task_db_info = get_task_db_info()
    is_task_healthy = task_db_info.get("status") == "healthy"

    overall_healthy = is_auth_healthy and is_task_healthy

    return create_success_response(
        data={
            "status": "healthy" if overall_healthy else "unhealthy",
            "services": {
                "authentication": "healthy" if is_auth_healthy else "unhealthy",
                "task_management": "healthy" if is_task_healthy else "unhealthy"
            },
            "timestamp": time.time(),
            "version": f"{config.app_name} v{config.app_version}",
            "database": {
                "auth": "connected" if is_auth_healthy else "disconnected",
                "task": "connected" if is_task_healthy else "disconnected"
            }
        },
        message="API服务健康" if overall_healthy else "API服务异常"
    )


# API信息
@app.get(f"{config.api_prefix}/info", tags=["系统"])
async def api_info():
    """API信息端点"""
    from src.domains.auth.database import get_database_info as get_auth_db_info
    from src.domains.task.database import get_database_info as get_task_db_info

    auth_db_info = get_auth_db_info()
    task_db_info = get_task_db_info()

    return create_success_response(
        data={
            "api_name": f"{config.app_name}",
            "api_version": config.app_version,
            "api_prefix": config.api_prefix,
            "service_type": "full-stack-api",
            "domains": {
                "认证系统": {
                    "endpoints": 5,
                    "status": "active",
                    "database": auth_db_info
                },
                "任务管理": {
                    "endpoints": 5,
                    "status": "active",
                    "database": task_db_info
                }
            },
            "total_endpoints": 13,  # 5个auth + 5个task + 3个system
            "database": {
                "auth": auth_db_info,
                "task": task_db_info
            },
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json"
            },
            "status": "提供完整的认证和任务管理API服务"
        },
        message="API信息 - 认证和任务管理服务"
    )


# 添加认证API路由
from src.domains.auth.router import router as auth_router

# 添加任务API路由
from src.domains.task.router import router as task_router

# 使用认证领域路由
app.include_router(auth_router, prefix=config.api_prefix, tags=["认证系统"])

# 使用任务领域路由
app.include_router(task_router, prefix=config.api_prefix, tags=["任务管理"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )