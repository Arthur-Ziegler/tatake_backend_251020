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
            "BearerAuth": {
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
    """自定义OpenAPI规范"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_config = OpenAPIConfig()

    # 获取基础OpenAPI规范
    openapi_schema = get_openapi(
        title=openapi_config.get_api_info()["title"],
        version=openapi_config.get_api_info()["version"],
        description=openapi_config.get_api_info()["description"],
        routes=app.routes,
        servers=openapi_config.get_server_info(),
        tags=openapi_config.get_tags_metadata()
    )

    # 移除无效的联系人和许可证信息，保持简洁

    # 添加组件 - OpenAPI 3.1规范
    openapi_schema["components"] = {
        "securitySchemes": openapi_config.get_security_schemes(),
        "examples": openapi_config.get_examples(),
        "schemas": {
            # 统一响应格式 - 与 auth/schemas.py 保持一致
            "UnifiedResponse": {
                "type": "object",
                "description": "API统一响应格式，所有API端点都使用这个格式",
                "properties": {
                    "code": {
                        "type": "integer",
                        "description": "HTTP状态码（200, 400, 401, 403, 404等）"
                    },
                    "data": {
                        "description": "响应数据，成功时包含具体数据，失败时为null"
                    },
                    "message": {
                        "type": "string",
                        "description": "响应消息，成功时为success，失败时为具体错误描述"
                    }
                },
                "required": ["code", "message"]
            },

            # 标准响应格式
            "StandardResponse": {
                "type": "object",
                "description": "API标准响应格式",
                "properties": {
                    "code": {
                        "type": "integer",
                        "description": "业务状态码，200表示成功"
                    },
                    "message": {
                        "type": "string",
                        "description": "响应消息"
                    },
                    "data": {
                        "description": "响应数据，结构根据具体接口变化"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "description": "响应时间戳"
                    },
                    "traceId": {
                        "type": "string",
                        "format": "uuid",
                        "description": "追踪ID，用于问题定位"
                    }
                },
                "required": ["code", "message", "timestamp", "traceId"]
            },

            # 错误响应格式
            "ErrorResponse": {
                "allOf": [
                    {"$ref": "#/components/schemas/StandardResponse"},
                    {
                        "type": "object",
                        "properties": {
                            "errorCode": {
                                "type": "string",
                                "description": "错误代码，用于程序化处理"
                            }
                        }
                    }
                ]
            },

            # 分页响应格式
            "PaginatedResponse": {
                "allOf": [
                    {"$ref": "#/components/schemas/StandardResponse"},
                    {
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "object",
                                "properties": {
                                    "items": {
                                        "type": "array",
                                        "description": "数据项列表"
                                    },
                                    "pagination": {
                                        "type": "object",
                                        "properties": {
                                            "current_page": {"type": "integer"},
                                            "total_pages": {"type": "integer"},
                                            "total_count": {"type": "integer"},
                                            "page_size": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                ]
            }
        }
    }

    # 移除外部文档，保持简洁

    # 添加全局安全要求
    # 全局安全要求已通过 router 自动设置，无需重复配置

    # 移除过度的 x- 扩展，保持简洁

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_openapi(app: FastAPI) -> None:
    """设置OpenAPI文档"""
    # 设置自定义OpenAPI函数
    app.openapi = lambda: custom_openapi(app)