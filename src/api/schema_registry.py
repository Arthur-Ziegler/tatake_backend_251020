"""
OpenAPI Schema手动注册模块

解决FastAPI无法自动注册所有Schema的问题，
通过手动导入和注册所有Pydantic模型来确保Swagger UI能正确显示示例数据。
"""

from typing import Dict, Any, Type
from pydantic import BaseModel

# 手动导入所有域的Schema，确保它们被Python解释器加载
from src.domains.auth.schemas import (
    UnifiedResponse, AuthTokenResponse, AuthTokenData,
    GuestInitRequest, WeChatRegisterRequest, WeChatLoginRequest,
    GuestUpgradeRequest, TokenRefreshRequest
)

from src.domains.task.schemas import (
    CreateTaskRequest, UpdateTaskRequest, TaskResponse, TaskListResponse,
    TaskDeleteResponse, TaskStatus, TaskPriority, CompleteTaskRequest,
    CompleteTaskResponse, UncompleteTaskRequest, UncompleteTaskResponse,
    TaskListQuery
)

from src.domains.chat.schemas import (
    SendMessageRequest, MessageResponse, ChatHistoryResponse,
    CreateSessionRequest, ChatSessionResponse, SessionListResponse,
    SessionInfoResponse, DeleteSessionResponse, ChatHealthResponse,
    ChatMessageItem, ChatSessionItem
)

from src.domains.focus.schemas import (
    StartFocusRequest, FocusSessionResponse, FocusSessionListResponse,
    FocusOperationResponse, SessionType
)

from src.domains.reward.schemas import (
    RewardResponse, RewardCatalogResponse, RewardRedeemRequest,
    RewardRedeemResponse, PointsBalanceResponse, PointsTransactionResponse,
    PointsTransactionsResponse, UserMaterialsResponse, AvailableRecipesResponse,
    RedeemRecipeRequest, RedeemRecipeResponse, MyRewardsResponse,
    LotteryResult, TaskCompleteResponse, RecipeMaterial,
    RecipeReward, UserMaterial, AvailableRecipe
)

from src.domains.top3.schemas import (
    SetTop3Request, GetTop3Response, Top3Response
)

from src.domains.user.schemas import (
    UserProfileResponse, UpdateProfileRequest, FeedbackRequest
)

# 所有需要注册的Schema模型
ALL_SCHEMAS: Dict[str, Type[BaseModel]] = {
    # 认证系统
    "UnifiedResponse": UnifiedResponse,
    "AuthTokenResponse": AuthTokenResponse,
    "AuthTokenData": AuthTokenData,
    "GuestInitRequest": GuestInitRequest,
    "WeChatRegisterRequest": WeChatRegisterRequest,
    "WeChatLoginRequest": WeChatLoginRequest,
    "GuestUpgradeRequest": GuestUpgradeRequest,
    "TokenRefreshRequest": TokenRefreshRequest,

    # 任务管理
    "CreateTaskRequest": CreateTaskRequest,
    "UpdateTaskRequest": UpdateTaskRequest,
    "TaskResponse": TaskResponse,
    "TaskListResponse": TaskListResponse,
    "TaskDeleteResponse": TaskDeleteResponse,
    "CompleteTaskRequest": CompleteTaskRequest,
    "CompleteTaskResponse": CompleteTaskResponse,
    "UncompleteTaskRequest": UncompleteTaskRequest,
    "UncompleteTaskResponse": UncompleteTaskResponse,
    "TaskListQuery": TaskListQuery,

    # 枚举类型
    "TaskStatus": TaskStatus,
    "TaskPriority": TaskPriority,

    # 聊天系统
    "SendMessageRequest": SendMessageRequest,
    "MessageResponse": MessageResponse,
    "ChatHistoryResponse": ChatHistoryResponse,
    "CreateSessionRequest": CreateSessionRequest,
    "ChatSessionResponse": ChatSessionResponse,
    "SessionListResponse": SessionListResponse,
    "SessionInfoResponse": SessionInfoResponse,
    "DeleteSessionResponse": DeleteSessionResponse,
    "ChatHealthResponse": ChatHealthResponse,
    "ChatMessageItem": ChatMessageItem,
    "ChatSessionItem": ChatSessionItem,

    # 番茄钟系统
    "StartFocusRequest": StartFocusRequest,
    "FocusSessionResponse": FocusSessionResponse,
    "FocusSessionListResponse": FocusSessionListResponse,
    "FocusOperationResponse": FocusOperationResponse,
    "SessionType": SessionType,

    # 奖励系统
    "RewardResponse": RewardResponse,
    "RewardCatalogResponse": RewardCatalogResponse,
    "RewardRedeemRequest": RewardRedeemRequest,
    "RewardRedeemResponse": RewardRedeemResponse,
    "PointsBalanceResponse": PointsBalanceResponse,
    "PointsTransactionResponse": PointsTransactionResponse,
    "PointsTransactionsResponse": PointsTransactionsResponse,
    "UserMaterialsResponse": UserMaterialsResponse,
    "AvailableRecipesResponse": AvailableRecipesResponse,
    "RedeemRecipeRequest": RedeemRecipeRequest,
    "RedeemRecipeResponse": RedeemRecipeResponse,
    "MyRewardsResponse": MyRewardsResponse,
    "LotteryResult": LotteryResult,
    "TaskCompleteResponse": TaskCompleteResponse,
    "RecipeMaterial": RecipeMaterial,
    "RecipeReward": RecipeReward,
    "UserMaterial": UserMaterial,
    "AvailableRecipe": AvailableRecipe,

    # Top3管理
    "SetTop3Request": SetTop3Request,
    "GetTop3Response": GetTop3Response,
    "Top3Response": Top3Response,

    # 用户管理
    "UserProfileResponse": UserProfileResponse,
    "UpdateProfileRequest": UpdateProfileRequest,
    "FeedbackRequest": FeedbackRequest,
}


def register_all_schemas_to_openapi(app) -> None:
    """
    将所有Schema手动注册到FastAPI应用的OpenAPI规范中

    这个函数解决了一个关键问题：FastAPI只会自动注册在路由函数签名中
    直接使用的Pydantic模型。许多Schema模型可能只在响应中被间接使用，
    导致它们不会被自动注册到OpenAPI components/schemas中。

    Args:
        app: FastAPI应用实例
    """
    print(f"🔧 开始注册{len(ALL_SCHEMAS)}个Schema到OpenAPI...")

    if not hasattr(app, "openapi_schema") or app.openapi_schema is None:
        print("❌ app.openapi_schema不存在")
        return

    openapi_schema = app.openapi_schema

    # 确保components/schemas存在
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}

    schemas = openapi_schema["components"]["schemas"]
    print(f"📋 当前已有{len(schemas)}个Schema: {list(schemas.keys())}")

    registered_count = 0

    # 手动注册所有Schema
    for schema_name, schema_model in ALL_SCHEMAS.items():
        if schema_name not in schemas:
            try:
                # 使用Pydantic模型的json_schema方法生成schema
                schema_json = schema_model.model_json_schema(
                    ref_template="#/components/schemas/{model}"
                )

                # 将Pydantic生成的schema转换为OpenAPI格式
                openapi_schema["components"]["schemas"][schema_name] = _convert_pydantic_schema_to_openapi(schema_json)
                registered_count += 1

            except Exception as e:
                print(f"⚠️ Schema注册失败: {schema_name} - {e}")
                continue
        else:
            print(f"✅ Schema已存在: {schema_name}")

    print(f"🎉 成功注册{registered_count}个新Schema，总计{len(openapi_schema['components']['schemas'])}个Schema")

    # 更新应用的OpenAPI schema
    app.openapi_schema = openapi_schema


def _convert_pydantic_schema_to_openapi(pydantic_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    将Pydantic生成的schema转换为OpenAPI 3.0格式

    Args:
        pydantic_schema: Pydantic模型生成的JSON schema

    Returns:
        符合OpenAPI 3.0规范的schema定义
    """
    # 移除Pydantic特有的字段，保留OpenAPI兼容的部分
    openapi_schema = {
        "type": pydantic_schema.get("type", "object"),
        "description": pydantic_schema.get("description", ""),
        "properties": pydantic_schema.get("properties", {}),
        "required": pydantic_schema.get("required", []),
    }

    # 如果有$defs，移动到components/schemas（这通常在调用时处理）
    if "$defs" in pydantic_schema:
        openapi_schema["$defs"] = pydantic_schema["$defs"]

    return openapi_schema


def validate_schema_examples() -> bool:
    """
    验证所有Schema是否都有正确的example参数

    Returns:
        bool: 如果所有Schema都有示例数据则返回True
    """
    missing_examples = []

    for schema_name, schema_model in ALL_SCHEMAS.items():
        try:
            schema_json = schema_model.model_json_schema()
            _check_schema_examples_recursive(schema_json, schema_name, missing_examples)
        except Exception as e:
            missing_examples.append(f"{schema_name}: 检查失败 - {e}")

    if missing_examples:
        print("❌ 发现缺少example的Schema字段:")
        for item in missing_examples:
            print(f"  - {item}")
        return False
    else:
        print("✅ 所有Schema字段都有正确的example参数")
        return True


def _check_schema_examples_recursive(
    schema: Dict[str, Any],
    path: str,
    missing_examples: list,
    parent_field: str = ""
) -> None:
    """
    递归检查schema中所有字段的example参数

    Args:
        schema: 要检查的schema
        path: schema的路径（用于错误报告）
        missing_examples: 缺少example的字段列表
        parent_field: 父字段名（用于递归）
    """
    if not isinstance(schema, dict):
        return

    # 检查当前字段的example
    if "example" not in schema and schema.get("type") in ["string", "integer", "number", "boolean"]:
        field_name = parent_field or path
        if field_name and field_name not in [item.split(":")[0] for item in missing_examples]:
            missing_examples.append(f"{field_name}: 缺少example参数")

    # 递归检查properties
    if "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            _check_schema_examples_recursive(
                prop_schema,
                f"{path}.{prop_name}",
                missing_examples,
                prop_name
            )

    # 递归检查items（数组类型）
    if "items" in schema:
        _check_schema_examples_recursive(
            schema["items"],
            f"{path}[]",
            missing_examples,
            f"{parent_field}[]"
        )


# 导出的主要函数
__all__ = [
    "register_all_schemas_to_openapi",
    "validate_schema_examples",
    "ALL_SCHEMAS"
]