# FastAPI OpenAPI模型注册完整解决方案

## 问题分析

当前的`ensure_openapi_schemas()`函数只是调用了`model.model_json_schema()`，但这并不能将模型注册到FastAPI的OpenAPI组件中。FastAPI只会在以下情况自动注册Pydantic模型到OpenAPI：

1. 模型用作路由函数的`response_model`参数
2. 模型用作请求体参数（`Body`）
3. 模型用作查询参数（`Query`，通过`Depends`）

## 解决方案

### 方法1：使用自定义OpenAPI函数（推荐）

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

def create_custom_openapi(app: FastAPI):
    """创建自定义OpenAPI函数，手动注册额外的Pydantic模型"""
    
    def custom_openapi():
        # 如果已经有缓存的模式，直接返回
        if app.openapi_schema:
            return app.openapi_schema
        
        # 生成标准的OpenAPI模式
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # 手动添加额外的模型到components/schemas
        from src.domains.auth.schemas import (
            WeChatRegisterRequest, WeChatLoginRequest, TokenRefreshRequest,
            GuestUpgradeRequest, AuthTokenResponse
        )
        from src.domains.task.schemas import (
            CreateTaskRequest, UpdateTaskRequest, CompleteTaskRequest,
            UncompleteTaskRequest, TaskResponse, TaskListQuery
        )
        from src.domains.chat.schemas import (
            CreateSessionRequest, SendMessageRequest, ChatSessionResponse,
            MessageResponse, ChatHistoryResponse
        )
        from src.domains.focus.schemas import (
            StartFocusRequest, FocusSessionResponse, FocusOperationResponse
        )
        from src.domains.reward.schemas import (
            RewardRedeemRequest, RecipeMaterial, RecipeReward,
            RedeemRecipeResponse, UserMaterial
        )
        from src.domains.top3.schemas import (
            SetTop3Request, Top3Response, GetTop3Response
        )
        from src.domains.user.schemas import (
            UpdateProfileRequest, FeedbackRequest, UserProfileResponse
        )

        # 定义要手动注册的模型
        models_to_register = [
            WeChatRegisterRequest, WeChatLoginRequest, TokenRefreshRequest,
            GuestUpgradeRequest, AuthTokenResponse,
            CreateTaskRequest, UpdateTaskRequest, CompleteTaskRequest,
            UncompleteTaskRequest, TaskResponse, TaskListQuery,
            CreateSessionRequest, SendMessageRequest, ChatSessionResponse,
            MessageResponse, ChatHistoryResponse,
            StartFocusRequest, FocusSessionResponse, FocusOperationResponse,
            RewardRedeemRequest, RecipeMaterial, RecipeReward,
            RedeemRecipeResponse, UserMaterial,
            SetTop3Request, Top3Response, GetTop3Response,
            UpdateProfileRequest, FeedbackRequest, UserProfileResponse
        ]
        
        # 使用Pydantic的schema()方法获取模型的JSON模式
        # ref_template参数确保引用的格式正确
        for model in models_to_register:
            try:
                # 使用model.schema()或model.model_json_schema()
                if hasattr(model, 'model_json_schema'):
                    # Pydantic v2
                    schema_dict = model.model_json_schema(ref_template='#/components/schemas/{model}')
                else:
                    # Pydantic v1
                    schema_dict = model.schema(ref_template='#/components/schemas/{model}')
                
                # 添加到OpenAPI组件中
                openapi_schema["components"]["schemas"][model.__name__] = schema_dict
                
            except Exception as e:
                print(f"⚠️ 模型 {model.__name__} 注册失败: {e}")
        
        # 缓存模式
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    return custom_openapi

# 在创建FastAPI应用后使用
def setup_openapi_manual_registration(app: FastAPI):
    """设置手动OpenAPI模型注册"""
    app.openapi = create_custom_openapi(app)
```

### 方法2：直接修改现有的OpenAPI模式

```python
def ensure_openapi_schemas_v2(app: FastAPI):
    """改进的版本：直接修改OpenAPI模式"""
    
    # 获取当前的OpenAPI模式（如果不存在则生成）
    if not app.openapi_schema:
        from fastapi.openapi.utils import get_openapi
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
    
    # 确保components和schemas存在
    if "components" not in app.openapi_schema:
        app.openapi_schema["components"] = {}
    if "schemas" not in app.openapi_schema["components"]:
        app.openapi_schema["components"]["schemas"] = {}
    
    # 导入所有需要注册的模型
    from src.domains.auth.schemas import (
        WeChatRegisterRequest, WeChatLoginRequest, TokenRefreshRequest,
        GuestUpgradeRequest, AuthTokenResponse
    )
    from src.domains.task.schemas import (
        CreateTaskRequest, UpdateTaskRequest, CompleteTaskRequest,
        UncompleteTaskRequest, TaskResponse, TaskListQuery
    )
    # ... 其他模型导入
    
    models = [
        WeChatRegisterRequest, WeChatLoginRequest, TokenRefreshRequest,
        GuestUpgradeRequest, AuthTokenResponse,
        CreateTaskRequest, UpdateTaskRequest, CompleteTaskRequest,
        UncompleteTaskRequest, TaskResponse, TaskListQuery,
        # ... 其他模型
    ]
    
    # 注册每个模型
    for model in models:
        try:
            # 使用Pydantic生成JSON模式
            if hasattr(model, 'model_json_schema'):
                # Pydantic v2
                schema_dict = model.model_json_schema()
            else:
                # Pydantic v1
                schema_dict = model.schema()
            
            # 添加到OpenAPI组件中
            app.openapi_schema["components"]["schemas"][model.__name__] = schema_dict
            
        except Exception as e:
            print(f"⚠️ 模型 {model.__name__} 注册失败: {e}")
```

### 方法3：使用虚拟路由注册（备用方案）

```python
from fastapi import APIRouter
from typing import List

def create_virtual_router_for_schemas():
    """创建一个虚拟路由，专门用于注册模式"""
    router = APIRouter()
    
    # 导入所有模型
    from src.domains.auth.schemas import AuthTokenResponse
    from src.domains.task.schemas import TaskResponse
    # ... 其他导入
    
    # 创建虚拟端点，使用所有需要注册的模型
    @router.post("/__internal__/schemas", include_in_schema=False)
    async def register_schemas(
        # 使用所有需要注册的模型作为参数
        auth_response: AuthTokenResponse = None,
        task_response: TaskResponse = None,
        # ... 其他模型参数
    ):
        """内部使用的虚拟端点，用于强制注册Pydantic模型到OpenAPI"""
        return {"status": "ok"}
    
    return router

# 在主应用中使用
def setup_schema_registration(app: FastAPI):
    """设置模式注册"""
    virtual_router = create_virtual_router_for_schemas()
    app.include_router(virtual_router, tags=["internal"])
```

## 最佳实践建议

### 1. 修改主应用文件

```python
# src/api/main.py

# 替换现有的ensure_openapi_schemas函数
def ensure_openapi_schemas():
    """确保所有Pydantic模型都注册到OpenAPI components - 改进版本"""
    from fastapi.openapi.utils import get_openapi
    
    # 获取或生成OpenAPI模式
    if not app.openapi_schema:
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
    
    # 确保components/schemas存在
    if "components" not in app.openapi_schema:
        app.openapi_schema["components"] = {}
    if "schemas" not in app.openapi_schema["components"]:
        app.openapi_schema["components"]["schemas"] = {}
    
    # 导入所有模型
    from src.domains.auth.schemas import (
        WeChatRegisterRequest, WeChatLoginRequest, TokenRefreshRequest,
        GuestUpgradeRequest, AuthTokenResponse
    )
    from src.domains.task.schemas import (
        CreateTaskRequest, UpdateTaskRequest, CompleteTaskRequest,
        UncompleteTaskRequest, TaskResponse, TaskListQuery
    )
    from src.domains.chat.schemas import (
        CreateSessionRequest, SendMessageRequest, ChatSessionResponse,
        MessageResponse, ChatHistoryResponse
    )
    from src.domains.focus.schemas import (
        StartFocusRequest, FocusSessionResponse, FocusOperationResponse
    )
    from src.domains.reward.schemas import (
        RewardRedeemRequest, RecipeMaterial, RecipeReward,
        RedeemRecipeResponse, UserMaterial
    )
    from src.domains.top3.schemas import (
        SetTop3Request, Top3Response, GetTop3Response
    )
    from src.domains.user.schemas import (
        UpdateProfileRequest, FeedbackRequest, UserProfileResponse
    )

    # 定义要注册的模型列表
    models = [
        WeChatRegisterRequest, WeChatLoginRequest, TokenRefreshRequest,
        GuestUpgradeRequest, AuthTokenResponse,
        CreateTaskRequest, UpdateTaskRequest, CompleteTaskRequest,
        UncompleteTaskRequest, TaskResponse, TaskListQuery,
        CreateSessionRequest, SendMessageRequest, ChatSessionResponse,
        MessageResponse, ChatHistoryResponse,
        StartFocusRequest, FocusSessionResponse, FocusOperationResponse,
        RewardRedeemRequest, RecipeMaterial, RecipeReward,
        RedeemRecipeResponse, UserMaterial,
        SetTop3Request, Top3Response, GetTop3Response,
        UpdateProfileRequest, FeedbackRequest, UserProfileResponse
    ]

    # 注册每个模型到OpenAPI组件
    registered_count = 0
    for model in models:
        try:
            # 使用Pydantic生成JSON模式
            if hasattr(model, 'model_json_schema'):
                # Pydantic v2
                schema_dict = model.model_json_schema()
            else:
                # Pydantic v1
                schema_dict = model.schema()
            
            # 添加到OpenAPI组件中
            app.openapi_schema["components"]["schemas"][model.__name__] = schema_dict
            registered_count += 1
            
        except Exception as e:
            print(f"⚠️ 模型 {model.__name__} 注册失败: {e}")
    
    print(f"✅ OpenAPI组件注册完成，共注册了 {registered_count} 个模型")
```

### 2. 验证注册结果

```python
# 测试脚本
def verify_openapi_registration():
    """验证OpenAPI模型注册"""
    import json
    import requests
    
    # 获取OpenAPI文档
    response = requests.get("http://localhost:8000/openapi.json")
    openapi_spec = response.json()
    
    # 检查组件中的模式
    schemas = openapi_spec.get("components", {}).get("schemas", {})
    
    print(f"OpenAPI中注册的模式数量: {len(schemas)}")
    print("注册的模式名称:")
    for schema_name in sorted(schemas.keys()):
        print(f"  - {schema_name}")
    
    # 检查特定模型是否存在
    expected_models = [
        "AuthTokenResponse",
        "TaskResponse", 
        "ChatSessionResponse",
        "UserProfileResponse"
    ]
    
    for model_name in expected_models:
        if model_name in schemas:
            print(f"✅ {model_name} 已注册")
        else:
            print(f"❌ {model_name} 未注册")
```

## 关键要点

1. **FastAPI内部机制**: FastAPI只在模型实际用于路由操作时自动注册模型到OpenAPI
2. **手动注册**: 可以通过修改`app.openapi_schema["components"]["schemas"]`来手动添加模型
3. **Pydantic模式生成**: 使用`model.model_json_schema()`或`model.schema()`生成JSON模式
4. **最佳时机**: 在所有路由加载完成后执行注册操作

## 注意事项

1. 确保在应用启动后执行注册，避免循环导入
2. 处理好Pydantic v1和v2的兼容性
3. 注册失败时不应影响应用的正常运行
4. 考虑缓存OpenAPI模式以提高性能

这个解决方案提供了完整的手动Pydantic模型注册机制，确保所有模型都能正确显示在OpenAPI文档中。