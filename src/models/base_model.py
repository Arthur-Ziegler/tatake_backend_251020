"""
基础 SQLModel 类
提供所有模型的通用字段和行为
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class BaseSQLModel(SQLModel):
    """基础SQLModel类

    为所有数据模型提供通用字段：
    - id: 主键，自动生成的UUID字符串
    - created_at: 创建时间戳
    - updated_at: 更新时间戳
    """

    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        description="主键ID，自动生成的UUID字符串"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="创建时间"
    )

    updated_at: datetime = Field(
        default=None,
        description="更新时间"
    )

    def model_post_init(self, __context: any) -> None:
        """模型初始化后调用，确保updated_at与created_at相同"""
        if self.updated_at is None:
            self.updated_at = self.created_at

    def __repr__(self) -> str:
        """返回模型的字符串表示"""
        class_name = self.__class__.__name__
        return f"{class_name}(id={self.id})"