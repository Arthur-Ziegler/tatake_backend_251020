# chat-tools-query Specification

## Purpose
TBD - created by archiving change sub2.2-chat-tools-query. Update Purpose after archive.
## Requirements
### Requirement: Query Tasks Tool
系统 SHALL提供任务列表查询工具。

#### Scenario: Query All Tasks
- **GIVEN** 用户无过滤条件
- **WHEN** LLM调用query_tasks时
- **THEN** 系统 SHALL返回用户的所有任务（默认20个）
- **AND** 包含分页信息

#### Scenario: Query by Status
- **GIVEN** status="pending"
- **WHEN** LLM调用query_tasks时
- **THEN** 系统 SHALL仅返回pending状态的任务

#### Scenario: Query Subtasks
- **GIVEN** parent_id="xxx"
- **WHEN** LLM调用query_tasks时
- **THEN** 系统 SHALL返回指定父任务的所有子任务

#### Scenario: Query with Pagination
- **GIVEN** limit=10, offset=20
- **WHEN** LLM调用query_tasks时
- **THEN** 系统 SHALL返回第21-30个任务

### Requirement: Get Task Detail Tool
系统 SHALL提供任务详情获取工具。

#### Scenario: Get Task with Subtasks
- **GIVEN** 有效task_id
- **WHEN** LLM调用get_task_detail时
- **THEN** 系统 SHALL返回完整任务信息
- **AND** 包含子任务列表
- **AND** 包含父任务信息（如果有）

#### Scenario: Get Task with Invalid Permission
- **GIVEN** task_id属于其他用户
- **WHEN** LLM调用get_task_detail时
- **THEN** 系统 SHALL返回权限错误

