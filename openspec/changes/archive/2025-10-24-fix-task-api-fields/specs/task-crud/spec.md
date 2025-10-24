# task-crud Specification Delta

## MODIFIED Requirements

### Requirement: API响应字段规范
系统 SHALL 返回任务的完整信息，包含所有必需字段。响应 MUST 删除敏感字段（user_id）和冗余字段（level, path, is_overdue, duration_minutes），并添加service_ids字段。

#### Scenario: TaskResponse包含完整必需字段
- **WHEN** 任务API返回任务数据（创建、获取、更新、完成等）
- **THEN** 响应data中MUST包含以下字段：
  - id (UUID字符串)
  - title (字符串，1-100字符)
  - description (字符串，可选)
  - status (枚举: pending/in_progress/completed)
  - priority (枚举: low/medium/high)
  - parent_id (UUID字符串，可选)
  - **tags (字符串数组)** ← 必须包含
  - **service_ids (字符串数组)** ← 新增字段
  - due_date (ISO 8601日期时间，可选)
  - **planned_start_time (ISO 8601日期时间，可选)** ← 必须包含
  - **planned_end_time (ISO 8601日期时间，可选)** ← 必须包含
  - **last_claimed_date (ISO 8601日期，可选)** ← 必须包含
  - **completion_percentage (浮点数，0.0-100.0)** ← 必须包含
  - is_deleted (布尔值)
  - created_at (ISO 8601日期时间)
  - updated_at (ISO 8601日期时间)

#### Scenario: TaskResponse不包含敏感和冗余字段
- **WHEN** 任务API返回任务数据
- **THEN** 响应data中MUST NOT包含以下字段：
  - **user_id** ← 已删除（安全考虑）
  - **level** ← 已删除（树结构字段）
  - **path** ← 已删除（树结构字段）
  - **is_overdue** ← 已删除（由前端计算）
  - **duration_minutes** ← 已删除（由前端计算）

#### Scenario: service_ids字段格式
- **WHEN** 任务API返回任务数据
- **THEN** service_ids字段MUST为字符串数组
- **AND** 当前阶段service_ids SHOULD返回空数组 `[]`（占位，后续AI匹配时填充）
- **AND** 前端MAY显示但不应依赖此字段的具体值

#### Scenario: tags字段正确序列化
- **WHEN** 任务包含tags数据
- **AND** tags在数据库中以JSON格式存储
- **THEN** API响应MUST将tags正确反序列化为字符串数组
- **AND** 空tags MUST返回空数组 `[]`（不是null）

#### Scenario: 前端计算is_overdue
- **WHEN** 前端需要显示任务是否过期
- **THEN** 前端SHOULD基于due_date字段自行计算：
  ```javascript
  const isOverdue = dueDate && new Date() > new Date(dueDate)
  ```
- **AND** 后端MUST NOT在API响应中包含is_overdue字段

#### Scenario: 前端计算duration_minutes
- **WHEN** 前端需要显示任务持续时间
- **THEN** 前端SHOULD基于planned_start_time和planned_end_time自行计算：
  ```javascript
  const durationMinutes = (endTime - startTime) / 60000
  ```
- **AND** 后端MUST NOT在API响应中包含duration_minutes字段

---

## MODIFIED Requirements

### Requirement: 任务完成防刷机制
系统 SHALL 在任务完成时设置last_claimed_date字段，实现终身限领机制。系统 MUST 使用Top3Service判断任务是否为Top3任务，不得使用任务标题进行判断。

#### Scenario: 首次完成任务设置last_claimed_date
- **WHEN** 用户首次调用 `POST /tasks/{id}/complete` 完成任务
- **AND** 任务的last_claimed_date为null
- **THEN** 系统MUST更新任务记录：
  - status设为'completed'
  - **last_claimed_date设为当前日期（DATE类型，YYYY-MM-DD格式）**
  - updated_at设为当前UTC时间
- **AND** 系统发放相应积分奖励

#### Scenario: 重复完成任务的防刷检测
- **WHEN** 用户尝试完成已有last_claimed_date的任务
- **THEN** 系统MUST拒绝发放奖励
- **AND** 返回points_awarded=0
- **AND** message说明"任务已完成，无法重复获得积分"
- **BUT** 任务status仍可更新为completed（幂等性）

#### Scenario: 正确判断Top3任务
- **WHEN** 系统需要判断任务是否为Top3任务
- **THEN** 系统MUST调用 `top3_service.is_task_in_today_top3(user_id, task_id)`
- **AND** MUST NOT通过任务标题或其他字段进行判断
- **AND** 只有Top3Service确认的任务才能触发Top3抽奖

#### Scenario: Top3任务抽奖逻辑
- **WHEN** 任务被确认为Top3任务
- **AND** 首次完成（last_claimed_date为null）
- **THEN** 系统MUST调用 `reward_service.top3_lottery(user_id)`
- **AND** 50%概率获得100积分
- **AND** 50%概率获得随机奖品

---

## REMOVED Requirements

### Requirement: 树结构字段管理（已删除）
~~系统 SHALL 维护任务的level和path字段，用于高效的子树查询。~~

**删除原因**：
- 数据库表中从未实现这两个字段
- 代码中硬编码假数据，无实际功能
- 增加parent_id变更时的复杂度
- 违反YAGNI原则

**替代方案**：
- 保留parent_id字段支持基本层级关系
- 使用递归CTE查询子树（repository.get_all_descendants已实现）

#### Scenario: ~~任务创建时计算level和path~~（已删除）
- ~~**WHEN** 创建新任务~~
- ~~**THEN** 系统自动计算level和path字段~~

**替代行为**：
- 只需设置parent_id字段
- level和path不再存储或返回

#### Scenario: ~~更新parent_id时更新level和path~~（已删除）
- ~~**WHEN** 更新任务的parent_id~~
- ~~**THEN** 系统递归更新所有子孙任务的level和path~~

**替代行为**：
- 只更新parent_id字段
- 无需递归更新子任务

---

## ADDED Requirements

### Requirement: Service层方法完整性
系统 SHALL 在TaskService中实现所有Router调用的方法。所有方法 MUST 遵循Repository→Service→Router的调用链，不得跳过Repository层直接操作数据库。

#### Scenario: 实现update_task_with_tree_structure方法
- **WHEN** Router调用 `task_service.update_task_with_tree_structure(task_id, request, user_id)`
- **THEN** 该方法MUST存在于TaskService类中
- **AND** 方法MUST执行以下步骤：
  1. 验证任务存在性和用户权限
  2. 构建update_data字典（只包含非None字段）
  3. 调用repository.update()更新任务
  4. 返回格式化的任务响应
- **AND** 由于已删除level/path字段，无需处理树结构更新

#### Scenario: 实现delete_task方法
- **WHEN** Router调用 `task_service.delete_task(task_id, user_id)`
- **THEN** 该方法MUST存在于TaskService类中
- **AND** 方法MUST执行以下步骤：
  1. 验证任务存在性和用户权限
  2. 调用repository.soft_delete_cascade()级联删除
  3. 返回删除结果（deleted_task_id, deleted_count, cascade_deleted）

#### Scenario: SQL查询包含所有必需字段
- **WHEN** Service层执行SQL查询获取任务数据
- **THEN** SELECT语句MUST包含以下所有字段：
  ```sql
  SELECT id, user_id, title, description, status, priority, parent_id,
         tags, service_ids, due_date, planned_start_time, planned_end_time,
         last_claimed_date, completion_percentage, is_deleted,
         created_at, updated_at
  FROM tasks
  ```
- **AND** JSON字段（tags, service_ids）MUST正确反序列化

#### Scenario: 创建任务时保存所有字段
- **WHEN** Service层创建新任务
- **THEN** MUST将所有请求字段保存到数据库：
  - title, description, status, priority, parent_id
  - **tags, service_ids** ← 必须保存
  - **due_date, planned_start_time, planned_end_time** ← 必须保存
  - user_id, created_at, updated_at

---

## Summary of Changes

### 字段变更
- ❌ 删除：user_id, level, path, is_overdue, duration_minutes
- ✅ 新增：service_ids（字符串数组）
- ✅ 修复：tags, planned_start_time, planned_end_time, due_date, last_claimed_date必须正确返回

### 逻辑变更
- ✅ last_claimed_date在任务完成时设置（防刷机制）
- ✅ Top3判断使用top3_service（删除标题判断逻辑）
- ✅ Service层实现完整方法（update_task, delete_task）
- ✅ SQL查询包含所有必需字段

### 职责变更
- ⚙️ is_overdue计算：后端 → 前端
- ⚙️ duration_minutes计算：后端 → 前端
- ⚙️ level/path维护：后端 → 无需维护

---

**相关Spec**：
- `api-layer-testing` - API层测试需要更新响应验证
- `service-layer-testing` - Service层测试需要添加新方法测试
- `focus-system` - 番茄钟系统使用task_id关联，无影响

**向后兼容性**：
- ⚠️ 破坏性变更：API响应格式变化
- ✅ 数据库Schema无变更
- ✅ JWT认证机制无变更

**迁移指南**：
- 前端需要更新响应字段引用
- 前端需要实现is_overdue和duration_minutes计算
- 前端需要处理service_ids字段（当前为空数组）
