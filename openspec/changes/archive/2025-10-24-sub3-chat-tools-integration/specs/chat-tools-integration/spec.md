# chat-tools-integration Specification

## MODIFIED Requirements

### Requirement: Tool Registration in LangGraph
系统 SHALL将所有任务管理工具注册到LangGraph。

#### Scenario: Register All Tools
- **GIVEN** 所有7个任务工具已实现
- **WHEN** 构建LangGraph图时
- **THEN** 系统 SHALL将8个工具注册到ToolNode
- **AND** 包含：sesame_opener, create_task, update_task, delete_task, query_tasks, get_task_detail, search_tasks, batch_create_subtasks
- **AND** 工具自动绑定到ChatOpenAI模型

#### Scenario: Tool Descriptions
- **GIVEN** 工具已注册
- **WHEN** LLM接收工具列表时
- **THEN** 每个工具 SHALL有清晰的描述
- **AND** LLM能理解工具的调用时机和参数

### Requirement: State Propagation
系统 SHALL确保user_id正确传递到工具。

#### Scenario: State Propagation from API to Tools
- **GIVEN** API层解析JWT得到user_id
- **WHEN** 调用聊天服务时
- **THEN** 系统 SHALL传递user_id到config
- **AND** config传递到LangGraph
- **AND** State在所有节点间传递
- **AND** InjectedState注入到工具

#### Scenario: Tool Permission Validation
- **GIVEN** 工具从InjectedState获取user_id
- **WHEN** 工具执行时
- **THEN** 系统 SHALL验证user_id存在
- **AND** 所有数据库操作使用该user_id
- **AND** 确保数据隔离

### Requirement: Backward Compatibility
系统 SHALL确保现有工具不受影响。

#### Scenario: Existing Tool Still Works
- **GIVEN** 新工具已注册
- **WHEN** LLM调用sesame_opener时
- **THEN** 系统 SHALL正常执行
- **AND** 不影响现有功能
