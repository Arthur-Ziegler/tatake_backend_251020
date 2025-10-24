# 任务清单

## 并行执行策略

```
阶段1（可并行）⚡：
  ├─ 1.1 删除level和path字段
  ├─ 1.2 删除计算字段
  ├─ 1.3 修复Response Schema
  ├─ 1.4 修复SQL查询
  └─ 1.5 实现Service方法

阶段2（依赖1.4）🔗：
  └─ 2 修复任务完成逻辑
```

---

## 【1.1】删除level和path字段（可并行）⚡

### 修改范围
本任务需要**彻底删除**项目中所有level和path相关代码，确保没有任何残留。

### 子任务

#### A. Schema层修改
- [ ] 1.1.1 删除`src/domains/task/schemas.py:374-375`的level和path字段定义：
  ```python
  # 删除这两行
  level: int = Field(..., description="任务层级深度，0表示根任务")
  path: str = Field(..., description="任务路径，格式为'/uuid1/uuid2/uuid3'")
  ```

#### B. Service层修改
- [ ] 1.1.2 删除`src/domains/task/service.py:325-326`的硬编码（get_tasks方法）
- [ ] 1.1.3 删除`src/domains/task/service.py:533-534`的硬编码（create_task方法）
- [ ] 1.1.4 删除`src/domains/task/service.py:627-638`的计算逻辑（_build_task_response方法）：
  ```python
  # 删除整个level/path计算块
  if task.parent_id is None:
      level = 0
      path = f"/{task.id}"
  else:
      level = 1
      path = f"/{task.parent_id}/{task.id}"

  task_dict.update({
      "level": level,  # 删除
      "path": path,    # 删除
      ...
  })
  ```

#### C. Models层修改
- [ ] 1.1.5 删除`src/domains/task/models.py:75`文档中的level/path说明
- [ ] 1.1.6 删除`src/domains/task/models.py:80-81`文档中的树结构功能说明
- [ ] 1.1.7 删除`src/domains/task/models.py:313-335`的calculate_path方法
- [ ] 1.1.8 删除`src/domains/task/models.py:337-354`的calculate_level方法
- [ ] 1.1.9 删除`src/domains/task/models.py:376-383`的get_path_depth方法

#### D. Repository层修改（删除未使用的方法）
- [ ] 1.1.10 删除`repository.py:639-687`的get_tasks_by_level方法
- [ ] 1.1.11 删除`repository.py:689-749`的get_subtree_tasks方法（使用path）
- [ ] 1.1.12 删除`repository.py:819-867`的get_tasks_by_path_prefix方法
- [ ] 1.1.13 修改`repository.py:195-291`的get_all_descendants方法（递归CTE中使用level）：
  ```python
  # 删除递归查询中的level字段
  # 保留功能但不返回level
  ```

#### E. 测试文件检查
- [ ] 1.1.14 验证`tests/domains/task/test_task_models_basic.py:132-133`的断言仍然有效
- [ ] 1.1.15 检查其他测试文件是否有level/path残留

#### F. 文档更新
- [ ] 1.1.16 更新`docs/`中所有提到level/path的文档
- [ ] 1.1.17 更新`openspec/specs/task-crud/spec.md`删除相关requirement

### 验证方式
```bash
# 1. 确认Schema中无level/path
rg "level.*Field|path.*Field" src/domains/task/schemas.py
# 应该返回空

# 2. 确认Service中无硬编码
rg "\"level\"|\"path\"" src/domains/task/service.py | grep -v "# "
# 应该返回空

# 3. 确认Models中无方法
rg "def.*level|def.*path|get_path_depth" src/domains/task/models.py
# 应该返回空

# 4. 确认Repository中方法已删除
rg "def get_tasks_by_level|def get_subtree_tasks|def get_tasks_by_path" src/domains/task/repository.py
# 应该返回空

# 5. 全局搜索确认
rg "\blevel\b:\s*int|\bpath\b:\s*str" src/domains/task/ --type py
# 应该只返回函数参数，无字段定义
```

### 注意事项
⚠️ **保留项**：
- `completion_percentage`字段**保留**（用于父任务完成度计算）
- `parent_id`字段**保留**（基本层级关系）
- `repository.get_all_descendants`方法**保留**（递归查询子任务）

⚠️ **测试验证**：
- 现有测试已经预期level/path不存在
- 修改后运行测试应该全部通过

### 预估工时
45分钟（比之前估计多15分钟，因为发现更多需要删除的代码）

---

## 【1.2】删除is_overdue和duration_minutes字段（可并行）⚡

### 修改范围
删除两个计算字段，将计算职责转移到前端。

### 子任务

#### A. Models层修改
- [ ] 1.2.1 删除`src/domains/task/models.py:254-267`的is_overdue属性：
  ```python
  @property
  def is_overdue(self) -> bool:
      """检查任务是否过期"""
      ...  # 删除整个方法
  ```
- [ ] 1.2.2 删除`src/domains/task/models.py:269-275`的duration_minutes属性：
  ```python
  @property
  def duration_minutes(self) -> Optional[int]:
      """计算计划持续时间（分钟）"""
      ...  # 删除整个方法
  ```
- [ ] 1.2.3 更新`models.py:310`的to_dict方法，删除这两个字段的返回：
  ```python
  # 删除这两行
  "is_overdue": self.is_overdue,
  "duration_minutes": self.duration_minutes
  ```

#### B. Schemas层修改
- [ ] 1.2.4 删除`src/domains/task/schemas.py:379-380`的字段定义：
  ```python
  # 删除这两行
  is_overdue: bool = Field(..., description="是否过期")
  duration_minutes: Optional[int] = Field(None, description="计划持续时间（分钟）")
  ```

#### C. Service层修改
- [ ] 1.2.5 删除`src/domains/task/service.py:329-330`（get_tasks方法）的赋值
- [ ] 1.2.6 删除`src/domains/task/service.py:538-539`（create_task方法）的计算和赋值：
  ```python
  # 删除这几行
  duration_minutes = None
  if hasattr(request, 'planned_start_time') ...
      duration_minutes = int(...)

  is_overdue = False
  if hasattr(request, 'due_date') ...
      is_overdue = ...

  # 结果字典中也删除
  "is_overdue": is_overdue,
  "duration_minutes": duration_minutes
  ```
- [ ] 1.2.7 删除`src/domains/task/service.py:643-644`（_build_task_response方法）的字段：
  ```python
  # 删除这两行
  "is_overdue": task.is_overdue,
  "duration_minutes": task.duration_minutes
  ```

#### D. 文档更新
- [ ] 1.2.8 更新task-crud spec，添加说明：这些字段由前端计算
- [ ] 1.2.9 在API文档中说明前端计算逻辑：
  ```javascript
  // is_overdue
  const isOverdue = dueDate && new Date() > new Date(dueDate)

  // duration_minutes
  const durationMinutes = plannedEndTime && plannedStartTime
    ? (new Date(plannedEndTime) - new Date(plannedStartTime)) / 60000
    : null
  ```

### 验证方式
```bash
# 1. 确认Models中无@property
rg "@property" src/domains/task/models.py | rg "is_overdue|duration_minutes"
# 应该返回空

# 2. 确认Schemas中无字段定义
rg "is_overdue.*Field|duration_minutes.*Field" src/domains/task/schemas.py
# 应该返回空

# 3. 确认Service中无计算逻辑
rg "is_overdue\s*=|duration_minutes\s*=" src/domains/task/service.py
# 应该返回空

# 4. 全局搜索确认（只应该在测试中残留）
rg "is_overdue|duration_minutes" src/domains/task/ --type py
# 应该返回空或只在注释中
```

### 注意事项
⚠️ **前端影响**：
- 前端需要实现这两个字段的计算逻辑
- 建议在前端创建计算属性或工具函数
- 所有引用这两个字段的组件都需要更新

⚠️ **Focus领域影响**：
- focus领域可能使用duration_minutes计算专注时长
- 需要检查focus相关代码是否受影响

### 预估工时
30分钟（比之前估计多10分钟，因为需要检查focus领域影响）

---

## 【1.3】修复TaskResponse Schema（可并行）⚡

### 修改范围
1. 删除user_id字段（安全考虑）
2. 添加service_ids字段（占位，等待AI匹配）
3. 确保请求Schema也包含service_ids

### 子任务

#### A. 删除user_id字段
- [ ] 1.3.1 从`src/domains/task/schemas.py:359`删除user_id字段定义：
  ```python
  # 删除这一行
  user_id: str = Field(..., description="用户ID")
  ```
- [ ] 1.3.2 从`src/domains/task/service.py:310, 519`删除user_id的赋值：
  ```python
  # get_tasks方法中删除
  "user_id": str(user_id),  # 删除

  # create_task方法中删除（但内部仍需user_id保存到DB）
  "user_id": task.user_id,  # 删除返回
  ```
- [ ] 1.3.3 从`src/domains/task/service.py:622`删除_build_task_response中的user_id

#### B. 添加service_ids字段
- [ ] 1.3.4 在`src/domains/task/schemas.py:365`（user_id下方）添加service_ids：
  ```python
  service_ids: List[str] = Field(default=[], description="关联服务ID列表，占位字段用于后续AI服务匹配")
  ```
- [ ] 1.3.5 确认`schemas.py:116`的CreateTaskRequest已有service_ids：
  ```python
  # 如果没有，添加：
  service_ids: Optional[List[str]] = Field(
      default=[],
      description="关联服务ID列表"
  )
  ```
- [ ] 1.3.6 确认`schemas.py:225`的UpdateTaskRequest已有service_ids：
  ```python
  # 如果没有，添加：
  service_ids: Optional[List[str]] = Field(
      default=None,
      description="关联服务ID列表"
  )
  ```

#### C. Service层确保正确返回
- [ ] 1.3.7 在`service.py:291`（get_tasks方法）确保service_ids被查询和返回
- [ ] 1.3.8 在`service.py:525`（create_task方法）确保service_ids被返回
- [ ] 1.3.9 在`service.py:622`（_build_task_response方法）确保service_ids被包含

#### D. 测试文件更新
- [ ] 1.3.10 更新`tests/domains/task/test_task_models_basic.py:121`删除user_id断言：
  ```python
  # 删除或注释掉
  # assert result["user_id"] == user_id
  ```
- [ ] 1.3.11 添加service_ids的测试断言：
  ```python
  assert "service_ids" in result
  assert isinstance(result["service_ids"], list)
  ```

#### E. 文档更新
- [ ] 1.3.12 更新task-crud spec的响应格式示例
- [ ] 1.3.13 在API文档中说明service_ids当前返回空数组

### 验证方式
```bash
# 1. 确认TaskResponse无user_id
rg "user_id.*Field" src/domains/task/schemas.py | rg "TaskResponse" -A 20
# 应该返回空

# 2. 确认TaskResponse有service_ids
rg "service_ids.*Field" src/domains/task/schemas.py
# 应该返回至少3处（CreateTaskRequest, UpdateTaskRequest, TaskResponse）

# 3. 确认Service层不返回user_id
rg "\"user_id\":" src/domains/task/service.py
# 应该只在数据库保存时使用，不在返回字典中

# 4. 测试API响应
curl -X GET http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" | jq '.data.tasks[0]'
# 应该包含service_ids，不包含user_id
```

### 注意事项
⚠️ **安全考虑**：
- user_id**不返回**给前端，但数据库中仍需保存
- Service层内部验证仍然需要user_id
- JWT token中已包含user_id信息

⚠️ **service_ids占位**：
- 当前返回空数组`[]`
- 数据库需要支持JSON类型存储
- 后续AI匹配功能开发时再填充数据

### 预估工时
25分钟（比之前估计多10分钟，因为需要更新测试）

---

## 【1.4】修复SQL查询字段映射（可并行）⚡

### 修改范围
这是**最关键的任务**，修复所有API返回数据不完整的根本原因。

### 问题分析
**当前SQL只查询7个字段**：
```sql
-- ❌ 当前（错误）
SELECT id, title, description, status, parent_id, created_at, updated_at
FROM tasks
```

**缺失的10个字段**：
1. user_id（内部需要，但不返回前端）
2. priority
3. tags (JSON)
4. service_ids (JSON)
5. due_date
6. planned_start_time
7. planned_end_time
8. last_claimed_date
9. completion_percentage
10. is_deleted

### 子任务

#### A. 修复get_tasks方法SQL查询
- [ ] 1.4.1 修改`src/domains/task/service.py:290-296`的SQL查询：
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

#### B. 修复结果映射逻辑
- [ ] 1.4.2 修改`service.py:304-332`的结果映射代码：
  ```python
  tasks = []
  for row in result:
      # 处理JSON字段反序列化
      import json
      tags = json.loads(row[7]) if row[7] else []
      service_ids = json.loads(row[8]) if row[8] else []

      task_data = {
          "id": str(row[0]),
          # ❌ 不返回user_id到前端
          "title": row[2],
          "description": row[3],
          "status": row[4],
          "priority": row[5],  # 新增
          "parent_id": str(row[6]) if row[6] else None,
          "tags": tags,  # 修复：JSON反序列化
          "service_ids": service_ids,  # 新增：JSON反序列化
          "due_date": row[9],  # 新增
          "planned_start_time": row[10],  # 新增
          "planned_end_time": row[11],  # 新增
          "last_claimed_date": row[12],  # 新增
          "completion_percentage": row[13],  # 新增
          "is_deleted": row[14],  # 新增
          "created_at": row[15],
          "updated_at": row[16]
      }
      tasks.append(task_data)
  ```

#### C. 添加JSON字段处理工具函数
- [ ] 1.4.3 在`service.py`顶部添加JSON处理工具：
  ```python
  import json
  from typing import Any

  def parse_json_field(value: Any) -> list:
      """安全解析JSON字段"""
      if value is None:
          return []
      if isinstance(value, str):
          try:
              return json.loads(value)
          except json.JSONDecodeError:
              return []
      if isinstance(value, list):
          return value
      return []
  ```

#### D. 修复create_task方法
- [ ] 1.4.4 修改`service.py:489-497`，保存所有字段到数据库：
  ```python
  task = Task(
      id=str(uuid4()),  # 确保ID生成
      user_id=str(user_id),
      title=request.title,
      description=request.description,
      status=request.status or TaskStatusConst.PENDING,
      priority=request.priority or TaskPriorityConst.MEDIUM,
      parent_id=str(request.parent_id) if request.parent_id else None,
      tags=request.tags or [],  # 新增
      service_ids=request.service_ids or [],  # 新增
      due_date=request.due_date,  # 新增
      planned_start_time=request.planned_start_time,  # 新增
      planned_end_time=request.planned_end_time,  # 新增
      completion_percentage=0.0,  # 新任务默认0%
      is_deleted=False,
      created_at=datetime.now(timezone.utc),
      updated_at=datetime.now(timezone.utc)
  )
  ```

#### E. 修复create_task返回结果
- [ ] 1.4.5 修改`service.py:516-539`的返回字典，包含所有新增字段：
  ```python
  result = {
      "id": str(task.id),
      # ❌ 不返回user_id
      "title": task.title,
      "description": task.description,
      "status": task.status,
      "priority": request.priority or "medium",  # 修复
      "parent_id": task.parent_id,
      "tags": request.tags or [],  # 修复
      "service_ids": request.service_ids or [],  # 新增
      "due_date": request.due_date,  # 修复
      "planned_start_time": request.planned_start_time,  # 修复
      "planned_end_time": request.planned_end_time,  # 修复
      "last_claimed_date": None,  # 新任务为None
      "completion_percentage": 0.0,
      "is_deleted": False,
      "created_at": task.created_at,
      "updated_at": task.updated_at
  }
  ```

#### F. 数据库验证
- [ ] 1.4.6 验证数据库表包含所有字段：
  ```bash
  sqlite3 tatake.db "PRAGMA table_info(tasks);"
  # 确认包含：tags (TEXT/JSON), service_ids (TEXT/JSON),
  #          priority (TEXT), last_claimed_date (DATE)
  ```
- [ ] 1.4.7 如果缺少字段，运行数据库迁移脚本

### 验证方式
```bash
# 1. 测试创建任务
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "完整测试任务",
    "description": "测试所有字段",
    "priority": "high",
    "tags": ["测试", "完整"],
    "service_ids": ["service-001"],
    "due_date": "2025-12-31T23:59:59Z",
    "planned_start_time": "2025-01-01T09:00:00Z",
    "planned_end_time": "2025-01-01T17:00:00Z"
  }' | jq

# 预期响应包含所有字段（不包含user_id）

# 2. 测试获取任务列表
curl -X GET http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" | jq '.data.tasks[0]'

# 预期包含：tags, service_ids, priority, due_date, planned_start_time,
#          planned_end_time, last_claimed_date, completion_percentage

# 3. 验证JSON字段正确反序列化
# tags和service_ids应该是数组，不是字符串

# 4. 验证user_id不返回
curl -X GET http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" | jq '.data.tasks[0].user_id'
# 应该返回null或不存在
```

### 注意事项
⚠️ **JSON字段兼容性**：
- SQLite：JSON存储为TEXT，需要json.loads()
- PostgreSQL/MySQL：原生JSON类型，自动反序列化
- 需要兼容两种情况

⚠️ **字段索引对应**：
- row[0]=id, row[1]=user_id, row[2]=title, ...
- **必须按SQL SELECT顺序严格对应**
- 建议使用命名元组或字典避免索引错误

⚠️ **性能影响**：
- 查询字段从7个增加到17个
- 预计性能影响 < 5ms，可忽略
- JSON反序列化影响 < 1ms per record

### 预估工时
75分钟（比之前估计多15分钟，因为需要处理JSON字段和数据库验证）

**这是最复杂的任务，建议安排经验丰富的开发者负责** 🎯

---

## 【1.5】实现缺失的Service方法（可并行）⚡

### 子任务
- [ ] 1.5.1 在`service.py`实现`update_task_with_tree_structure`方法：
  ```python
  def update_task_with_tree_structure(
      self, task_id: UUID, request: UpdateTaskRequest, user_id: UUID
  ) -> Dict[str, Any]:
      """更新任务（简化版，不处理树结构复杂度）"""
      # 1. 调用repository.get_by_id验证任务存在
      # 2. 构建update_data字典（只包含非None字段）
      # 3. 调用repository.update更新任务
      # 4. 调用_build_task_response返回响应
  ```
- [ ] 1.5.2 在`service.py`实现`delete_task`方法：
  ```python
  def delete_task(
      self, task_id: UUID, user_id: UUID
  ) -> Dict[str, Any]:
      """删除任务及所有子任务"""
      # 1. 验证任务存在和权限
      # 2. 调用repository.soft_delete_cascade级联删除
      # 3. 返回删除结果
  ```
- [ ] 1.5.3 添加循环引用检测逻辑（如果更新parent_id）
- [ ] 1.5.4 添加单元测试覆盖这两个方法

### 验证方式
```bash
# 测试更新
curl -X PUT http://localhost:8000/api/v1/tasks/{id} \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"更新后的标题"}'

# 测试删除
curl -X DELETE http://localhost:8000/api/v1/tasks/{id} \
  -H "Authorization: Bearer $TOKEN"
```

### 预估工时
45分钟

---

## 【2】修复任务完成逻辑（依赖1.4）🔗

**依赖**：必须等待1.4完成，因为需要last_claimed_date字段正确查询

### 子任务
- [ ] 2.1 删除`service.py:189-197`的错误Top3判断逻辑
- [ ] 2.2 统一使用`completion_service.py`的complete_task方法
- [ ] 2.3 在`service.py:206-217`的UPDATE语句中添加last_claimed_date设置：
  ```sql
  UPDATE tasks
  SET status = 'completed',
      last_claimed_date = :claim_date,
      updated_at = :now
  WHERE id = :task_id AND user_id = :user_id
  ```
- [ ] 2.4 修复`completion_service.py:249`的uncomplete_task类型错误：
  ```python
  # 修改前：task.model_dump()
  # 修改后：self.task_service.get_task(task_id, user_id)  # 重新获取最新数据
  ```
- [ ] 2.5 添加Top3判断的集成测试

### 验证方式
```bash
# 测试完成任务
curl -X POST http://localhost:8000/api/v1/tasks/{id}/complete \
  -H "Authorization: Bearer $TOKEN"
# 检查返回的task.last_claimed_date不为null

# 测试取消完成
curl -X POST http://localhost:8000/api/v1/tasks/{id}/uncomplete \
  -H "Authorization: Bearer $TOKEN"
# 应返回200，不报500错误
```

### 预估工时
40分钟

---

## 总工时统计

- 阶段1并行任务总和：170分钟（串行）
- **并行执行预估**：60分钟（按最长任务1.4计算）
- 阶段2任务：40分钟
- **总预估工时**：100分钟（1.7小时）
- **串行执行需要**：210分钟（3.5小时）
- **效率提升**：52%

---

## 完成定义（DoD）

### 代码质量
- ✅ 所有代码通过类型检查（mypy）
- ✅ 遵循项目代码规范
- ✅ 添加完整的docstring文档

### 测试覆盖
- ✅ 单元测试覆盖率 > 85%
- ✅ 所有API scenario测试通过
- ✅ 端到端测试验证完整流程

### 文档更新
- ✅ 更新task-crud spec
- ✅ 更新API示例文档
- ✅ 记录破坏性变更

### Code Review
- ✅ 所有子任务代码审查通过
- ✅ 无安全隐患
- ✅ 性能影响评估完成

---

**下一步行动**：开始并行执行阶段1的5个任务 🚀
