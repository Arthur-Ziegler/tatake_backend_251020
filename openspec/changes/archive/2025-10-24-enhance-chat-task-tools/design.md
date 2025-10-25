# 设计文档：聊天任务管理工具

## 架构设计

### 工具层次结构
```
用户自然语言
    ↓
LangGraph Agent
    ↓
Task Tools (7个独立工具)
    ↓
工具辅助层 (utils.py)
    ├── get_task_service_context() - Session管理
    ├── safe_uuid_convert() - UUID转换
    └── parse_datetime() - 日期解析
    ↓
TaskService (复用现有业务逻辑)
    ↓
TaskRepository
    ↓
SQLite数据库
```

### 核心技术方案

#### 1. 全局数据库管理器（Session获取）

**问题**：LangGraph工具无法使用FastAPI的Depends机制

**解决方案**：创建工具专用的Session管理器

```python
# src/domains/chat/tools/utils.py
from contextlib import contextmanager
from src.database import get_engine
from sqlmodel import Session
from src.domains.task.service import TaskService
from src.domains.points.service import PointsService

@contextmanager
def get_task_service_context():
    """
    为工具提供TaskService实例（带Session管理）

    使用上下文管理器确保Session正确关闭
    """
    engine = get_engine()
    session = Session(engine)
    try:
        points_service = PointsService(session)
        task_service = TaskService(session, points_service)
        yield task_service
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**使用示例**：
```python
@tool
def create_task(...):
    with get_task_service_context() as task_service:
        result = task_service.create_task(...)
        return json.dumps({"success": True, "data": result})
```

---

#### 2. 权限传递方案（InjectedState）

**使用LangGraph InjectedState机制自动注入user_id**

```python
from typing import Annotated
from langgraph.prebuilt import InjectedState

@tool
def create_task(
    title: str,
    state: Annotated[dict, InjectedState]  # 自动注入
) -> str:
    user_id = state.get("user_id")  # 从State获取
    if not user_id:
        return json.dumps({"success": False, "error": "用户未认证"})
    # 继续处理...
```

**State传递流程**：
```
API层 (JWT → user_id)
  → Service层 (config={"configurable": {"user_id": "..."}})
  → LangGraph (State自动传递)
  → 工具 (InjectedState自动注入)
```

---

#### 3. UUID转换与错误处理

**问题**：LLM传递字符串，TaskService期望UUID对象

**解决方案**：工具层统一转换并捕获错误

```python
# utils.py
from uuid import UUID
from typing import Optional

def safe_uuid_convert(uuid_str: Optional[str]) -> Optional[UUID]:
    """
    安全转换UUID字符串

    Args:
        uuid_str: UUID字符串或None

    Returns:
        UUID对象或None

    Raises:
        ValueError: UUID格式错误时
    """
    if not uuid_str:
        return None
    try:
        return UUID(uuid_str)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"无效的任务ID格式：{uuid_str}")

# 工具中使用
@tool
def create_task(title: str, parent_id: str = None, ...):
    try:
        parent_uuid = safe_uuid_convert(parent_id)
        user_uuid = safe_uuid_convert(user_id)
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)})
```

---

#### 4. DateTime字段解析

**问题**：CreateTaskRequest需要datetime对象，LLM传递ISO字符串

**解决方案**：工具层手动解析，提供友好错误

```python
# utils.py
from datetime import datetime
from typing import Optional

def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """
    解析ISO格式日期时间字符串

    支持格式：
    - 2024-12-31T23:59:59Z
    - 2024-12-31T23:59:59+08:00
    - 2024-12-31T23:59:59

    Args:
        dt_str: ISO格式日期时间字符串

    Returns:
        datetime对象或None

    Raises:
        ValueError: 日期格式错误
    """
    if not dt_str:
        return None
    try:
        # 处理Z时区标记
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        return datetime.fromisoformat(dt_str)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"日期格式错误：{dt_str}，请使用ISO格式（如：2024-12-31T23:59:59Z）")

# 工具中使用
@tool
def create_task(
    title: str,
    due_date: str = None,
    planned_start_time: str = None,
    planned_end_time: str = None,
    ...
):
    try:
        due_date_dt = parse_datetime(due_date)
        start_dt = parse_datetime(planned_start_time)
        end_dt = parse_datetime(planned_end_time)
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)})
```

---

#### 5. 批量创建事务策略

**决策**：接受"部分成功"（不修改TaskService）

**理由**：
- TaskService.create_task()每次自动commit
- 修改Service超出提案范围
- 部分成功对用户更友好（能看到哪些成功哪些失败）

**实现方案**：
```python
@tool
def batch_create_subtasks(
    parent_id: str,
    subtasks: List[Dict[str, str]],
    state: Annotated[dict, InjectedState]
) -> str:
    """
    批量创建子任务（支持部分成功）

    Args:
        parent_id: 父任务ID
        subtasks: 子任务列表 [{"title": "...", "description": "..."}]

    Returns:
        JSON格式：{"success": bool, "created": [...], "failed": [...]}
    """
    user_id = state.get("user_id")

    try:
        user_uuid = safe_uuid_convert(user_id)
        parent_uuid = safe_uuid_convert(parent_id)
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)})

    created_tasks = []
    failed_tasks = []

    with get_task_service_context() as task_service:
        # 先验证父任务存在
        try:
            parent_task = task_service.get_task(parent_uuid, user_uuid)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"父任务不存在或无权访问：{str(e)}"
            })

        # 逐个创建子任务
        for subtask in subtasks:
            try:
                request = CreateTaskRequest(
                    title=subtask.get("title", "未命名任务"),
                    description=subtask.get("description", ""),
                    parent_id=parent_id
                )
                result = task_service.create_task(request, user_uuid)
                created_tasks.append(result)
            except Exception as e:
                failed_tasks.append({
                    "title": subtask.get("title", "未命名任务"),
                    "error": str(e)
                })

    return json.dumps({
        "success": len(failed_tasks) == 0,
        "created": created_tasks,
        "failed": failed_tasks,
        "message": f"成功创建{len(created_tasks)}个子任务，{len(failed_tasks)}个失败"
    })
```

---

#### 6. 搜索工具设计（方案D）

**返回最小化字段+时间信息**

```python
@tool
def search_tasks(
    query: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """
    搜索任务（返回所有任务供LLM分析）

    MVP方案：返回所有任务（最多100个）的简化信息，
    让LLM自行分析匹配用户查询。

    后续优化：升级为向量搜索
    """
    user_id = state.get("user_id")

    try:
        user_uuid = safe_uuid_convert(user_id)
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)})

    with get_task_service_context() as task_service:
        # 获取所有任务（最多100个）
        all_tasks = task_service.list_tasks(
            user_id=user_uuid,
            limit=100,
            include_deleted=False
        )

        # 简化任务信息
        simplified_tasks = [
            {
                "id": str(task["id"]),
                "title": task["title"],
                "status": task["status"],
                "priority": task.get("priority"),
                "created_at": task["created_at"].isoformat() if task.get("created_at") else None,
                "updated_at": task["updated_at"].isoformat() if task.get("updated_at") else None,
                "due_date": task["due_date"].isoformat() if task.get("due_date") else None,
            }
            for task in all_tasks
        ]

        return json.dumps({
            "success": True,
            "tasks": simplified_tasks,
            "total": len(simplified_tasks),
            "note": f"请从上述任务中找出与'{query}'相关的任务"
        })
```

**Token成本估算**：
- 100任务 × 80 tokens/任务 = 8000 tokens
- 可接受的MVP成本

---

## 工具规范

### 统一返回格式
```json
{
  "success": true/false,
  "data": {...},           // 成功时的数据
  "error": "错误信息",      // 失败时的错误
  "message": "友好提示"     // 可选，供LLM解释给用户
}
```

### 完整工具清单与参数

#### 1. create_task
```python
@tool
def create_task(
    title: str,                          # 必填
    description: str = "",               # 可选
    parent_id: str = None,               # 可选，UUID字符串
    priority: str = "medium",            # 可选，low/medium/high
    tags: List[str] = None,              # 可选
    due_date: str = None,                # 可选，ISO格式
    planned_start_time: str = None,      # 可选，ISO格式
    planned_end_time: str = None,        # 可选，ISO格式
    state: Annotated[dict, InjectedState] = None
) -> str:
    """创建任务（支持全字段）"""
```

#### 2. update_task
```python
@tool
def update_task(
    task_id: str,                        # 必填
    title: str = None,                   # 可选
    description: str = None,             # 可选
    status: str = None,                  # 可选，pending/in_progress/completed
    priority: str = None,                # 可选
    tags: List[str] = None,              # 可选
    due_date: str = None,                # 可选，ISO格式
    state: Annotated[dict, InjectedState] = None
) -> str:
    """更新任务"""
```

#### 3. delete_task
```python
@tool
def delete_task(
    task_id: str,                        # 必填
    state: Annotated[dict, InjectedState] = None
) -> str:
    """删除任务（软删除）"""
```

#### 4. query_tasks
```python
@tool
def query_tasks(
    status: str = None,                  # 可选，pending/in_progress/completed
    parent_id: str = None,               # 可选，查询子任务
    limit: int = 20,                     # 可选，默认20
    offset: int = 0,                     # 可选，默认0
    state: Annotated[dict, InjectedState] = None
) -> str:
    """条件查询任务列表"""
```

#### 5. get_task_detail
```python
@tool
def get_task_detail(
    task_id: str,                        # 必填
    state: Annotated[dict, InjectedState] = None
) -> str:
    """获取任务详情（含子任务）"""
```

#### 6. search_tasks
```python
@tool
def search_tasks(
    query: str,                          # 必填
    limit: int = 100,                    # 可选，默认100
    state: Annotated[dict, InjectedState] = None
) -> str:
    """搜索任务（LLM分析模式）"""
```

#### 7. batch_create_subtasks
```python
@tool
def batch_create_subtasks(
    parent_id: str,                      # 必填
    subtasks: List[Dict[str, str]],      # 必填，[{"title": "...", "description": "..."}]
    state: Annotated[dict, InjectedState] = None
) -> str:
    """批量创建子任务（支持部分成功）"""
```

---

## 测试策略

### 工具单元测试
- Mock TaskService和InjectedState
- 测试UUID转换错误处理
- 测试datetime解析错误处理
- 测试每个工具的成功和失败场景
- 验证返回JSON格式正确性

### 集成测试
- 使用真实数据库（测试环境）
- 测试工具调用TaskService的完整流程
- 测试多用户隔离（UserA不能操作UserB的任务）
- 测试任务树创建（父任务 + 子任务）
- 测试批量创建的部分成功场景

### 对话场景测试（E2E）
- 场景1：创建任务对话
- 场景2：任务拆分对话（多轮确认）
- 场景3：任务搜索对话
- 场景4：批量创建部分失败的用户交互

---

## 性能考虑

### 当前方案（MVP）
- 实时数据库查询，无缓存
- 搜索工具返回最多100个任务
- 单次对话token消耗：
  - 普通CRUD：500-1000 tokens
  - 搜索操作：8000-12000 tokens（取决于任务数）

### 未来优化方向
1. **向量搜索**：预计算任务embedding，实现真正的语义搜索
2. **任务缓存**：Redis缓存热门任务列表
3. **智能分页**：搜索时只返回最相关的任务（不是全部）
4. **批量操作优化**：修改TaskService支持真正的事务批量创建

---

## 实施步骤概览

1. **Phase 1**：工具基础设施（utils.py，Session管理）
2. **Phase 2**：实现7个工具（并行开发）
3. **Phase 3**：LangGraph集成（绑定工具）
4. **Phase 4**：测试（单元、集成、E2E）
5. **Phase 5**：文档和部署

**预估工作量**：10-12小时（1-2天）
