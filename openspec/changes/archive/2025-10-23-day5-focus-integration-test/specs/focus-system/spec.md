# Focus System Specification

## ADDED Requirements

### Requirement: 简化专注会话数据模型
Focus会话记录SHALL仅保留核心时段信息（id/user_id/task_id/session_type/start_time/end_time/created_at），MUST删除状态管理和duration计算字段。

#### Scenario: 创建专注会话
**Given** 用户已登录且有可用任务
**When** 用户开始专注会话
**Then** 创建FocusSession记录，包含id/user_id/task_id/session_type/start_time，end_time为NULL

#### Scenario: 自动关闭前一个未完成会话
**Given** 用户已有一个未完成的会话（end_time为NULL）
**When** 用户开始新的会话
**Then** 前一个会话的end_time自动设置为当前时间，然后创建新会话

---

### Requirement: 支持4种会话类型
session_type MUST支持focus/break/long_break/pause四种类型，累计时长计算SHALL由前端/统计服务负责。

#### Scenario: 暂停专注会话
**Given** 用户正在进行focus会话
**When** 用户点击暂停
**Then** 当前focus会话自动关闭，创建新的pause类型会话

#### Scenario: 恢复专注会话
**Given** 用户处于pause会话中
**When** 用户恢复专注
**Then** pause会话自动关闭，创建新的focus类型会话

---

### Requirement: 提供4个显式API操作
Focus系统MUST提供start/pause/resume/complete四个显式操作端点。

#### Scenario: 开始专注
**When** POST /focus/sessions with {"task_id": "uuid", "session_type": "focus"}
**Then** 返回200及新创建的session详情

#### Scenario: 暂停专注
**When** POST /focus/sessions/{id}/pause
**Then** 返回200，当前session关闭，创建pause session

#### Scenario: 恢复专注
**When** POST /focus/sessions/{id}/resume
**Then** 返回200，pause session关闭，创建新focus session

#### Scenario: 完成专注
**When** POST /focus/sessions/{id}/complete
**Then** 返回200，session的end_time设置为当前时间

---

### Requirement: 统一响应格式
所有Focus API MUST返回{code, message, data}格式。

#### Scenario: 成功响应
**When** API调用成功
**Then** 返回{"code": 200, "message": "操作成功", "data": {...}}

#### Scenario: 错误响应
**When** API调用失败（如session不存在）
**Then** 返回{"code": 404, "message": "会话未找到", "data": {}}
