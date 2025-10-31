# Task Microservice Proxy

## MODIFIED Requirements

### Requirement: 任务CRUD SHALL通过微服务代理实现
系统MUST通过HTTP代理调用task微服务（localhost:20252）实现所有任务CRUD操作，SHALL保持API路径和响应格式完全兼容。

#### Scenario: 创建任务
- **Given** 用户已认证且提供有效任务数据
- **When** POST /tasks 携带title, description, priority
- **Then** 代理调用微服务POST /api/v1/tasks，返回创建的任务
- **And** 响应格式为`{code: 201, data: TaskResponse, message: "任务创建成功"}`
- **And** 缺失字段（parent_id等）返回null

#### Scenario: 查询任务详情
- **Given** 用户已认证且任务存在
- **When** GET /tasks/{task_id}
- **Then** 代理调用微服务GET /api/v1/tasks/{task_id}，传递user_id参数
- **And** 返回任务详情，缺失字段为null

#### Scenario: 更新任务
- **Given** 用户已认证且任务存在
- **When** PUT /tasks/{task_id} 携带更新数据
- **Then** 代理调用微服务PUT /api/v1/tasks/{task_id}
- **And** 返回更新后的任务

#### Scenario: 删除任务
- **Given** 用户已认证且任务存在
- **When** DELETE /tasks/{task_id}
- **Then** 代理调用微服务DELETE /api/v1/tasks/{task_id}/{user_id}
- **And** 返回删除成功响应

#### Scenario: 查询任务列表
- **Given** 用户已认证
- **When** GET /tasks?page=1&page_size=20
- **Then** 代理调用微服务GET /api/v1/tasks，传递user_id和分页参数
- **And** 返回任务列表和分页信息

### Requirement: Top3设置MUST集成积分扣除
系统SHALL在调用微服务前扣除300积分，MUST在微服务调用失败时回滚积分事务。

#### Scenario: 设置Top3任务
- **Given** 用户已认证且积分余额 ≥ 300
- **When** POST /tasks/special/top3 携带date和task_ids
- **Then** 先扣除300积分
- **And** 调用微服务POST /api/v1/top3
- **And** 返回Top3设置成功响应
- **And** 微服务失败时回滚积分

#### Scenario: 查询Top3任务
- **Given** 用户已认证且指定日期有Top3设置
- **When** GET /tasks/special/top3/{date}
- **Then** 代理调用微服务GET /api/v1/top3/{user_id}/{date}
- **And** 返回Top3任务详情

### Requirement: 响应格式MUST统一转换
代理层SHALL将微服务响应`{success, data}`转换为`{code, data, message}`格式，MUST正确映射成功/失败状态码。

#### Scenario: 成功响应转换
- **Given** 微服务返回`{success: true, data: {...}}`
- **When** 代理层处理响应
- **Then** 转换为`{code: 200, data: {...}, message: "success"}`

#### Scenario: 错误响应转换
- **Given** 微服务返回`{success: false, data: {...}}`
- **When** 代理层处理响应
- **Then** 根据错误类型转换为`{code: 4xx/5xx, data: null, message: "错误信息"}`

#### Scenario: 网络错误处理
- **Given** 微服务连接失败或超时
- **When** 代理层捕获异常
- **Then** 返回`{code: 503, data: null, message: "服务暂时不可用"}`

## REMOVED Requirements

### Requirement: 任务数据本地存储
**删除原因**: 迁移至微服务数据库

#### Scenario: 本地数据库操作（已删除）
- 删除Task模型
- 删除TaskRepository
- 删除TaskService（保留TaskCompletionService）
- 删除tasks表

### Requirement: Top3数据本地存储
**删除原因**: 迁移至微服务数据库

#### Scenario: 本地Top3管理（已删除）
- 删除Top3Task模型
- 删除Top3Repository
- 删除Top3Service
- 删除top3_tasks表

## PRESERVED Requirements

### Requirement: 任务完成逻辑保持不变
**保留原因**: 依赖本地奖励系统，暂不迁移

#### Scenario: 完成任务
- **Given** 任务存在且用户有权限
- **When** POST /tasks/{task_id}/complete
- **Then** 继续使用TaskCompletionService
- **And** 发放积分、处理抽奖、更新父任务完成度

#### Scenario: 取消完成任务
- **Given** 任务已完成且用户有权限
- **When** POST /tasks/{task_id}/uncomplete
- **Then** 继续使用TaskCompletionService
- **And** 更新任务状态和父任务完成度
