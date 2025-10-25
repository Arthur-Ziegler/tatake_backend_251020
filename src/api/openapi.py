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
            "description": """
# TaKeKe 任务管理API服务

TaKeKe是一个现代化的任务管理系统，提供专注时间管理、奖励机制和AI智能对话等功能。

## 主要功能

### 🎯 任务管理
- 创建、编辑、删除任务
- 任务分类和标签管理
- 任务优先级和进度跟踪
- 任务统计和分析

### 🍅 番茄钟专注
- 专注会话管理
- 自定义专注时长
- 休息时间设置
- 专注统计报告

### 🏆 奖励系统
- 积分奖励机制
- 成就徽章系统
- 等级升级体系
- 奖励兑换功能

### 🤖 AI智能对话
- 任务建议和规划
- 专注提醒和激励
- 个性化指导
- 智能问答

## 技术特性

- **现代化架构**: 基于FastAPI框架，支持异步处理
- **统一响应格式**: 所有API响应采用标准格式，包含TraceID追踪
- **完整错误处理**: 详细的错误信息和本地化支持
- **安全认证**: JWT + RefreshToken双重认证机制
- **性能优化**: Redis缓存、数据库连接池、请求限流
- **实时监控**: 完整的日志记录和性能监控

## 使用指南

### 认证方式
API使用Bearer Token认证，在请求头中添加：
```
Authorization: Bearer <your_token>
```

### 响应格式
所有响应都采用统一格式：
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {...},
  "timestamp": "2024-01-01T00:00:00Z",
  "traceId": "unique-trace-id"
}
```

### 错误处理
错误响应包含详细的错误信息和TraceID，便于问题定位。

## 开发支持

- **Swagger UI**: `/docs` - 交互式API文档
- **ReDoc**: `/redoc` - 美观的API文档
- **OpenAPI**: `/openapi.json` - 标准API规范
- **健康检查**: `/health` - 服务状态检查
""",
            "version": config.app_version,
            "termsOfService": "https://tatake.app/terms",
            "contact": {
                "name": "TaKeKe API Support",
                "url": "https://tatake.app/support",
                "email": "api-support@tatake.app"
            },
            "license": {
                "name": "MIT License",
                "url": "https://opensource.org/licenses/MIT"
            }
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
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API密钥认证（预留接口）"
            }
        }

    @staticmethod
    def get_server_info() -> List[Dict[str, Any]]:
        """获取服务器信息"""
        return [
            {
                "url": f"http://{config.api_host}:{config.api_port}{config.api_prefix}",
                "description": "开发环境服务器"
            },
            {
                "url": f"https://api.tatake.app{config.api_prefix}",
                "description": "生产环境服务器"
            }
        ]

    @staticmethod
    def get_external_docs() -> Dict[str, str]:
        """获取外部文档链接"""
        return {
            "description": "完整的API文档和开发指南",
            "url": "https://docs.tatake.app"
        }

    @staticmethod
    def get_examples() -> Dict[str, Any]:
        """获取示例数据 - 遵循OpenAPI 3.1规范"""
        return {
            # 成功响应示例
            "SuccessResponse": {
                "summary": "标准成功响应",
                "description": "API调用成功时的标准响应格式，包含业务数据和追踪信息",
                "value": {
                    "code": 200,
                    "message": "操作成功",
                    "data": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "完成项目文档编写",
                        "description": "编写完整的API文档和用户指南",
                        "status": "completed",
                        "priority": "high",
                        "completion_percentage": 100,
                        "tags": ["文档", "项目"],
                        "created_at": "2025-01-15T09:00:00Z",
                        "updated_at": "2025-01-15T15:30:00Z"
                    },
                    "timestamp": "2025-01-15T15:30:00Z",
                    "traceId": "550e8400-e29b-41d4-a716-446655440000"
                }
            },

            # 错误响应示例
            "ErrorResponse": {
                "summary": "标准错误响应",
                "description": "API调用失败时的标准响应格式，包含详细错误信息和追踪ID",
                "value": {
                    "code": 4001,
                    "message": "请求参数验证失败",
                    "data": {
                        "field": "title",
                        "error": "任务标题不能为空",
                        "received_value": ""
                    },
                    "timestamp": "2025-01-15T15:30:00Z",
                    "traceId": "550e8400-e29b-41d4-a716-446655440000",
                    "errorCode": "VALIDATION_ERROR"
                }
            },

            # 任务完成奖励示例
            "TaskCompletionReward": {
                "summary": "任务完成奖励响应",
                "description": "完成任务时获得的奖励详情，包含积分或奖品信息",
                "value": {
                    "code": 200,
                    "message": "任务完成，奖励已发放",
                    "data": {
                        "task": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "title": "完成项目文档",
                            "status": "completed",
                            "completion_percentage": 100
                        },
                        "reward_earned": {
                            "type": "points",
                            "transaction_id": "550e8400-e29b-41d4-a716-446655440001",
                            "amount": 100,
                            "reward_id": None,
                            "message": "Top3任务完成，获得100积分奖励"
                        }
                    },
                    "timestamp": "2025-01-15T15:30:00Z",
                    "traceId": "550e8400-e29b-41d4-a716-446655440000"
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

    # 添加联系人和许可证信息
    openapi_schema["info"].update({
        "contact": openapi_config.get_api_info()["contact"],
        "license": openapi_config.get_api_info()["license"],
        "termsOfService": openapi_config.get_api_info()["termsOfService"]
    })

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

    # 添加外部文档
    openapi_schema["externalDocs"] = openapi_config.get_external_docs()

    # 添加全局安全要求
    openapi_schema["security"] = [
        {"BearerAuth": []}
    ]

    # 移除过度的 x- 扩展，保持简洁

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_openapi(app: FastAPI) -> None:
    """设置OpenAPI文档"""
    # 设置自定义OpenAPI函数
    app.openapi = lambda: custom_openapi(app)