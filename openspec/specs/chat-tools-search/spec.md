# chat-tools-search Specification

## Purpose
TBD - created by archiving change sub2.3-chat-tools-search. Update Purpose after archive.
## Requirements
### Requirement: Search Tasks Tool
系统 SHALL提供任务搜索工具（LLM分析模式）。

#### Scenario: Search Tasks with Query
- **GIVEN** query="项目相关"
- **WHEN** LLM调用search_tasks时
- **THEN** 系统 SHALL获取用户所有任务（最多100个）
- **AND** 返回简化任务列表
- **AND** 包含字段：id, title, status, priority, created_at, updated_at, due_date
- **AND** 附加提示信息："请从上述任务中找出与'项目相关'相关的任务"

#### Scenario: Search Tasks with Limit
- **GIVEN** limit=50
- **WHEN** LLM调用search_tasks时
- **THEN** 系统 SHALL最多返回50个任务

#### Scenario: Search Tasks Token Cost
- **GIVEN** 用户有100个任务
- **WHEN** LLM调用search_tasks时
- **THEN** 系统 SHALL返回简化信息
- **AND** token消耗约8000-12000

#### Scenario: Search with No Tasks
- **GIVEN** 用户无任务
- **WHEN** LLM调用search_tasks时
- **THEN** 系统 SHALL返回空列表
- **AND** total=0

