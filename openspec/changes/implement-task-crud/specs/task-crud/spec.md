# 任务管理（Task CRUD）规范

## ADDED Requirements

### Requirement: 创建任务
系统 SHALL 支持用户创建任务。创建时只有 title 字段必填，其他字段均可选。系统 MUST 验证 parent_id 的存在性和所有权，并验证时间字段的逻辑正确性。

#### Scenario: 成功创建基础任务
- **WHEN** 用户调用 `POST /tasks` 并传递 title（1-100 字符）
- **THEN** 系统创建新任务，status 默认为 pending，priority 默认为 medium
- **AND** 返回 HTTP 200 响应，格式为 `{ "code": 200, "data": {...}, "message": "success" }`
- **AND** data 包含完整的任务信息（包含自动生成的 id, created_at, updated_at）

#### Scenario: 创建子任务
- **WHEN** 用户创建任务时提供有效的 parent_id
- **AND** parent_id 指向的任务存在且未被删除
- **AND** parent_id 指向的任务属于当前用户
- **THEN** 系统创建新任务，并设置其 parent_id
- **AND** 返回 HTTP 200 响应

#### Scenario: parent_id 不存在
- **WHEN** 用户创建任务时提供的 parent_id 不存在或已被删除
- **THEN** 系统返回 HTTP 404 响应
- **AND** 响应格式为 `{ "code": 404, "data": null, "message": "父任务不存在" }`

#### Scenario: parent_id 不属于当前用户
- **WHEN** 用户创建任务时提供的 parent_id 属于其他用户
- **THEN** 系统返回 HTTP 403 响应
- **AND** 响应格式为 `{ "code": 403, "data": null, "message": "无权访问该父任务" }`

#### Scenario: 时间字段验证
- **WHEN** 用户同时提供 planned_start_time 和 planned_end_time
- **AND** planned_end_time 早于或等于 planned_start_time
- **THEN** 系统返回 HTTP 400 响应
- **AND** 响应格式为 `{ "code": 400, "data": null, "message": "计划结束时间必须晚于开始时间" }`

#### Scenario: title 字段验证
- **WHEN** 用户创建任务时 title 为空或超过 100 字符
- **THEN** 系统返回 HTTP 422 响应
- **AND** 响应格式为 `{ "code": 422, "data": null, "message": "任务标题必须在1-100字符之间" }`

#### Scenario: 创建时设置 status 为 completed
- **WHEN** 用户创建任务时显式设置 status 为 completed
- **THEN** 系统允许创建，并将任务状态设为 completed
- **AND** 返回 HTTP 200 响应

#### Scenario: 创建时添加标签
- **WHEN** 用户创建任务时提供 tags 数组（如 ["工作", "重要"]）
- **THEN** 系统将 tags 存储为 JSON 格式
- **AND** 返回 HTTP 200 响应，data 中包含 tags 字段

### Requirement: 获取任务详情
系统 SHALL 支持用户通过任务 ID 获取任务详情。系统 MUST 验证任务所有权，已删除的任务 MUST 返回 404 错误。

#### Scenario: 成功获取任务详情
- **WHEN** 用户调用 `GET /tasks/{id}` 且任务存在、未删除、属于当前用户
- **THEN** 系统返回 HTTP 200 响应
- **AND** 响应格式为 `{ "code": 200, "data": {...}, "message": "success" }`
- **AND** data 包含任务的所有字段（包括 is_deleted 字段）

#### Scenario: 获取已删除的任务
- **WHEN** 用户尝试获取已软删除的任务（is_deleted=true）
- **THEN** 系统返回 HTTP 404 响应
- **AND** 响应格式为 `{ "code": 404, "data": null, "message": "任务不存在" }`

#### Scenario: 获取不存在的任务
- **WHEN** 用户尝试获取不存在的任务 ID
- **THEN** 系统返回 HTTP 404 响应
- **AND** 响应格式为 `{ "code": 404, "data": null, "message": "任务不存在" }`

#### Scenario: 获取其他用户的任务
- **WHEN** 用户尝试获取不属于自己的任务
- **THEN** 系统返回 HTTP 403 响应
- **AND** 响应格式为 `{ "code": 403, "data": null, "message": "无权访问该任务" }`

### Requirement: 更新任务
系统 SHALL 支持用户更新任务信息。更新操作 MUST 支持部分更新（只更新提供的字段）。系统 MUST 禁止修改 id, user_id, created_at 字段，并在更新 parent_id 时防止循环引用。

#### Scenario: 成功部分更新任务
- **WHEN** 用户调用 `PUT /tasks/{id}` 并提供部分字段（如只更新 title）
- **AND** 任务存在、未删除、属于当前用户
- **THEN** 系统只更新提供的字段，其他字段保持不变
- **AND** 系统自动更新 updated_at 字段为当前时间
- **AND** 返回 HTTP 200 响应，data 包含更新后的完整任务信息

#### Scenario: 更新任务的 parent_id
- **WHEN** 用户更新任务的 parent_id
- **AND** 新的 parent_id 有效（存在、未删除、属于当前用户）
- **AND** 不会形成循环引用（新父任务不是当前任务的子孙任务）
- **THEN** 系统更新 parent_id
- **AND** 返回 HTTP 200 响应

#### Scenario: 更新 parent_id 导致循环引用
- **WHEN** 用户尝试将任务 A 的 parent_id 设为任务 B
- **AND** 任务 B 是任务 A 的子孙任务（会形成循环）
- **THEN** 系统返回 HTTP 400 响应
- **AND** 响应格式为 `{ "code": 400, "data": null, "message": "不能将任务移动到其子任务下，会形成循环引用" }`

#### Scenario: 更新 tags 字段
- **WHEN** 用户更新任务的 tags 字段
- **THEN** 系统完全替换原有的 tags（不是合并）
- **AND** 返回 HTTP 200 响应

#### Scenario: 更新时时间字段验证
- **WHEN** 用户更新任务，同时提供 planned_start_time 和 planned_end_time
- **AND** planned_end_time 早于或等于 planned_start_time
- **THEN** 系统返回 HTTP 400 响应
- **AND** 响应格式为 `{ "code": 400, "data": null, "message": "计划结束时间必须晚于开始时间" }`

#### Scenario: 尝试更新不可修改的字段
- **WHEN** 用户尝试在请求中包含 id, user_id, 或 created_at 字段
- **THEN** 系统忽略这些字段的修改（不返回错误，但不应用修改）
- **AND** 返回 HTTP 200 响应，被忽略的字段保持原值

#### Scenario: 更新已删除的任务
- **WHEN** 用户尝试更新已软删除的任务
- **THEN** 系统返回 HTTP 404 响应
- **AND** 响应格式为 `{ "code": 404, "data": null, "message": "任务不存在" }`

### Requirement: 删除任务
系统 SHALL 支持软删除任务。删除父任务时 MUST 级联软删除所有子任务（递归）。系统 MUST 验证任务所有权，不允许恢复已删除的任务（第一阶段）。

#### Scenario: 成功删除叶子任务
- **WHEN** 用户调用 `DELETE /tasks/{id}` 删除一个没有子任务的任务
- **AND** 任务存在、未删除、属于当前用户
- **THEN** 系统将任务的 is_deleted 设为 true
- **AND** 返回 HTTP 200 响应
- **AND** 响应格式为 `{ "code": 200, "data": {"deleted_count": 1}, "message": "任务已删除" }`

#### Scenario: 级联删除父任务及所有子任务
- **WHEN** 用户删除一个有子任务的任务
- **AND** 任务存在、未删除、属于当前用户
- **THEN** 系统递归查找所有子任务（包括子孙任务）
- **AND** 将父任务和所有子孙任务的 is_deleted 设为 true
- **AND** 返回 HTTP 200 响应
- **AND** data.deleted_count 表示总共删除的任务数量（包括父任务）

#### Scenario: 删除已删除的任务
- **WHEN** 用户尝试删除已软删除的任务
- **THEN** 系统返回 HTTP 404 响应
- **AND** 响应格式为 `{ "code": 404, "data": null, "message": "任务不存在" }`

#### Scenario: 删除其他用户的任务
- **WHEN** 用户尝试删除不属于自己的任务
- **THEN** 系统返回 HTTP 403 响应
- **AND** 响应格式为 `{ "code": 403, "data": null, "message": "无权访问该任务" }`

### Requirement: 获取任务列表
系统 SHALL 支持用户获取自己的任务列表，支持分页、状态筛选。列表 MUST 默认按创建时间倒序排列，默认不包含已删除任务。

#### Scenario: 获取默认任务列表
- **WHEN** 用户调用 `GET /tasks` 不提供任何查询参数
- **THEN** 系统返回当前用户的所有未删除任务
- **AND** 任务按 created_at 倒序排列（最新的在前）
- **AND** 默认分页：page=1, page_size=20
- **AND** 返回 HTTP 200 响应
- **AND** 响应格式为 `{ "code": 200, "data": {"tasks": [...], "pagination": {...}}, "message": "success" }`

#### Scenario: 分页查询
- **WHEN** 用户调用 `GET /tasks?page=2&page_size=10`
- **THEN** 系统返回第 2 页的 10 条任务
- **AND** pagination 包含 current_page=2, page_size=10, total_count, total_pages

#### Scenario: 按单一状态筛选
- **WHEN** 用户调用 `GET /tasks?status=pending`
- **THEN** 系统只返回 status 为 pending 的任务

#### Scenario: 按多个状态筛选
- **WHEN** 用户调用 `GET /tasks?status=pending,in_progress`
- **THEN** 系统返回 status 为 pending 或 in_progress 的任务

#### Scenario: 包含已删除任务
- **WHEN** 用户调用 `GET /tasks?include_deleted=true`
- **THEN** 系统返回包含已删除任务（is_deleted=true）的列表

#### Scenario: 空列表
- **WHEN** 用户没有任何任务或筛选后无结果
- **THEN** 系统返回 HTTP 200 响应
- **AND** data.tasks 为空数组 []
- **AND** pagination.total_count 为 0

#### Scenario: 分页参数验证
- **WHEN** 用户提供无效的分页参数（如 page=0 或 page_size>100）
- **THEN** 系统返回 HTTP 422 响应
- **AND** 响应格式为 `{ "code": 422, "data": null, "message": "分页参数无效" }`

### Requirement: 数据模型
系统 MUST 使用以下数据模型存储任务信息。所有时间字段 MUST 使用 UTC 时区。

#### Scenario: 任务表字段定义
- **WHEN** 创建或更新任务
- **THEN** 系统使用以下字段结构：
  - **id**: UUID（主键）
  - **user_id**: UUID（外键，关联 auth.id）
  - **title**: 字符串（1-100字符，必填）
  - **description**: 字符串（可选，无长度限制）
  - **status**: 枚举（"pending" | "in_progress" | "completed"，默认 pending）
  - **priority**: 枚举（"low" | "medium" | "high"，默认 medium）
  - **tags**: JSON 数组（可选，存储字符串数组）
  - **parent_id**: UUID（可选，外键，关联 tasks.id，ondelete SET NULL）
  - **due_date**: DateTime（可选，带时区）
  - **planned_start_time**: DateTime（可选，带时区）
  - **planned_end_time**: DateTime（可选，带时区）
  - **created_at**: DateTime（必填，默认当前 UTC 时间，带时区）
  - **updated_at**: DateTime（必填，默认当前 UTC 时间，自动更新，带时区）
  - **is_deleted**: Boolean（默认 false）

#### Scenario: 索引定义
- **WHEN** 数据库表创建完成
- **THEN** 系统必须建立以下索引：
  - idx_task_user_id（单列索引，user_id）
  - idx_task_status（单列索引，status）
  - idx_task_is_deleted（单列索引，is_deleted）
  - idx_task_parent_id（单列索引，parent_id）

### Requirement: 统一响应格式
系统 MUST 使用与 auth 领域一致的统一响应格式。所有成功响应 code 为 200，message 为 "success"。所有错误响应 data 为 null，message 为具体错误描述。

#### Scenario: 成功响应格式
- **WHEN** API 调用成功
- **THEN** 响应格式必须为：
  ```json
  {
    "code": 200,
    "data": { /* 实际数据 */ },
    "message": "success"
  }
  ```

#### Scenario: 错误响应格式
- **WHEN** API 调用失败（如 404, 400, 403, 422 等）
- **THEN** 响应格式必须为：
  ```json
  {
    "code": 4xx 或 5xx,
    "data": null,
    "message": "具体错误描述"
  }
  ```

#### Scenario: 列表响应格式
- **WHEN** 调用 GET /tasks 列表接口
- **THEN** 响应格式必须为：
  ```json
  {
    "code": 200,
    "data": {
      "tasks": [ /* 任务数组 */ ],
      "pagination": {
        "current_page": 1,
        "page_size": 20,
        "total_count": 100,
        "total_pages": 5
      }
    },
    "message": "success"
  }
  ```

### Requirement: 认证和授权
系统 MUST 要求所有任务相关的 API 端点都需要认证（有效的 access_token）。系统 MUST 确保用户只能访问和操作自己的任务。

#### Scenario: 未认证用户访问
- **WHEN** 用户调用任何任务 API 但未提供 access_token 或 token 无效
- **THEN** 系统返回 HTTP 401 响应
- **AND** 响应格式为 `{ "code": 401, "data": null, "message": "认证令牌无效或已过期" }`

#### Scenario: 跨用户访问控制
- **WHEN** 用户 A 尝试访问或修改用户 B 的任务
- **THEN** 系统返回 HTTP 403 响应
- **AND** 响应格式为 `{ "code": 403, "data": null, "message": "无权访问该任务" }`
