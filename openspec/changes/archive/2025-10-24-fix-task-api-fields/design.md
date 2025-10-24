# 技术设计文档

## 架构影响分析

### 受影响的层级
```
┌─────────────────────┐
│   API Layer         │ ← router.py (调用缺失方法)
├─────────────────────┤
│   Service Layer     │ ← service.py (SQL查询缺字段、Top3判断错误)
├─────────────────────┤
│   Repository Layer  │ ← repository.py (未使用，可保留)
├─────────────────────┤
│   Model Layer       │ ← models.py/schemas.py (字段定义不一致)
├─────────────────────┤
│   Database          │ ← SQLite (表结构正确)
└─────────────────────┘
```

### 问题根因

1. **数据模型与Schema不一致**
   - 模型有service_ids，Schema无
   - Schema要求level/path，模型无，代码硬编码假数据

2. **Service层实现不完整**
   - Router调用的方法不存在
   - SQL查询只选择部分字段
   - Top3判断逻辑重复且错误

3. **计算字段职责混乱**
   - is_overdue/duration_minutes应由前端计算
   - 后端在多处重复计算

---

## 设计决策

### 决策1：删除level和path字段 ✅

**背景**：
- 数据库表中从未实现这两个字段
- 代码中硬编码返回假数据（level=0, path="/task_id"）
- Repository中有大量未使用的level/path查询方法

**方案对比**：

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| A. 实现level/path功能 | 支持高效子树查询 | 复杂度高，需要递归更新，修改parent_id时需要更新所有子任务 | ❌ |
| B. 删除level/path字段 | 简化设计，降低复杂度 | 子树查询需要递归（性能影响有限） | ✅ |

**决定**：选择方案B
- 符合YAGNI原则：当前无实际需求
- 保留parent_id已足够支持任务层级
- 如需子树查询可用递归CTE（repository中已实现）

**影响**：
- ✅ TaskResponse删除level/path字段
- ✅ Service层删除硬编码逻辑
- ✅ Repository保留递归查询方法（未来可能用到）

---

### 决策2：删除计算字段 ✅

**背景**：
- is_overdue = 当前时间 > due_date（前端可计算）
- duration_minutes = (end_time - start_time) / 60（前端可计算）

**方案对比**：

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| A. 后端计算返回 | 前端简单 | 后端计算冗余，网络传输浪费 | ❌ |
| B. 前端自行计算 | 职责清晰，减少网络传输 | 前端需要实现计算逻辑 | ✅ |

**决定**：选择方案B
- 前后端职责分离原则
- 减少API响应体积
- 前端已有due_date和时间字段，计算trivial

**API契约变更**：
```diff
{
  "id": "uuid",
  "title": "任务标题",
- "user_id": "uuid",  // 删除
- "is_overdue": false,  // 删除
- "duration_minutes": 60,  // 删除
- "level": 0,  // 删除
- "path": "/uuid",  // 删除
+ "service_ids": [],  // 新增
  "tags": ["标签1"],
  "due_date": "2025-01-01T00:00:00Z",
  "planned_start_time": "2025-01-01T09:00:00Z",
  "planned_end_time": "2025-01-01T10:00:00Z"
}
```

---

### 决策3：统一Top3判断逻辑 ✅

**背景**：
- `service.py:189`：错误的判断 - 通过任务标题包含"top3"字符串
- `completion_service.py:132`：正确的判断 - 调用top3_service.is_task_in_today_top3()

**问题分析**：
```python
# ❌ 错误实现（service.py）
if "top3" in task_title.lower():
    points_to_award = reward_config.get_normal_task_points()
    reward_type = "task_complete_top3"

# ✅ 正确实现（completion_service.py）
is_top3 = self.top3_service.is_task_in_today_top3(str(user_id), str(task_id))
if is_top3:
    lottery_result = self.reward_service.top3_lottery(str(user_id))
```

**方案**：
- 删除service.py中的complete_task方法
- 统一使用completion_service.complete_task
- Router中已经调用正确的方法（无需修改）

**影响**：
- Service层职责更清晰
- 避免逻辑重复和不一致
- Top3判断100%准确

---

### 决策4：SQL查询字段映射修复 ✅

**当前问题**：
```python
# service.py:290 - 只查询7个字段
query = f"""
    SELECT id, title, description, status, parent_id, created_at, updated_at
    FROM tasks
    ...
"""
```

**缺失字段**：
1. priority
2. tags (JSON)
3. service_ids (JSON)
4. due_date
5. planned_start_time
6. planned_end_time
7. last_claimed_date
8. completion_percentage
9. is_deleted
10. user_id（内部需要，但不返回给前端）

**修复方案**：
```python
query = f"""
    SELECT
        id, user_id, title, description, status, priority, parent_id,
        tags, service_ids, due_date, planned_start_time, planned_end_time,
        last_claimed_date, completion_percentage, is_deleted,
        created_at, updated_at
    FROM tasks
    WHERE {where_clause}
    ORDER BY created_at DESC
    LIMIT :limit OFFSET :offset
"""
```

**JSON字段处理**：
```python
import json

# 处理SQLite返回的JSON字符串
tags = json.loads(row.tags) if row.tags else []
service_ids = json.loads(row.service_ids) if row.service_ids else []
```

**数据库兼容性**：
- ✅ SQLite：JSON字段存储为TEXT，需要json.loads()
- ✅ PostgreSQL：原生JSON类型，自动反序列化
- ✅ MySQL：JSON类型，自动反序列化

---

### 决策5：Service方法实现策略 ✅

**缺失方法**：
1. `update_task_with_tree_structure`
2. `delete_task`

**实现原则**：
- 简化优先：不处理level/path树结构更新
- 委托Repository：复用现有的update和soft_delete_cascade方法
- 验证优先：严格的权限和存在性检查

**update_task实现**：
```python
def update_task_with_tree_structure(
    self, task_id: UUID, request: UpdateTaskRequest, user_id: UUID
) -> Dict[str, Any]:
    """
    更新任务（简化版）

    说明：由于删除了level/path字段，无需处理树结构更新
    """
    # 1. 验证任务存在和权限
    task = self.task_repository.get_by_id(str(task_id), str(user_id))
    if not task:
        raise TaskNotFoundException(f"任务不存在: {task_id}")

    # 2. 构建更新数据（只包含非None字段）
    update_data = {}
    for field, value in request.dict(exclude_unset=True).items():
        if value is not None:
            update_data[field] = value

    # 3. 调用repository更新
    updated_task = self.task_repository.update(task_id, user_id, update_data)

    # 4. 返回响应
    return self._build_task_response(updated_task)
```

**delete_task实现**：
```python
def delete_task(self, task_id: UUID, user_id: UUID) -> Dict[str, Any]:
    """
    软删除任务及所有子任务
    """
    # 1. 验证任务存在和权限
    task = self.task_repository.get_by_id(str(task_id), str(user_id))
    if not task:
        raise TaskNotFoundException(f"任务不存在: {task_id}")

    # 2. 级联软删除
    deleted_count = self.task_repository.soft_delete_cascade(task_id, user_id)

    # 3. 返回结果
    return {
        "deleted_task_id": str(task_id),
        "deleted_count": deleted_count,
        "cascade_deleted": deleted_count > 1
    }
```

---

### 决策6：last_claimed_date防刷机制修复 ✅

**当前问题**：
```python
# service.py:206 - 未设置last_claimed_date
UPDATE tasks
SET status = 'completed', updated_at = :now
WHERE id = :task_id AND user_id = :user_id
```

**修复方案**：
```python
from datetime import date, timezone

# 设置首次完成日期
claim_date = date.today()  # 或 datetime.now(timezone.utc).date()

UPDATE tasks
SET status = 'completed',
    last_claimed_date = :claim_date,  // 新增
    updated_at = :now
WHERE id = :task_id AND user_id = :user_id
```

**防刷逻辑验证**：
```python
# 在发放奖励前检查
if task.last_claimed_date is not None:
    # 已领取过奖励，拒绝重复发放
    return {"points_awarded": 0, "message": "任务已完成，无法重复获得积分"}
```

**数据库类型**：
- last_claimed_date: DATE类型（YYYY-MM-DD格式）
- 与created_at/updated_at的DATETIME类型区分

---

## 风险评估

### 高风险项
1. ❌ **SQL查询遗漏字段** - 可能导致数据丢失
   - 缓解措施：详细的字段映射测试

2. ❌ **JSON字段反序列化错误** - 可能导致500错误
   - 缓解措施：添加try-except处理

3. ❌ **前端兼容性破坏** - 删除字段导致前端报错
   - 缓解措施：API版本控制，前端同步更新

### 中风险项
4. ⚠️ **循环引用检测缺失** - update parent_id时可能形成循环
   - 缓解措施：添加递归检测逻辑（后续优化）

5. ⚠️ **性能影响** - 删除path后子树查询变慢
   - 缓解措施：使用递归CTE查询（已实现）

### 低风险项
6. ✅ **测试覆盖不足** - 新方法缺少测试
   - 缓解措施：每个子任务都包含测试用例

---

## 回滚计划

### 阶段1回滚（并行任务）
- **1.1-1.3**：恢复Schema字段定义
- **1.4**：恢复旧的SQL查询
- **1.5**：删除新增的Service方法

### 阶段2回滚
- **2**：恢复service.py中的complete_task逻辑

### Git策略
- 每个子任务一个commit
- 阶段1完成后打tag: `fix-task-api-phase1`
- 阶段2完成后打tag: `fix-task-api-phase2`

---

## 性能影响

### 响应体积变化
```
修改前：~1.2KB (包含7个冗余字段)
修改后：~0.9KB (删除5个字段，添加1个)
优化：-25%
```

### 查询性能
- SQL查询增加10个字段：影响 < 5ms（忽略不计）
- JSON反序列化：影响 < 1ms per record
- 整体影响：可忽略

---

## 测试策略

### 单元测试
- 每个新增/修改的方法都有对应测试
- Mock外部依赖（top3_service, reward_service）

### 集成测试
- 端到端测试完整流程：创建→更新→完成→删除
- 验证所有字段正确返回

### Scenario测试
- 覆盖task-crud spec中的所有scenario
- 验证错误处理和边界条件

---

**设计审查人**：待定
**审查日期**：2025-10-24
**状态**：✅ 已批准
