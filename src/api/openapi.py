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
                "description": "系统相关的接口，包括健康检查、API信息等",
                "externalDocs": {
                    "description": "系统接口文档",
                    "url": "https://docs.tatake.app/system"
                }
            },
            {
                "name": "认证系统",
                "description": "用户认证相关接口，包括登录、注册、令牌管理等",
                "externalDocs": {
                    "description": "认证接口文档",
                    "url": "https://docs.tatake.app/auth"
                }
            },
            {
                "name": "用户管理",
                "description": "用户信息管理相关接口，包括用户资料查询、更新、设置等功能的完整管理",
                "externalDocs": {
                    "description": "用户管理文档",
                    "url": "https://docs.tatake.app/user"
                }
            },
            {
                "name": "任务管理",
                "description": "任务创建、编辑、删除等管理接口",
                "externalDocs": {
                    "description": "任务管理文档",
                    "url": "https://docs.tatake.app/tasks"
                }
            },
            {
                "name": "番茄钟系统",
                "description": "专注时间管理和番茄钟相关接口",
                "externalDocs": {
                    "description": "番茄钟文档",
                    "url": "https://docs.tatake.app/focus"
                }
            },
            {
                "name": "奖励系统",
                "description": "积分、徽章、等级等奖励相关接口",
                "externalDocs": {
                    "description": "奖励系统文档",
                    "url": "https://docs.tatake.app/rewards"
                }
            },
            {
                "name": "统计分析",
                "description": "数据统计和分析相关接口",
                "externalDocs": {
                    "description": "统计分析文档",
                    "url": "https://docs.tatake.app/statistics"
                }
            },
            {
                "name": "AI对话",
                "description": "AI智能对话和建议相关接口",
                "externalDocs": {
                    "description": "AI对话文档",
                    "url": "https://docs.tatake.app/chat"
                }
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

            # 认证成功示例
            "AuthenticationSuccess": {
                "summary": "用户认证成功",
                "description": "微信登录或注册成功时的响应，包含访问令牌和用户信息",
                "value": {
                    "code": 200,
                    "message": "登录成功",
                    "data": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 1800,
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "user": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "wechat_openid": "ox1234567890abcdef",
                            "created_at": "2025-01-01T00:00:00Z"
                        }
                    },
                    "timestamp": "2025-01-15T15:30:00Z",
                    "traceId": "550e8400-e29b-41d4-a716-446655440000"
                }
            }
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

    # 添加扩展信息 - OpenAPI 3.1兼容
    openapi_schema["x-tag-groups"] = [
        {
            "name": "核心功能",
            "description": "系统核心功能模块",
            "tags": ["认证系统", "用户管理", "任务管理"]
        },
        {
            "name": "高级功能",
            "description": "高级业务功能模块",
            "tags": ["番茄钟系统", "奖励系统", "AI对话", "Top3管理"]
        },
        {
            "name": "辅助功能",
            "description": "辅助和管理功能模块",
            "tags": ["统计分析", "积分系统", "系统"]
        }
    ]

    # 添加变更日志扩展
    openapi_schema["x-changelog"] = [
        {
            "version": "1.1.0",
            "date": "2025-01-15",
            "changes": [
                {
                    "type": "enhanced",
                    "description": "升级OpenAPI文档至专业级标准",
                    "impact": "开发者体验显著改善"
                },
                {
                    "type": "added",
                    "description": "添加完整的响应示例和错误处理说明",
                    "impact": "API集成更加便捷"
                }
            ]
        },
        {
            "version": "1.0.0",
            "date": "2025-01-01",
            "changes": [
                {
                    "type": "initial",
                    "description": "初始版本发布，包含基础CRUD功能",
                    "impact": "系统正式上线"
                }
            ]
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_openapi(app: FastAPI) -> None:
    """设置OpenAPI文档"""
    # 设置自定义OpenAPI函数
    app.openapi = lambda: custom_openapi(app)

    # 添加API文档路由
    @app.get("/api-info", tags=["系统"], summary="获取API详细信息")
    async def get_api_info(request: Request):
        """获取API的详细信息和统计数据"""
        from .responses import create_success_response
        from .dependencies import service_factory

        # 获取请求ID
        trace_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        # 获取API统计信息
        total_routes = len([route for route in app.routes if hasattr(route, 'methods')])

        # 按标签分组统计
        routes_by_tag = {}
        for route in app.routes:
            if hasattr(route, 'tags') and route.tags:
                for tag in route.tags:
                    routes_by_tag[tag] = routes_by_tag.get(tag, 0) + 1

        return create_success_response(
            data={
                **OpenAPIConfig.get_api_info(),
                "statistics": {
                    "total_routes": total_routes,
                    "routes_by_tag": routes_by_tag,
                    "openapi_version": "3.1.0",
                    "documentation_urls": {
                        "swagger_ui": app.docs_url,
                        "redoc": app.redoc_url,
                        "openapi_json": app.openapi_url
                    }
                },
                "configuration": {
                    "api_prefix": config.api_prefix,
                    "debug_mode": config.debug,
                    "rate_limit_enabled": config.rate_limit_enabled,
                    "cors_enabled": len(config.allowed_origins) > 0
                }
            },
            message="API信息获取成功",
            trace_id=trace_id
        )

    # 添加文档健康检查
    @app.get("/docs-health", tags=["系统"], summary="文档服务健康检查")
    async def docs_health_check():
        """检查文档服务是否正常工作"""
        from .responses import create_success_response

        return create_success_response(
            data={
                "status": "healthy",
                "services": {
                    "swagger_ui": "available",
                    "redoc": "available",
                    "openapi_json": "available"
                },
                "endpoints": {
                    "swagger_ui": app.docs_url,
                    "redoc": app.redoc_url,
                    "openapi_json": app.openapi_url
                }
            },
            message="文档服务健康"
        )