# chat-tools-batch Specification

## ADDED Requirements

### Requirement: Batch Create Subtasks Tool
系统 SHALL提供批量创建子任务工具（支持部分成功）。

#### Scenario: Batch Create All Success
- **GIVEN** parent_id和3个有效子任务
- **WHEN** LLM调用batch_create_subtasks时
- **THEN** 系统 SHALL创建所有3个子任务
- **AND** 返回JSON {"success": true, "created": [3个任务], "failed": []}

#### Scenario: Batch Create Partial Failure
- **GIVEN** parent_id和5个子任务，其中第3个数据无效
- **WHEN** LLM调用batch_create_subtasks时
- **THEN** 系统 SHALL创建4个成功的子任务
- **AND** 返回JSON {"success": false, "created": [4个任务], "failed": [1个错误]}
- **AND** 错误详情包含失败原因

#### Scenario: Batch Create with Invalid Parent
- **GIVEN** 不存在的parent_id
- **WHEN** LLM调用batch_create_subtasks时
- **THEN** 系统 SHALL返回错误
- **AND** 不创建任何子任务

#### Scenario: Batch Create with Permission Error
- **GIVEN** parent_id属于其他用户
- **WHEN** LLM调用batch_create_subtasks时
- **THEN** 系统 SHALL返回权限错误
- **AND** 不创建任何子任务

#### Scenario: Task Decomposition Workflow
- **GIVEN** 用户输入"把任务xxx拆分为几个子任务"
- **WHEN** LLM进行多轮对话后
- **THEN** LLM SHALL生成拆分建议（纯文本，不调用工具）
- **AND** 等待用户确认
- **AND** 用户确认后调用batch_create_subtasks
- **AND** 所有子任务使用同一parent_id
