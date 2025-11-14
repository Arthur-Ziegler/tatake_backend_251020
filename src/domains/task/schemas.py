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

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from pydantic_core import ValidationError

# 导入相关模型
from src.core.types import TaskStatus, TaskPriority
# 认证模块已迁移到微服务，使用共用的UnifiedResponse

# 定义常量（原来在models.py中）
class TaskStatusConst:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class TaskPriorityConst:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


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
    - due_date: 截止日期（date格式：YYYY-MM-DD）
    - planned_start_time: 计划开始时间
    - planned_end_time: 计划结束时间

    验证规则：
    - title长度必须在1-100字符之间
    - 如果设置parent_id，必须为有效的字符串ID
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
                "tags": ["文档", "项目"],
                "due_date": "2024-12-31",
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
        description="任务标题，1-100字符，必填",
        example="完成项目文档编写"
    )

    # 可选字段
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="任务描述，最多5000字符",
        example="编写项目的详细技术文档和用户手册"
    )
    status: TaskStatus = Field(
        default=TaskStatusConst.PENDING,
        description="任务状态：pending/in_progress/completed",
        example="pending"
    )
    priority: TaskPriority = Field(
        default=TaskPriorityConst.MEDIUM,
        description="任务优先级：low/medium/high",
        example="medium"
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="父任务ID，支持任务树结构",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    tags: Optional[List[str]] = Field(
        default=[],
        max_length=10,
        description="任务标签列表，最多10个标签",
        example=["工作", "重要", "紧急"]
    )
    service_ids: Optional[List[str]] = Field(
        default=[],
        max_length=10,
        description="关联服务ID列表，占位字段用于后续AI服务匹配",
        example=["chat", "timer", "points"]
    )
    due_date: Optional[date] = Field(
        default=None,
        description="任务截止日期（date格式：YYYY-MM-DD，不含时间和时区信息。验证时将转换为UTC时区的23:59:59与计划时间比较）",
        example="2024-12-31"
    )
    planned_start_time: Optional[datetime] = Field(
        default=None,
        description="计划开始时间（ISO 8601格式）",
        example="2024-12-20T09:00:00Z"
    )
    planned_end_time: Optional[datetime] = Field(
        default=None,
        description="计划结束时间（ISO 8601格式）",
        example="2024-12-30T18:00:00Z"
    )

    @field_validator('tags')
    @classmethod
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
            # 将date转为datetime进行比较（使用当天结束时间23:59:59 UTC）
            from datetime import datetime, time, timezone

            # 将due_date转为UTC时区的datetime（当天结束时间23:59:59）
            due_datetime = datetime.combine(
                self.due_date,
                time(23, 59, 59),
                tzinfo=timezone.utc
            )

            # 确保planned_end_time有时区信息（如果是naive datetime，假定为UTC）
            planned_end = self.planned_end_time
            if planned_end.tzinfo is None:
                planned_end = planned_end.replace(tzinfo=timezone.utc)

            # 比较两个aware datetime
            if due_datetime < planned_end:
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
                "due_date": "2024-12-25",
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
        description="任务标题，1-100字符",
        example="更新后的任务标题"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="任务描述，最多5000字符",
        example="编写项目的详细技术文档和用户手册"
    )
    status: Optional[TaskStatus] = Field(
        default=None,
        description="任务状态：pending/in_progress/completed",
        example="in_progress"
    )
    priority: Optional[TaskPriority] = Field(
        default=None,
        description="任务优先级：low/medium/high",
        example="high"
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="父任务ID，支持任务树结构",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="任务标签列表，最多10个标签",
        example=["更新", "测试"]
    )
    service_ids: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="关联服务ID列表，占位字段用于后续AI服务匹配",
        example=["chat", "timer"]
    )
    due_date: Optional[date] = Field(
        default=None,
        description="任务截止日期（date格式：YYYY-MM-DD，不含时间和时区信息。验证时将转换为UTC时区的23:59:59与计划时间比较）",
        example="2024-12-25"
    )
    planned_start_time: Optional[datetime] = Field(
        default=None,
        description="计划开始时间（ISO 8601格式）",
        example="2024-12-15T09:00:00Z"
    )
    planned_end_time: Optional[datetime] = Field(
        default=None,
        description="计划结束时间（ISO 8601格式）",
        example="2024-12-20T18:00:00Z"
    )

    @field_validator('tags')
    @classmethod
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

        if self.due_date and self.planned_end_time:
            # 将date转为datetime进行比较（使用当天结束时间23:59:59 UTC）
            from datetime import datetime, time, timezone

            # 将due_date转为UTC时区的datetime（当天结束时间23:59:59）
            due_datetime = datetime.combine(
                self.due_date,
                time(23, 59, 59),
                tzinfo=timezone.utc
            )

            # 确保planned_end_time有时区信息（如果是naive datetime，假定为UTC）
            planned_end = self.planned_end_time
            if planned_end.tzinfo is None:
                planned_end = planned_end.replace(tzinfo=timezone.utc)

            # 比较两个aware datetime
            if due_datetime < planned_end:
                raise ValueError("截止日期不能早于计划结束时间")

        return self


class TaskListQuery(BaseModel):
    """
    任务列表查询Schema - 简化版本

    用于获取任务列表的API查询参数。只支持基本分页和是否包含已删除任务。

    查询参数：
    - page: 页码（从1开始）
    - page_size: 每页大小
    - include_deleted: 是否包含已删除的任务
    - sort_by: 排序字段（固定为created_at）
    - sort_order: 排序方向（固定为desc）
    """
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )

    # 分页参数
    page: int = Field(
        default=1,
        ge=1,
        description="页码，从1开始",
        example=1
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="每页大小，1-100",
        example=20
    )

    # 筛选参数
    include_deleted: bool = Field(
        default=False,
        description="是否包含已删除的任务"
    )
    status: Optional[str] = Field(
        default=None,
        description="任务状态筛选",
        example="pending"
    )
    priority: Optional[str] = Field(
        default=None,
        description="优先级筛选",
        example="high"
    )

    # 排序参数（固定值，简化API）
    sort_by: str = Field(
        default="created_at",
        description="排序字段：固定为created_at"
    )
    sort_order: str = Field(
        default="desc",
        description="排序方向：固定为desc（最新在前）"
    )


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
                "due_date": "2024-12-31",
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
    id: str = Field(..., description="任务ID", example="550e8400-e29b-41d4-a716-446655440000")
    title: str = Field(..., description="任务标题", example="完成项目文档编写")
    description: Optional[str] = Field(None, description="任务描述", example="编写项目的详细技术文档和用户手册")
    status: TaskStatus = Field(..., description="任务状态", example="active")
    priority: Optional[TaskPriority] = Field(None, description="任务优先级", example="medium")
    user_id: Optional[str] = Field(None, description="用户ID", example="550e8400-e29b-41d4-a716-446655440001")
    parent_id: Optional[str] = Field(None, description="父任务ID", example="550e8400-e29b-41d4-a716-446655440001")
    tags: List[str] = Field(default=[], description="任务标签", example=["工作", "重要", "紧急"])
    service_ids: List[str] = Field(default=[], description="关联服务ID列表，占位字段用于后续AI服务匹配", example=["chat", "timer", "points"])
    due_date: Optional[date] = Field(None, description="截止日期（date格式：YYYY-MM-DD）", example="2024-12-31")
    planned_start_time: Optional[datetime] = Field(None, description="计划开始时间", example="2024-01-01T09:00:00Z")
    planned_end_time: Optional[datetime] = Field(None, description="计划结束时间", example="2024-01-01T18:00:00Z")
    last_claimed_date: Optional[date] = Field(None, description="最后领奖日期，用于防刷机制", example="2024-01-15")
    is_deleted: bool = Field(..., description="是否已删除")
    created_at: Optional[datetime] = Field(None, description="创建时间（微服务返回）")
    updated_at: Optional[datetime] = Field(None, description="更新时间（微服务返回）")

    # 简化字段
    completion_percentage: float = Field(..., description="任务完成百分比，0.0-100.0", example=65.5)

    

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

    deleted_task_id: str = Field(..., description="被删除的任务ID")
    deleted_count: int = Field(..., description="删除的任务总数")
    cascade_deleted: bool = Field(..., description="是否有级联删除")


# ===== 统一响应格式 =====

# 删除的Wrapper类：
# - TaskCreateResponse(UnifiedResponse)
# - TaskGetResponse(UnifiedResponse)
# - TaskUpdateResponse(UnifiedResponse)
# - TaskDeleteResponseWrapper(UnifiedResponse)
# - TaskListResponseWrapper(UnifiedResponse)


# ===== 任务完成相关Schema =====

class CompleteTaskRequest(BaseModel):
    """
    完成任务请求Schema

    用于完成任务操作的API请求。支持可选的情绪和难度反馈。

    设计说明：
    - 任务ID从URL路径参数获取
    - 用户ID从JWT token中自动提取
    - mood_feedback为可选字段，用于提供任务完成反馈
    """
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "mood_feedback": {
                    "comment": "任务比较简单，顺利完成",
                    "difficulty": "easy"
                }
            },
            "description": "完成任务请求，可选包含情绪反馈"
        }
    )

    mood_feedback: Optional[Dict[str, str]] = Field(
        default=None,
        description="任务完成反馈，包含评论和难度信息",
        example={
            "comment": "任务比较简单，顺利完成",
            "difficulty": "easy"
        }
    )


class CompleteTaskResponse(BaseModel):
    """
    完成任务响应Schema

    用于返回任务完成操作的详细结果，包含任务信息、奖励信息和父任务更新信息。

    字段说明：
    - task: 完成后的任务信息
    - completion_result: 任务完成操作结果（积分奖励等）
    - lottery_result: 抽奖结果（如果是Top3任务）
    - parent_update: 父任务完成度更新信息
    - message: 操作结果描述
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "task": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "完成项目文档",
                    "status": "completed",
                    "completion_percentage": 100.0
                },
                "completion_result": {
                    "success": True,
                    "points_awarded": 2,
                    "reward_type": "task_complete"
                },
                "lottery_result": {
                    "reward_type": "points",
                    "points": 100,
                    "message": "恭喜获得100积分！"
                },
                "parent_update": {
                    "success": True,
                    "updated_tasks_count": 2,
                    "updated_tasks": [
                        {
                            "task_id": "parent-uuid",
                            "completion_percentage": 75.0,
                            "child_count": 4
                        }
                    ]
                },
                "message": "任务完成成功"
            }
        }
    )

    task: Dict[str, Any] = Field(..., description="完成后的任务信息")
    completion_result: Dict[str, Any] = Field(..., description="任务完成操作结果")
    lottery_result: Optional[Dict[str, Any]] = Field(None, description="抽奖结果（Top3任务）")
    parent_update: Optional[Dict[str, Any]] = Field(None, description="父任务完成度更新信息")
    message: str = Field(..., description="操作结果描述")


class UncompleteTaskRequest(BaseModel):
    """
    取消任务完成请求Schema

    用于取消任务完成状态的API请求。

    设计说明：
    - 任务ID从URL路径参数获取
    - 用户ID从JWT token中自动提取
    - 请求体为空，简化API调用
    - 注意：取消完成不会回收已发放的积分和奖励
    """
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        json_schema_extra={
            "example": {},
            "description": "取消任务完成请求不需要请求体"
        }
    )


class UncompleteTaskResponse(BaseModel):
    """
    取消任务完成响应Schema

    用于返回取消任务完成操作的详细结果。

    字段说明：
    - task: 取消完成后的任务信息
    - parent_update: 父任务完成度更新信息
    - message: 操作结果描述（包含不回收奖励的提示）
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "task": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "完成项目文档",
                    "status": "pending",
                    "completion_percentage": 25.0
                },
                "parent_update": {
                    "success": True,
                    "updated_tasks_count": 2,
                    "updated_tasks": [
                        {
                            "task_id": "parent-uuid",
                            "completion_percentage": 50.0,
                            "child_count": 4
                        }
                    ]
                },
                "message": "取消完成成功（注意：已发放的积分和奖励不会回收）"
            }
        }
    )

    task: Dict[str, Any] = Field(..., description="取消完成后的任务信息")
    parent_update: Optional[Dict[str, Any]] = Field(None, description="父任务完成度更新信息")
    message: str = Field(..., description="操作结果描述")


# ===== 任务完成统一响应格式 =====

# 删除的Wrapper类：
# - TaskCompleteResponseWrapper(UnifiedResponse)
# - TaskUncompleteResponseWrapper(UnifiedResponse)