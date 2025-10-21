"""
Task领域Schema定义

定义任务管理相关的请求和响应Schema，确保API接口的数据格式统一和验证。

Schema设计原则：
1. 统一格式：所有API使用统一的响应格式
2. 完整验证：使用Pydantic进行严格的数据验证
3. 清晰文档：每个字段都有详细的说明
4. 向后兼容：预留扩展空间，便于后续版本升级

Schema分类：
1. 请求Schema：用于接收API请求数据
2. 响应Schema：用于返回API响应数据
3. 查询Schema：用于处理查询参数
4. 分页Schema：用于处理分页信息

API端点对应的Schema：
- POST /tasks -> CreateTaskRequest -> TaskResponse
- GET /tasks/{id} -> TaskResponse
- PUT /tasks/{id} -> UpdateTaskRequest -> TaskResponse
- DELETE /tasks/{id} -> TaskDeleteResponse
- GET /tasks -> TaskListQuery -> TaskListResponse

作者：TaKeKe团队
版本：1.0.0
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, validator, model_validator
from pydantic_core import ValidationError

# 导入相关模型
from .models import TaskStatusConst, TaskPriorityConst
from src.domains.auth.schemas import UnifiedResponse

# 定义类型别名以保持兼容性
TaskStatus = str
TaskPriority = str


# ===== 请求Schema =====

class CreateTaskRequest(BaseModel):
    """
    创建任务请求Schema

    用于创建新任务的API请求。只包含创建任务时必要的字段，
    其他字段可以使用默认值或在创建后通过更新API设置。

    必填字段：
    - title: 任务标题（1-100字符）

    可选字段：
    - description: 任务描述
    - status: 任务状态（默认为pending）
    - priority: 任务优先级（默认为medium）
    - parent_id: 父任务ID
    - tags: 任务标签列表
    - due_date: 截止日期
    - planned_start_time: 计划开始时间
    - planned_end_time: 计划结束时间

    验证规则：
    - title长度必须在1-100字符之间
    - 如果设置parent_id，必须为有效的UUID
    - 如果设置时间范围，结束时间必须晚于开始时间
    - tags最多包含10个标签，每个标签最多20字符
    """
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",  # 禁止额外字段
        json_schema_extra={
            "example": {
                "title": "完成项目文档",
                "description": "编写项目的详细技术文档和用户手册",
                "status": "pending",
                "priority": "high",
                "parent_id": "550e8400-e29b-41d4-a716-446655440000",
                "tags": ["文档", "项目"],
                "due_date": "2024-12-31T23:59:59Z",
                "planned_start_time": "2024-12-20T09:00:00Z",
                "planned_end_time": "2024-12-30T18:00:00Z"
            }
        }
    )

    # 必填字段
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="任务标题，1-100字符，必填"
    )

    # 可选字段
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="任务描述，最多5000字符"
    )
    status: TaskStatus = Field(
        default=TaskStatusConst.PENDING,
        description="任务状态：pending/in_progress/completed"
    )
    priority: TaskPriority = Field(
        default=TaskPriorityConst.MEDIUM,
        description="任务优先级：low/medium/high"
    )
    parent_id: Optional[UUID] = Field(
        default=None,
        description="父任务ID，支持任务树结构"
    )
    tags: Optional[List[str]] = Field(
        default=[],
        max_length=10,
        description="任务标签列表，最多10个标签"
    )
    due_date: Optional[datetime] = Field(
        default=None,
        description="任务截止日期（ISO 8601格式）"
    )
    planned_start_time: Optional[datetime] = Field(
        default=None,
        description="计划开始时间（ISO 8601格式）"
    )
    planned_end_time: Optional[datetime] = Field(
        default=None,
        description="计划结束时间（ISO 8601格式）"
    )

    @validator('tags')
    def validate_tags(cls, v):
        """验证标签列表"""
        if v is None:
            return []

        # 检查每个标签的长度
        for tag in v:
            if not isinstance(tag, str):
                raise ValueError("标签必须是字符串")
            if len(tag) == 0:
                raise ValueError("标签不能为空")
            if len(tag) > 20:
                raise ValueError("每个标签最多20个字符")

        # 去重
        return list(set(v))

    @model_validator(mode='after')
    def validate_time_range(self):
        """验证时间范围的合理性"""
        if self.planned_start_time and self.planned_end_time:
            if self.planned_end_time <= self.planned_start_time:
                raise ValueError("计划结束时间必须晚于计划开始时间")

        if self.due_date and self.planned_end_time:
            if self.due_date < self.planned_end_time:
                raise ValueError("截止日期不能早于计划结束时间")

        return self


class UpdateTaskRequest(BaseModel):
    """
    更新任务请求Schema

    用于更新现有任务的API请求。所有字段都是可选的，
    支持部分更新（只更新提供的字段）。

    字段说明：
    - 所有字段都是可选的，支持部分更新
    - 更新时会验证字段的有效性
    - 时间字段的验证规则与创建时相同
    - tags字段会完全替换，不是追加

    特殊说明：
    - 如果parent_id设置为None，会将任务移至根级别
    - 如果tags设置为空列表，会清空所有标签
    """
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "title": "更新后的任务标题",
                "description": "更新后的任务描述",
                "status": "in_progress",
                "priority": "high",
                "parent_id": None,
                "tags": ["更新", "测试"],
                "due_date": "2024-12-25T23:59:59Z",
                "planned_start_time": "2024-12-15T09:00:00Z",
                "planned_end_time": "2024-12-20T18:00:00Z"
            }
        }
    )

    # 所有字段都是可选的
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="任务标题，1-100字符"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="任务描述，最多5000字符"
    )
    status: Optional[TaskStatus] = Field(
        default=None,
        description="任务状态：pending/in_progress/completed"
    )
    priority: Optional[TaskPriority] = Field(
        default=None,
        description="任务优先级：low/medium/high"
    )
    parent_id: Optional[UUID] = Field(
        default=None,
        description="父任务ID，支持任务树结构"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="任务标签列表，最多10个标签"
    )
    due_date: Optional[datetime] = Field(
        default=None,
        description="任务截止日期（ISO 8601格式）"
    )
    planned_start_time: Optional[datetime] = Field(
        default=None,
        description="计划开始时间（ISO 8601格式）"
    )
    planned_end_time: Optional[datetime] = Field(
        default=None,
        description="计划结束时间（ISO 8601格式）"
    )

    @validator('tags')
    def validate_tags(cls, v):
        """验证标签列表"""
        if v is None:
            return None  # 表示不更新标签字段

        # 检查每个标签的长度
        for tag in v:
            if not isinstance(tag, str):
                raise ValueError("标签必须是字符串")
            if len(tag) == 0:
                raise ValueError("标签不能为空")
            if len(tag) > 20:
                raise ValueError("每个标签最多20个字符")

        # 去重
        return list(set(v))

    @model_validator(mode='after')
    def validate_time_range(self):
        """验证时间范围的合理性"""
        if self.planned_start_time and self.planned_end_time:
            if self.planned_end_time <= self.planned_start_time:
                raise ValueError("计划结束时间必须晚于计划开始时间")

        return self


class TaskListQuery(BaseModel):
    """
    任务列表查询Schema

    用于获取任务列表的API查询参数。支持分页、筛选和排序。

    查询参数：
    - page: 页码（从1开始）
    - page_size: 每页大小
    - status: 按状态筛选（支持多选）
    - priority: 按优先级筛选（支持多选）
    - parent_id: 按父任务ID筛选
    - include_deleted: 是否包含已删除的任务
    - due_before: 截止日期筛选（早于指定日期）
    - due_after: 截止日期筛选（晚于指定日期）
    - search: 搜索关键词（搜索标题和描述）
    - sort_by: 排序字段
    - sort_order: 排序方向
    """
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )

    # 分页参数
    page: int = Field(
        default=1,
        ge=1,
        description="页码，从1开始"
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="每页大小，1-100"
    )

    # 筛选参数
    status: Optional[List[TaskStatus]] = Field(
        default=None,
        description="按状态筛选，支持多选"
    )
    priority: Optional[List[TaskPriority]] = Field(
        default=None,
        description="按优先级筛选，支持多选"
    )
    parent_id: Optional[UUID] = Field(
        default=None,
        description="按父任务ID筛选"
    )
    include_deleted: bool = Field(
        default=False,
        description="是否包含已删除的任务"
    )
    due_before: Optional[datetime] = Field(
        default=None,
        description="截止日期筛选，早于指定日期"
    )
    due_after: Optional[datetime] = Field(
        default=None,
        description="截止日期筛选，晚于指定日期"
    )
    search: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="搜索关键词，搜索标题和描述"
    )

    # 排序参数
    sort_by: str = Field(
        default="created_at",
        description="排序字段：created_at/updated_at/due_date/priority/title"
    )
    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
        description="排序方向：asc/desc"
    )

    @validator('sort_by')
    def validate_sort_by(cls, v):
        """验证排序字段"""
        allowed_fields = {
            'created_at', 'updated_at', 'due_date',
            'priority', 'title', 'status'
        }
        if v not in allowed_fields:
            raise ValueError(f"排序字段必须是以下之一：{', '.join(allowed_fields)}")
        return v


# ===== 响应Schema =====

class TaskResponse(BaseModel):
    """
    任务响应Schema

    用于返回单个任务的详细信息。包含任务的所有字段和计算字段。

    字段说明：
    - 包含任务的所有基本字段
    - 添加计算字段：is_overdue, duration_minutes
    - 时间字段使用ISO 8601格式返回
    - parent_id在为None时返回null
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "title": "完成项目文档",
                "description": "编写项目的详细技术文档和用户手册",
                "status": "in_progress",
                "priority": "high",
                "parent_id": "550e8400-e29b-41d4-a716-446655440002",
                "tags": ["文档", "项目"],
                "due_date": "2024-12-31T23:59:59Z",
                "planned_start_time": "2024-12-20T09:00:00Z",
                "planned_end_time": "2024-12-30T18:00:00Z",
                "is_deleted": False,
                "created_at": "2024-12-15T10:00:00Z",
                "updated_at": "2024-12-16T14:30:00Z",
                "is_overdue": False,
                "duration_minutes": 540
            }
        }
    )

    # 基本字段
    id: UUID = Field(..., description="任务ID")
    user_id: UUID = Field(..., description="用户ID")
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    status: TaskStatus = Field(..., description="任务状态")
    priority: TaskPriority = Field(..., description="任务优先级")
    parent_id: Optional[UUID] = Field(None, description="父任务ID")
    tags: List[str] = Field(default=[], description="任务标签")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    planned_start_time: Optional[datetime] = Field(None, description="计划开始时间")
    planned_end_time: Optional[datetime] = Field(None, description="计划结束时间")
    is_deleted: bool = Field(..., description="是否已删除")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    # 计算字段
    is_overdue: bool = Field(..., description="是否过期")
    duration_minutes: Optional[int] = Field(None, description="计划持续时间（分钟）")


class PaginationInfo(BaseModel):
    """
    分页信息Schema

    用于返回列表数据的分页信息。

    字段说明：
    - current_page: 当前页码
    - page_size: 每页大小
    - total_count: 总记录数
    - total_pages: 总页数
    - has_next: 是否有下一页
    - has_prev: 是否有上一页
    """
    model_config = ConfigDict(from_attributes=True)

    current_page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_count: int = Field(..., description="总记录数")
    total_pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class TaskListResponse(BaseModel):
    """
    任务列表响应Schema

    用于返回任务列表和分页信息。

    结构说明：
    - tasks: 任务列表
    - pagination: 分页信息
    """
    model_config = ConfigDict(from_attributes=True)

    tasks: List[TaskResponse] = Field(..., description="任务列表")
    pagination: PaginationInfo = Field(..., description="分页信息")


class TaskDeleteResponse(BaseModel):
    """
    任务删除响应Schema

    用于返回任务删除操作的结果。

    字段说明：
    - deleted_task_id: 被删除的任务ID
    - deleted_count: 删除的任务总数（包括级联删除的子任务）
    - cascade_deleted: 是否有级联删除的子任务
    """
    model_config = ConfigDict(from_attributes=True)

    deleted_task_id: UUID = Field(..., description="被删除的任务ID")
    deleted_count: int = Field(..., description="删除的任务总数")
    cascade_deleted: bool = Field(..., description="是否有级联删除")


# ===== 统一响应格式 =====

class TaskCreateResponse(UnifiedResponse):
    """
    任务创建响应

    继承自UnifiedResponse，data字段包含创建的任务信息。
    """
    data: TaskResponse = Field(..., description="创建的任务信息")


class TaskGetResponse(UnifiedResponse):
    """
    任务获取响应

    继承自UnifiedResponse，data字段包含获取的任务信息。
    """
    data: TaskResponse = Field(..., description="获取的任务信息")


class TaskUpdateResponse(UnifiedResponse):
    """
    任务更新响应

    继承自UnifiedResponse，data字段包含更新后的任务信息。
    """
    data: TaskResponse = Field(..., description="更新后的任务信息")


class TaskDeleteResponseWrapper(UnifiedResponse):
    """
    任务删除响应

    继承自UnifiedResponse，data字段包含删除操作的结果。
    """
    data: TaskDeleteResponse = Field(..., description="删除操作的结果")


class TaskListResponseWrapper(UnifiedResponse):
    """
    任务列表响应

    继承自UnifiedResponse，data字段包含任务列表和分页信息。
    """
    data: TaskListResponse = Field(..., description="任务列表和分页信息")