# 番茄钟系统规范变更

## ADDED Requirements

### REQ-FOCUS-001: 自动关闭未完成会话
**新增原因**：v3文档要求但未实现

#### Scenario: 开始新会话时自动关闭旧会话
- **Given** 用户已有一个进行中的专注会话（`end_time = NULL`）
- **When** 用户开始新的专注会话
- **Then** 旧会话的`end_time`设置为当前时间
- **And** 新会话正常创建
- **And** 数据库中只有1个进行中会话

#### Scenario: 无旧会话时正常创建
- **Given** 用户无进行中的会话
- **When** 用户开始新会话
- **Then** 直接创建新会话
- **And** 不执行关闭逻辑

#### Scenario: 暂停会话也触发自动关闭
- **Given** 用户处于专注会话中
- **When** 用户请求暂停（`session_type=pause`）
- **Then** 当前专注会话被关闭
- **And** 创建新的暂停会话
- **And** 专注时长可累计（focus-pause-focus合并计算）

### REQ-FOCUS-002: API文档完整性
**新增原因**：确保SwaggerUI展示自动关闭机制

#### Scenario: SwaggerUI展示自动关闭说明
- **Given** 访问`/docs` SwaggerUI
- **When** 查看`POST /focus/sessions` API
- **Then** 描述中包含"自动终止前一个未完成的session"说明
- **And** 请求参数包含`session_type`枚举值
- **And** 响应示例展示完整会话对象

## MODIFIED Requirements

### REQ-FOCUS-003: 会话创建逻辑
**修改内容**：增强会话创建前的清理逻辑

#### Scenario: 会话创建完整流程
- **Given** 用户请求创建新会话
- **When** 执行会话创建
- **Then** 步骤1：查询用户是否有进行中会话
- **And** 步骤2：如有，设置旧会话的`end_time`
- **And** 步骤3：创建新会话（`end_time = NULL`）
- **And** 步骤4：返回新会话详情和当前时间
