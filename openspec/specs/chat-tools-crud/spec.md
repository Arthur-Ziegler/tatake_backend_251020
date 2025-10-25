# chat-tools-crud Specification

## Purpose
TBD - created by archiving change sub2.1-chat-tools-crud. Update Purpose after archive.
## Requirements
### Requirement: Create Task Tool
系统 SHALL提供创建任务工具。

#### Scenario: Create Simple Task
- **GIVEN** 用户提供title="完成项目"
- **WHEN** LLM调用create_task工具时
- **THEN** 系统 SHALL从InjectedState获取user_id
- **AND** 调用TaskService.create_task()
- **AND** 返回JSON {"success": true, "data": {task_info}}

#### Scenario: Create Task with Full Fields
- **GIVEN** 用户提供所有字段（title, description, parent_id, priority, tags, due_date, planned_start_time, planned_end_time）
- **WHEN** LLM调用create_task时
- **THEN** 系统 SHALL解析所有datetime字段
- **AND** 转换parent_id为UUID
- **AND** 创建完整任务

#### Scenario: Create Task with Invalid UUID
- **GIVEN** parent_id="invalid-uuid"
- **WHEN** LLM调用create_task时
- **THEN** 系统 SHALL返回JSON {"success": false, "error": "无效的任务ID格式"}

#### Scenario: Create Task with Invalid Date
- **GIVEN** due_date="invalid-date"
- **WHEN** LLM调用create_task时
- **THEN** 系统 SHALL返回JSON {"success": false, "error": "日期格式错误..."}

### Requirement: Update Task Tool
系统 SHALL提供更新任务工具。

#### Scenario: Update Task Title
- **GIVEN** task_id和新title
- **WHEN** LLM调用update_task时
- **THEN** 系统 SHALL验证task权限
- **AND** 调用TaskService.update_task_with_tree_structure()
- **AND** 返回更新后的任务

#### Scenario: Update Task with Invalid Permission
- **GIVEN** task_id属于其他用户
- **WHEN** LLM调用update_task时
- **THEN** 系统 SHALL返回权限错误

### Requirement: Delete Task Tool
系统 SHALL提供删除任务工具。

#### Scenario: Delete Task Successfully
- **GIVEN** 有效task_id
- **WHEN** LLM调用delete_task时
- **THEN** 系统 SHALL验证权限
- **AND** 调用TaskService.delete_task()
- **AND** 返回删除确认

#### Scenario: Delete Non-existent Task
- **GIVEN** 不存在的task_id
- **WHEN** LLM调用delete_task时
- **THEN** 系统 SHALL返回"任务不存在"错误

