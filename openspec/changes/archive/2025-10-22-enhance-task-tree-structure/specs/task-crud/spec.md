## MODIFIED Requirements

### Requirement: 数据模型
系统 MUST 使用以下数据模型存储任务信息，新增树结构支持字段。所有时间字段 MUST 使用 UTC 时区。

#### Scenario: 任务表字段定义扩展
- **WHEN** 重建Task表结构
- **THEN** 系统使用以下字段结构：
  - **id**: UUID（主键）
  - **user_id**: UUID（外键，关联 auth.id）
  - **title**: 字符串（1-100字符，必填）
  - **description**: 字符串（可选，无长度限制）
  - **status**: 枚举（"pending" | "in_progress" | "completed"，默认 pending）
  - **priority**: 枚举（"low" | "medium" | "high"，默认 medium）
  - **tags**: JSON 数组（可选，存储字符串数组）
  - **parent_id**: UUID（可选，外键，关联 tasks.id，ondelete SET NULL）
  - **level**: 整数（默认 0，任务层级深度，0表示根任务）
  - **path**: 字符串（默认空，任务路径格式如'/uuid1/uuid2/uuid3'）
  - **completion_percentage**: 浮点数（默认 0.0，范围 0.0-100.0）
  - **estimated_pomodoros**: 整数（默认 1，预计番茄钟数量）
  - **actual_pomodoros**: 整数（默认 0，实际完成的番茄钟数量）
  - **due_date**: DateTime（可选，带时区）
  - **planned_start_time**: DateTime（可选，带时区）
  - **planned_end_time**: DateTime（可选，带时区）
  - **created_at**: DateTime（必填，默认当前 UTC 时间，带时区）
  - **updated_at**: DateTime（必填，默认当前 UTC 时间，自动更新，带时区）
  - **is_deleted**: Boolean（默认 false）

#### Scenario: 索引定义扩展
- **WHEN** 数据库表创建完成
- **THEN** 系统必须建立以下索引：
  - idx_task_user_id（单列索引，user_id）
  - idx_task_status（单列索引，status）
  - idx_task_is_deleted（单列索引，is_deleted）
  - idx_task_parent_id（单列索引，parent_id）
  - idx_task_level（单列索引，level）
  - idx_task_path（单列索引，path，支持前缀查询）
  - idx_task_completion（单列索引，completion_percentage）
  - idx_task_user_level（复合索引，user_id, level）

### Requirement: 创建任务
系统 SHALL 支持用户创建任务，并自动计算任务层级和路径。系统 MUST 验证 parent_id 的存在性和所有权，并自动设置 level 和 path 字段。

#### Scenario: 创建根任务
- **WHEN** 用户调用 `POST /tasks` 且不提供 parent_id
- **AND** title 为 1-100 字符
- **THEN** 系统创建新任务，level 设为 0，path 设为空字符串
- **AND** status 默认为 pending，priority 默认为 medium
- **AND** 返回 HTTP 200 响应，包含所有新增字段

#### Scenario: 创建子任务
- **WHEN** 用户创建任务时提供有效的 parent_id
- **AND** parent_id 指向的任务存在且未删除
- **AND** parent_id 指向的任务属于当前用户
- **THEN** 系统创建新任务，设置其 parent_id
- **AND** 自动计算 level = 父任务.level + 1
- **AND** 自动计算 path = 父任务.path + '/' + task_id
- **AND** 返回 HTTP 200 响应

#### Scenario: 创建深层嵌套任务
- **WHEN** 用户创建任务时提供 parent_id 指向一个已有子任务的任务
- **THEN** 系统创建新任务，并正确计算 level 和 path
- **AND** level 应为父任务层级 + 1
- **AND** path 应包含完整的路径层级

### Requirement: 更新任务
系统 SHALL 支持用户更新任务信息，更新 parent_id 时 MUST 重新计算 level 和 path 字段，并防止循环引用。更新任务状态时 MUST 触发完成度重新计算。

#### Scenario: 更新任务的 parent_id
- **WHEN** 用户调用 `PUT /tasks/{id}` 并修改 parent_id
- **AND** 新的 parent_id 有效（存在、未删除、属于当前用户）
- **AND** 不会形成循环引用
- **THEN** 系统更新 parent_id
- **AND** 重新计算 level 为新父任务的 level + 1
- **AND** 重新计算 path 为新父任务的 path + '/' + task_id
- **AND** 返回 HTTP 200 响应，包含更新后的 level 和 path

#### Scenario: 更新 parent_id 导致循环引用
- **WHEN** 用户尝试将任务 A 的 parent_id 设为任务 A 的子孙任务
- **THEN** 系统返回 HTTP 400 响应
- **AND** 响应格式为 `{ "code": 400, "data": null, "message": "不能将任务移动到其子任务下，会形成循环引用" }`

#### Scenario: 更新任务状态触发完成度计算
- **WHEN** 用户将任务状态更新为 completed
- **AND** 该任务有子任务
- **THEN** 系统更新任务状态
- **AND** 重新计算该任务及其所有祖先任务的 completion_percentage
- **AND** 返回 HTTP 200 响应

### Requirement: 获取任务详情
系统 SHALL 支持用户通过任务 ID 获取任务详情，返回完整的树结构字段信息。

#### Scenario: 成功获取任务详情
- **WHEN** 用户调用 `GET /tasks/{id}` 且任务存在、未删除、属于当前用户
- **THEN** 系统返回 HTTP 200 响应
- **AND** data 包含所有字段（包括新增的 level, path, completion_percentage 等）
- **AND** completion_percentage 反映实时的完成度计算结果

### Requirement: 删除任务
系统 SHALL 支持软删除任务，删除父任务时 MUST 级联软删除所有子任务，并重新计算相关任务的完成度。

#### Scenario: 级联删除父任务及所有子任务
- **WHEN** 用户删除一个有子任务的任务
- **AND** 任务存在、未删除、属于当前用户
- **THEN** 系统递归查找所有子任务（包括子孙任务）
- **AND** 将父任务和所有子孙任务的 is_deleted 设为 true
- **AND** 返回 HTTP 200 响应
- **AND** data.deleted_count 表示总共删除的任务数量（包括父任务）

### Requirement: 任务完成度计算
系统 MUST 提供基于叶子节点数量的任务完成度计算功能。

#### Scenario: 叶子节点完成度计算
- **WHEN** 系统计算某个任务的 completion_percentage
- **THEN** 系统执行以下逻辑：
  - 1. 获取该任务下的所有叶子节点（没有子节点的任务）
  - 2. 如果没有叶子节点，返回 100%（任务自身完成）或 0%（任务自身未完成）
  - 3. 统计已完成的叶子节点数量
  - 4. 完成度 = (已完成叶子节点数 / 总叶子节点数) * 100.0

#### Scenario: 复杂树结构完成度计算
- **WHEN** 任务树结构为多层嵌套
- **THEN** 系统正确递归计算所有叶子节点，得出准确的完成百分比

#### Scenario: 部分完成状态
- **WHEN** 部分子任务已完成，部分未完成
- **THEN** 系统返回基于已完成叶子节点数量的准确百分比（如 3/5 = 60.0%）

### Requirement: 统一响应格式
系统 MUST 在响应中包含新增的树结构字段。

#### Scenario: 成功响应格式扩展
- **WHEN** API 调用成功
- **THEN** 响应格式必须包含新增字段：
  ```json
  {
    "code": 200,
    "data": {
      "id": "uuid",
      "title": "任务标题",
      "level": 2,
      "path": "/uuid1/uuid2",
      "completion_percentage": 60.0,
      "estimated_pomodoros": 3,
      "actual_pomodoros": 1,
      // ... 其他现有字段
    },
    "message": "success"
  }
  ```

## ADDED Requirements

### Requirement: 循环引用检测
系统 MUST 提供循环引用检测功能，防止任务树出现无限循环。

#### Scenario: 检测直接循环引用
- **WHEN** 用户尝试将任务 A 的 parent_id 设为任务 A
- **THEN** 系统返回 HTTP 400 响应
- **AND** 错误消息为 "不能将任务设置为自身的父任务"

#### Scenario: 检测深层循环引用
- **WHEN** 用户尝试将任务 A 的 parent_id 设为任务 A 的子孙任务
- **THEN** 系统检测到循环引用并返回 HTTP 400 响应
- **AND** 错误消息为 "不能将任务移动到其子任务下，会形成循环引用"

### Requirement: 路径管理
系统 MUST 提供任务路径自动计算和管理功能。

#### Scenario: 自动路径计算
- **WHEN** 创建或更新任务的 parent_id
- **THEN** 系统自动计算并设置 path 字段
- **AND** path 格式为 "/grandparent_id/parent_id/task_id"
- **AND** 根任务的 path 为空字符串或"/task_id"

#### Scenario: 路径更新
- **WHEN** 任务被移动到新的父任务下
- **THEN** 系统更新该任务及其所有子孙任务的 path 字段
- **AND** 确保所有路径反映新的层级结构

### Requirement: 层级查询优化
系统 SHALL 提供基于树结构的高效查询功能。

#### Scenario: 按层级查询任务
- **WHEN** 需要查询特定层级的任务
- **THEN** 系统支持按 level 字段过滤
- **AND** 返回指定层级的所有任务

#### Scenario: 子树查询
- **WHEN** 需要查询某个任务的所有子任务
- **THEN** 系统使用 path 字段进行高效的前缀查询
- **AND** 查询条件为 `WHERE path LIKE '/parent_id/%'`