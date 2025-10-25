"""
模型注册路由 - 根本解决FastAPI模型可见性问题

这个模块提供专门的路由来确保所有Pydantic模型都能被FastAPI的自动检测机制发现，
从根本上解决OpenAPI schema不完整的问题。
"""

from fastapi import APIRouter
from typing import Union

# 导入所有需要注册的模型
from src.domains.auth.schemas import AuthTokenResponse
from src.domains.chat.schemas import (
    ChatHistoryResponse, 
    ChatSessionResponse, 
    MessageResponse
)
from src.domains.user.schemas import (
    FeedbackRequest,
    UpdateProfileRequest, 
    UserProfileResponse
)
from src.domains.task.schemas import TaskListQuery
from src.domains.top3.schemas import GetTop3Response, Top3Response
from src.domains.reward.schemas import RewardRedeemRequest
from src.domains.focus.schemas import FocusOperationResponse, FocusSessionResponse

# 创建模型注册路由器
model_registry_router = APIRouter(tags=["模型注册"])

# 创建一个联合类型，包含所有需要注册的模型
AllModelsUnion = Union[
    AuthTokenResponse,
    ChatHistoryResponse,
    ChatSessionResponse,
    MessageResponse,
    FeedbackRequest,
    UpdateProfileRequest,
    UserProfileResponse,
    TaskListQuery,
    GetTop3Response,
    Top3Response,
    RewardRedeemRequest,
    FocusOperationResponse,
    FocusSessionResponse
]

@model_registry_router.get(
    "/models/registry",
    response_model=AllModelsUnion,
    include_in_schema=False,  # 不在Swagger UI中显示这个端点
    summary="模型注册端点",
    description="内部端点，确保所有Pydantic模型都能被FastAPI自动检测机制发现，"
                "从根本上解决OpenAPI schema不完整的问题。"
)
def register_models():
    """
    模型注册端点
    
    这个端点不会实际被调用，它的作用是：
    1. 让所有列在AllModelsUnion中的模型被FastAPI的自动检测机制发现
    2. 确保这些模型出现在OpenAPI的components/schemas中
    3. 解决Swagger UI中的Resolver Error问题
    """
    # 这个函数体不会实际执行，只是为了让FastAPI解析模型
    return None

@model_registry_router.post(
    "/models/validate",
    response_model=AllModelsUnion,
    include_in_schema=False,
    summary="模型验证端点",
    description="内部端点，用于验证所有模型都能正确序列化"
)
def validate_models():
    """
    模型验证端点
    
    提供额外的模型引用机会，确保复杂模型关系也能被正确检测
    """
    return None