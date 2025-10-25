"""
OpenAPI文档配置模块

提供API文档的详细配置，包括元数据、标签、安全方案、响应示例等。
"""

import uuid
from typing import Dict, List, Any

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from .config import config


class OpenAPIConfig:
    """OpenAPI配置类"""

    @staticmethod
    def get_api_info() -> Dict[str, Any]:
        """获取API基本信息"""
        return {
            "title": config.app_name,
            "description": "TaKeKe API服务，提供认证、任务管理、奖励系统和智能对话功能",
            "version": config.app_version
        }

    @staticmethod
    def get_tags_metadata() -> List[Dict[str, Any]]:
        """获取API标签元数据"""
        return [
            {
                "name": "系统",
                "description": "系统相关的接口，包括健康检查、API信息等"
            },
            {
                "name": "认证系统",
                "description": "用户认证相关接口，包括登录、注册、令牌管理等"
            },
            {
                "name": "用户管理",
                "description": "用户信息管理相关接口，包括用户资料查询、更新、设置等"
            },
            {
                "name": "任务管理",
                "description": "任务创建、编辑、删除等管理接口"
            },
            {
                "name": "番茄钟系统",
                "description": "专注时间管理和番茄钟相关接口"
            },
            {
                "name": "奖励系统",
                "description": "积分、徽章、等级等奖励相关接口"
            },
            {
                "name": "积分系统",
                "description": "积分流水和积分管理相关接口"
            },
            {
                "name": "Top3管理",
                "description": "每日Top3任务管理相关接口"
            },
            {
                "name": "智能聊天",
                "description": "AI智能对话和建议相关接口"
            }
        ]

    @staticmethod
    def get_security_schemes() -> Dict[str, Any]:
        """获取安全认证方案"""
        return {
            "HTTPBearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT认证令牌，格式：Bearer <token>"
            }
        }

    @staticmethod
    def get_server_info() -> List[Dict[str, Any]]:
        """获取服务器信息"""
        return [
            {
                "url": f"http://{config.api_host}:{config.api_port}{config.api_prefix}",
                "description": "开发环境服务器"
            }
        ]

    @staticmethod
    def get_examples() -> Dict[str, Any]:
        """获取示例数据 - 遵循OpenAPI 3.1规范"""
        return {
            # 成功响应示例
            "SuccessResponse": {
                "summary": "成功响应",
                "description": "API调用成功时的标准响应格式",
                "value": {
                    "code": 200,
                    "message": "操作成功",
                    "data": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "完成项目文档编写",
                        "status": "completed"
                    }
                }
            },

            # 错误响应示例
            "ErrorResponse": {
                "summary": "错误响应",
                "description": "API调用失败时的标准响应格式",
                "value": {
                    "code": 4001,
                    "message": "请求参数验证失败",
                    "data": {
                        "field": "title",
                        "error": "任务标题不能为空"
                    }
                }
            },
        }


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """自定义OpenAPI规范 - 增强版，手动注册所有Schema"""
    if app.openapi_schema:
        return app.openapi_schema

    # 生成基础OpenAPI schema
    openapi_schema = get_openapi(
        title=OpenAPIConfig.get_api_info()["title"],
        version=OpenAPIConfig.get_api_info()["version"],
        description=OpenAPIConfig.get_api_info()["description"],
        routes=app.routes,
        servers=OpenAPIConfig.get_server_info()
    )

    # 添加安全方案
    openapi_schema["components"]["securitySchemes"] = OpenAPIConfig.get_security_schemes()

    # 添加示例数据
    openapi_schema["components"]["examples"] = OpenAPIConfig.get_examples()

    # 【关键】手动注册所有Schema到OpenAPI
    from .schema_registry import register_all_schemas_to_openapi
    app.openapi_schema = openapi_schema
    register_all_schemas_to_openapi(app)

    return app.openapi_schema


def setup_openapi(app: FastAPI) -> None:
    """设置OpenAPI文档 - 使用增强版Schema注册机制"""
    # 使用增强版的custom_openapi，确保所有Schema都被正确注册
    app.openapi = lambda: custom_openapi(app)