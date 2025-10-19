# 数据层设计文档

## 设计原则

### 1. TDD 驱动设计
- **测试先行**: 每个功能先写测试，再写实现
- **重构安全**: 充分的测试覆盖保证重构安全性
- **质量保证**: 95%+ 测试覆盖率是硬性要求

### 2. 类型安全优先
- **SQLModel 优势**: 结合 Pydantic 验证和 SQLAlchemy ORM
- **类型注解**: 100% 类型注解覆盖
- **编译时检查**: mypy 静态类型检查

### 3. 领域驱动设计
- **模型映射**: 直接映射业务概念到数据模型
- **关系清晰**: 明确定义模型间关系
- **边界明确**: 每个模型职责单一

---

## SQLModel 模型设计规范

### 基础模型类

```python
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, func

class BaseSQLModel(SQLModel):
    """所有 SQLModel 模型的基类"""

    id: Optional[str] = Field(
        default=None,
        primary_key=True,
        index=True,
        description="主键ID"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, server_default=func.now()),
        description="创建时间"
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now()),
        description="更新时间"
    )

    class Config:
        """Pydantic 配置"""
        validate_assignment = True
        use_enum_values = True
        extra = "forbid"
```

### 模型设计原则

#### 1. 字段定义规范

```python
class ExampleModel(BaseSQLModel, table=True):
    __tablename__ = "example_models"  # 表名显式定义

    # 基础字段类型
    name: str = Field(
        max_length=100,
        index=True,
        description="名称，必填"
    )

    # 可选字段
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="描述，可选"
    )

    # 枚举字段
    status: StatusEnum = Field(
        default=StatusEnum.ACTIVE,
        description="状态"
    )

    # 外键关系
    user_id: str = Field(
        foreign_key="users.id",
        index=True,
        description="用户ID"
    )

    # 数值字段
    priority: int = Field(
        default=0,
        ge=0,
        le=10,
        description="优先级 (0-10)"
    )
```

#### 2. 关系定义规范

```python
from sqlmodel import Relationship, SQLModel
from typing import List, Optional

class User(BaseSQLModel, table=True):
    __tablename__ = "users"

    # 基本字段
    nickname: str = Field(max_length=50, description="昵称")
    email: Optional[str] = Field(default=None, max_length=100, description="邮箱")

    # 一对多关系
    tasks: List["Task"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # 一对一关系
    settings: Optional["UserSettings"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )

class Task(BaseSQLModel, table=True):
    __tablename__ = "tasks"

    title: str = Field(max_length=200, description="任务标题")
    user_id: str = Field(foreign_key="users.id", description="用户ID")
    parent_id: Optional[str] = Field(default=None, foreign_key="tasks.id", description="父任务ID")

    # 反向关系
    user: User = Relationship(back_populates="tasks")

    # 自引用关系
    parent: Optional["Task"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Task.id"}
    )
    children: List["Task"] = Relationship(back_populates="parent")
```

#### 3. 枚举定义规范

```python
from enum import Enum

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DELETED = "deleted"

class PriorityLevel(str, Enum):
    """优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class SessionType(str, Enum):
    """会话类型枚举"""
    FOCUS = "focus"
    BREAK = "break"
    LONG_BREAK = "long_break"
```

---

## 具体模型设计

### 1. 用户系统模型

#### User 模型
```python
class User(BaseSQLModel, table=True):
    __tablename__ = "users"

    # 基本信息
    nickname: str = Field(max_length=50, description="昵称")
    avatar: Optional[str] = Field(default=None, max_length=255, description="头像URL")
    phone: Optional[str] = Field(default=None, max_length=20, unique=True, description="手机号")
    email: Optional[str] = Field(default=None, max_length=100, unique=True, description="邮箱")
    wechat_openid: Optional[str] = Field(default=None, max_length=100, unique=True, description="微信OpenID")
    is_guest: bool = Field(default=False, description="是否游客")
    last_login_at: Optional[datetime] = Field(default=None, description="最后登录时间")

    # 关系
    settings: Optional["UserSettings"] = Relationship(back_populates="user")
    tasks: List["Task"] = Relationship(back_populates="user")
    focus_sessions: List["FocusSession"] = Relationship(back_populates="user")
```

#### UserSettings 模型
```python
class UserSettings(BaseSQLModel, table=True):
    __tablename__ = "user_settings"

    user_id: str = Field(foreign_key="users.id", unique=True, description="用户ID")

    # 专注设置
    focus_duration: int = Field(default=25, ge=1, le=120, description="专注时长(分钟)")
    break_duration: int = Field(default=5, ge=1, le=30, description="休息时长(分钟)")
    long_break_duration: int = Field(default=15, ge=1, le=60, description="长休息时长(分钟)")

    # 自动设置
    auto_start_breaks: bool = Field(default=False, description="自动开始休息")
    auto_start_focus: bool = Field(default=False, description="自动开始专注")

    # 通知设置
    notification_enabled: bool = Field(default=True, description="通知开关")
    sound_enabled: bool = Field(default=True, description="声音开关")

    # 界面设置
    theme: ThemeEnum = Field(default=ThemeEnum.LIGHT, description="主题")
    language: str = Field(default="zh-CN", max_length=10, description="语言")
    timezone: str = Field(default="Asia/Shanghai", max_length=50, description="时区")

    # 关系
    user: User = Relationship(back_populates="settings")
```

### 2. 任务系统模型

#### Task 模型 (支持树结构)
```python
class Task(BaseSQLModel, table=True):
    __tablename__ = "tasks"

    # 基本信息
    user_id: str = Field(foreign_key="users.id", index=True, description="用户ID")
    parent_id: Optional[str] = Field(default=None, foreign_key="tasks.id", index=True, description="父任务ID")
    predecessor_id: Optional[str] = Field(default=None, foreign_key="tasks.id", description="前驱任务ID")

    title: str = Field(max_length=200, description="任务标题")
    description: Optional[str] = Field(default=None, max_length=2000, description="任务详情")

    # 状态和优先级
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    priority: PriorityLevel = Field(default=PriorityLevel.MEDIUM, description="优先级")

    # 时间管理
    due_date: Optional[datetime] = Field(default=None, description="截止日期")
    planned_start_time: Optional[datetime] = Field(default=None, description="计划开始时间")
    planned_end_time: Optional[datetime] = Field(default=None, description="计划结束时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")

    # 番茄钟相关
    estimated_pomodoros: int = Field(default=1, ge=0, description="预计番茄数")
    actual_pomodoros: int = Field(default=0, ge=0, description="实际番茄数")

    # 树结构计算字段
    completion_percentage: int = Field(default=0, ge=0, le=100, description="完成百分比")
    level: int = Field(default=0, ge=0, description="任务层级")
    path: str = Field(default="", max_length=1000, description="任务路径")

    # 关系
    user: User = Relationship(back_populates="tasks")
    parent: Optional["Task"] = Relationship(back_populates="children", sa_relationship_kwargs={"remote_side": "Task.id"})
    children: List["Task"] = Relationship(back_populates="parent")
    focus_sessions: List["FocusSession"] = Relationship(back_populates="task")
    top3_records: List["TaskTop3"] = Relationship(back_populates="task")
```

#### TaskTop3 模型
```python
class TaskTop3(BaseSQLModel, table=True):
    __tablename__ = "task_top3"

    user_id: str = Field(foreign_key="users.id", index=True, description="用户ID")
    task_id: str = Field(foreign_key="tasks.id", description="任务ID")
    date: datetime = Field(index=True, description="日期(YYYY-MM-DD)")
    position: int = Field(ge=1, le=3, description="位置(1-3)")

    # 关系
    user: User = Relationship(back_populates="top3_tasks")
    task: Task = Relationship(back_populates="top3_records")

    # 复合唯一约束
    __table_args__ = (
        {"schema": None},
    )
```

### 3. 专注系统模型

#### FocusSession 模型
```python
class FocusSession(BaseSQLModel, table=True):
    __tablename__ = "focus_sessions"

    user_id: str = Field(foreign_key="users.id", index=True, description="用户ID")
    task_id: Optional[str] = Field(default=None, foreign_key="tasks.id", index=True, description="关联任务ID")

    session_type: SessionType = Field(default=SessionType.FOCUS, description="会话类型")

    # 时间管理
    planned_duration: int = Field(ge=1, le=180, description="计划时长(分钟)")
    actual_duration: int = Field(default=0, ge=0, description="实际时长(分钟)")
    start_time: datetime = Field(description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")

    # 状态和进度
    status: SessionStatus = Field(default=SessionStatus.PENDING, description="会话状态")
    pause_duration: int = Field(default=0, ge=0, description="暂停总时长(秒)")
    interruptions_count: int = Field(default=0, ge=0, description="干扰次数")

    # 用户反馈
    notes: Optional[str] = Field(default=None, max_length=500, description="备注")
    satisfaction: Optional[SatisfactionLevel] = Field(default=None, description="满意度")

    # 关系
    user: User = Relationship(back_populates="focus_sessions")
    task: Optional[Task] = Relationship(back_populates="focus_sessions")
```

### 4. 奖励系统模型

#### Reward 模型
```python
class Reward(BaseSQLModel, table=True):
    __tablename__ = "rewards"

    name: str = Field(max_length=100, description="奖励名称")
    description: str = Field(max_length=500, description="奖励描述")
    icon: str = Field(max_length=255, description="图标URL")

    # 价值信息
    points_value: Optional[int] = Field(default=None, ge=0, description="积分价值")
    amount_to_collect: Optional[int] = Field(default=None, ge=1, description="所需碎片数")

    # 分类和状态
    category: RewardCategory = Field(description="奖励分类")
    is_active: bool = Field(default=True, description="是否激活")
    is_limited: bool = Field(default=False, description="是否限量")
    total_quantity: Optional[int] = Field(default=None, ge=0, description="总数量")

    # 关系
    user_fragments: List["UserFragment"] = Relationship(back_populates="reward")
```

#### UserFragment 模型
```python
class UserFragment(BaseSQLModel, table=True):
    __tablename__ = "user_fragments"

    user_id: str = Field(foreign_key="users.id", index=True, description="用户ID")
    reward_id: str = Field(foreign_key="rewards.id", description="奖励ID")
    obtained_at: datetime = Field(description="获得时间")
    source: FragmentSource = Field(description="获得来源")

    # 关系
    user: User = Relationship(back_populates="fragments")
    reward: Reward = Relationship(back_populates="user_fragments")
```

#### LotteryRecord 模型
```python
class LotteryRecord(BaseSQLModel, table=True):
    __tablename__ = "lottery_records"

    user_id: str = Field(foreign_key="users.id", index=True, description="用户ID")
    task_id: str = Field(foreign_key="tasks.id", description="关联任务ID")

    reward_type: LotteryRewardType = Field(description="奖励类型")
    points_amount: Optional[int] = Field(default=None, ge=0, description="获得积分数")
    fragment_id: Optional[str] = Field(default=None, foreign_key="user_fragments.id", description="获得碎片ID")
    fragment_name: Optional[str] = Field(default=None, max_length=100, description="碎片名称")

    # 心情反馈
    mood: MoodLevel = Field(description="心情")
    mood_comment: Optional[str] = Field(default=None, max_length=200, description="心情评论")
    difficulty: DifficultyLevel = Field(description="难度感受")

    # 关系
    user: User = Relationship(back_populates="lottery_records")
    task: Task = Relationship(back_populates="lottery_records")
```

### 5. 聊天系统模型

#### ChatSession 模型
```python
class ChatSession(BaseSQLModel, table=True):
    __tablename__ = "chat_sessions"

    user_id: str = Field(foreign_key="users.id", index=True, description="用户ID")
    title: str = Field(max_length=200, description="会话标题")

    # 会话状态
    is_active: bool = Field(default=True, description="是否活跃")
    message_count: int = Field(default=0, ge=0, description="消息数量")
    last_message_at: Optional[datetime] = Field(default=None, description="最后消息时间")

    # 关系
    user: User = Relationship(back_populates="chat_sessions")
    messages: List["ChatMessage"] = Relationship(back_populates="session", cascade="all, delete-orphan")
```

#### ChatMessage 模型
```python
class ChatMessage(BaseSQLModel, table=True):
    __tablename__ = "chat_messages"

    session_id: str = Field(foreign_key="chat_sessions.id", index=True, description="会话ID")

    sender: MessageSender = Field(description="发送者")
    message_type: MessageType = Field(description="消息类型")
    content: str = Field(description="消息内容")

    # 多媒体支持
    file_url: Optional[str] = Field(default=None, max_length=500, description="文件URL")
    metadata: Optional[str] = Field(default=None, max_length=1000, description="元数据JSON")

    # 消息顺序
    sequence_number: int = Field(ge=0, description="序号")

    # 关系
    session: ChatSession = Relationship(back_populates="messages")
```

---

## 数据库约束设计

### 1. 主键约束
- 所有表使用 UUID 字符串作为主键
- 主键命名为 `id`
- 自动生成唯一值

### 2. 外键约束
- 外键命名格式: `{related_table}_id`
- 设置适当的级联操作
- 建立索引提升查询性能

### 3. 唯一约束
```python
# 用户唯一标识
phone: Optional[str] = Field(default=None, unique=True, description="手机号")
email: Optional[str] = Field(default=None, unique=True, description="邮箱")
wechat_openid: Optional[str] = Field(default=None, unique=True, description="微信OpenID")

# 用户设置唯一性
user_id: str = Field(foreign_key="users.id", unique=True, description="用户ID")

# Top3 任务唯一性 (用户+日期+位置)
# 通过 SQLAlchemy 的 UniqueConstraint 实现
```

### 4. 检查约束
```python
# 数值范围约束
priority: int = Field(ge=0, le=10, description="优先级 (0-10)")
focus_duration: int = Field(default=25, ge=1, le=120, description="专注时长(分钟)")

# 枚举值约束
status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
```

### 5. 索引策略
```python
# 查询频繁的字段建立索引
user_id: str = Field(foreign_key="users.id", index=True, description="用户ID")
created_at: datetime = Field(index=True, description="创建时间")

# 复合索引
# (user_id, status) - 查询用户任务状态
# (user_id, created_at) - 查询用户历史记录
# (task_id, start_time) - 查询任务专注记录
```

---

## 数据验证规则

### 1. Pydantic 验证器

```python
from pydantic import validator

class Task(BaseSQLModel, table=True):
    # ... 字段定义

    @validator('planned_end_time')
    def validate_end_time(cls, v, values):
        """验证结束时间必须晚于开始时间"""
        if v and 'planned_start_time' in values and values['planned_start_time']:
            if v <= values['planned_start_time']:
                raise ValueError('结束时间必须晚于开始时间')
        return v

    @validator('estimated_pomodoros')
    def validate_pomodoros(cls, v):
        """验证番茄数合理性"""
        if v < 0:
            raise ValueError('番茄数不能为负数')
        if v > 100:  # 假设最多100个番茄
            raise ValueError('番茄数不能超过100')
        return v
```

### 2. 自定义验证方法

```python
class Task(BaseSQLModel, table=True):
    # ... 字段定义

    def can_be_completed(self) -> bool:
        """检查任务是否可以完成"""
        return self.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]

    def is_overdue(self) -> bool:
        """检查任务是否过期"""
        if self.due_date and self.status != TaskStatus.COMPLETED:
            return datetime.utcnow() > self.due_date
        return False

    def calculate_completion_percentage(self, subtasks: List['Task']) -> int:
        """根据子任务计算完成百分比"""
        if not subtasks:
            return 100 if self.status == TaskStatus.COMPLETED else 0

        completed_count = sum(1 for task in subtasks if task.status == TaskStatus.COMPLETED)
        return int((completed_count / len(subtasks)) * 100)
```

---

## 性能优化设计

### 1. 查询优化

```python
# 预加载关联数据
def get_user_with_tasks(user_id: str) -> Optional[User]:
    """获取用户及其任务（预加载）"""
    with Session(engine) as session:
        statement = select(User).where(User.id == user_id).options(
            selectinload(User.tasks),
            selectinload(User.settings)
        )
        return session.exec(statement).first()

# 批量操作优化
def create_tasks_batch(task_data_list: List[dict]) -> List[Task]:
    """批量创建任务"""
    with Session(engine) as session:
        tasks = [Task(**data) for data in task_data_list]
        session.add_all(tasks)
        session.commit()
        for task in tasks:
            session.refresh(task)
        return tasks
```

### 2. 分页查询

```python
from typing import Tuple

class PaginationResult:
    def __init__(self, items: List, total: int, page: int, page_size: int):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = (total + page_size - 1) // page_size

def get_paginated_tasks(
    user_id: str,
    page: int = 1,
    page_size: int = 20
) -> PaginationResult:
    """分页获取用户任务"""
    with Session(engine) as session:
        offset = (page - 1) * page_size

        # 查询总数
        count_statement = select(func.count(Task.id)).where(Task.user_id == user_id)
        total = session.exec(count_statement).one()

        # 查询数据
        statement = (
            select(Task)
            .where(Task.user_id == user_id)
            .offset(offset)
            .limit(page_size)
            .order_by(Task.created_at.desc())
        )
        tasks = session.exec(statement).all()

        return PaginationResult(tasks, total, page, page_size)
```

---

## 测试设计原则

### 1. 模型测试覆盖

```python
import pytest
from sqlmodel import Session
from datetime import datetime

class TestTaskModel:
    """任务模型测试"""

    def test_task_creation(self, session: Session):
        """测试任务创建"""
        task = Task(
            title="测试任务",
            user_id="user123",
            description="这是一个测试任务"
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        assert task.id is not None
        assert task.title == "测试任务"
        assert task.status == TaskStatus.PENDING
        assert task.created_at is not None

    def test_task_validation(self):
        """测试任务验证"""
        # 测试必填字段
        with pytest.raises(ValueError):
            Task(user_id="user123")  # 缺少 title

        # 测试字段长度限制
        with pytest.raises(ValueError):
            Task(
                title="a" * 201,  # 超过200字符限制
                user_id="user123"
            )

    def test_task_tree_relationship(self, session: Session):
        """测试任务树形关系"""
        parent_task = Task(title="父任务", user_id="user123")
        child_task = Task(title="子任务", user_id="user123", parent_id=parent_task.id)

        session.add(parent_task)
        session.add(child_task)
        session.commit()

        # 测试关系查询
        assert len(parent_task.children) == 1
        assert child_task.parent == parent_task
```

### 2. 数据库约束测试

```python
class TestDatabaseConstraints:
    """数据库约束测试"""

    def test_unique_email_constraint(self, session: Session):
        """测试邮箱唯一约束"""
        user1 = User(nickname="用户1", email="test@example.com")
        user2 = User(nickname="用户2", email="test@example.com")

        session.add(user1)
        session.commit()

        # 第二个用户应该违反唯一约束
        session.add(user2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_foreign_key_constraint(self, session: Session):
        """测试外键约束"""
        # 创建任务时引用不存在的用户ID
        task = Task(title="任务", user_id="nonexistent_user")

        session.add(task)
        with pytest.raises(IntegrityError):
            session.commit()
```

---

这个设计文档为数据层实现提供了详细的技术规范和最佳实践指导，确保代码质量和可维护性。