# chat-task-tools Specification Delta

## ADDED Requirements

### Requirement: Task Management Tools
系统 SHALL提供完整的任务管理工具集，支持通过自然语言对话管理任务。

#### Scenario: Create Task Tool
- **GIVEN** 用户需要创建任务
- **WHEN** LLM调用create_task工具时
- **THEN** 系统 SHALL接收title, description, parent_id等参数
- **AND** 从InjectedState获取user_id
- **AND** 调用TaskService创建任务
- **AND** 返回JSON格式 `{"success": true, "data": {"id": "...", "title": "..."}, "message": "任务创建成功"}`

#### Scenario: Update Task Tool
- **GIVEN** 用户需要修改任务
- **WHEN** LLM调用update_task工具时
- **THEN** 系统 SHALL验证task_id所属权限
- **AND** 更新title/description/status等字段
- **AND** 返回更新后的任务信息

#### Scenario: Delete Task Tool
- **GIVEN** 用户需要删除任务
- **WHEN** LLM调用delete_task工具时
- **THEN** 系统 SHALL验证任务所属权限
- **AND** 执行软删除（设置deleted_at）
- **AND** 返回删除确认信息

### Requirement: Task Query Tools
系统 SHALL提供灵活的任务查询能力，支持条件过滤和详情获取。

#### Scenario: Query Tasks Tool
- **GIVEN** 用户需要查询任务列表
- **WHEN** LLM调用query_tasks工具时
- **THEN** 系统 SHALL支持status, parent_id, limit等过滤参数
- **AND** 仅返回当前用户的任务
- **AND** 返回任务列表JSON格式
- **AND** 包含分页信息（total, limit, offset）

#### Scenario: Get Task Detail Tool
- **GIVEN** 用户需要查看任务详情
- **WHEN** LLM调用get_task_detail工具时
- **THEN** 系统 SHALL返回完整任务信息
- **AND** 包含子任务列表（如果有）
- **AND** 包含父任务信息（如果有）
- **AND** 验证访问权限

### Requirement: Task Search Tool
系统 SHALL提供任务搜索工具，支持LLM智能匹配。

#### Scenario: Search Tasks Tool (LLM Analysis Mode)
- **GIVEN** 用户需要搜索任务
- **WHEN** LLM调用search_tasks工具时
- **THEN** 系统 SHALL获取用户所有任务（最多100个）
- **AND** 返回简化的任务列表JSON
- **AND** 包含任务ID、标题、描述、状态
- **AND** 附带提示信息供LLM分析匹配
- **AND** LLM自行从列表中选择相关任务

#### Scenario: Search Performance Limit
- **GIVEN** 用户任务数量超过100个
- **WHEN** 调用搜索工具时
- **THEN** 系统 SHALL仅返回最近更新的100个任务
- **AND** 在返回信息中说明限制情况

### Requirement: Batch Subtask Creation
系统 SHALL支持批量创建子任务，用于任务智能拆分场景。

#### Scenario: Batch Create Subtasks Tool
- **GIVEN** 用户确认任务拆分方案
- **WHEN** LLM调用batch_create_subtasks工具时
- **THEN** 系统 SHALL接收parent_id和subtasks列表
- **AND** subtasks格式为 `[{"title": "...", "description": "..."}]`
- **AND** 批量创建所有子任务
- **AND** 返回创建成功的子任务列表
- **AND** 如果部分失败，返回成功和失败的详细信息

#### Scenario: Task Decomposition Workflow
- **GIVEN** 用户输入宏大任务
- **WHEN** 进行多轮对话确认拆分方案
- **THEN** LLM SHALL首先理解任务需求
- **AND** 生成拆分建议（纯文本，不调用工具）
- **AND** 等待用户确认
- **AND** 用户确认后调用create_task创建父任务
- **AND** 然后调用batch_create_subtasks创建子任务
- **AND** 所有操作使用同一会话的State（user_id持久化）

### Requirement: Tool Security and Permissions
系统 SHALL确保所有工具操作的安全性和权限隔离。

#### Scenario: User ID Injection via State
- **GIVEN** 工具需要验证用户身份
- **WHEN** 工具被LangGraph调用时
- **THEN** 系统 SHALL通过InjectedState注入user_id
- **AND** user_id来自API层的JWT认证
- **AND** 工具内部无法伪造或修改user_id

#### Scenario: Permission Validation
- **GIVEN** 工具尝试操作任务
- **WHEN** 验证权限时
- **THEN** 系统 SHALL检查task.user_id == state.user_id
- **AND** 不匹配时返回权限错误
- **AND** 错误信息不泄露其他用户的任务信息

#### Scenario: Error Response Format
- **GIVEN** 工具执行失败
- **WHEN** 返回错误信息时
- **THEN** 系统 SHALL返回标准JSON格式
- **AND** 格式为 `{"success": false, "error": "错误描述"}`
- **AND** 包含用户友好的错误提示
- **AND** 不暴露敏感的堆栈信息

### Requirement: Tool Integration with LangGraph
系统 SHALL将新工具集成到现有LangGraph图结构中。

#### Scenario: Tool Registration
- **GIVEN** 需要注册任务管理工具
- **WHEN** 构建LangGraph图时
- **THEN** 系统 SHALL将7个工具注册到ToolNode
- **AND** 使用标准的@tool装饰器定义
- **AND** 工具自动绑定到ChatOpenAI模型
- **AND** 工具描述清晰，供LLM理解调用时机

#### Scenario: Tool Response Handling
- **GIVEN** 工具返回JSON格式响应
- **WHEN** LLM接收工具响应时
- **THEN** LLM SHALL解析JSON内容
- **AND** 将结构化数据转换为自然语言
- **AND** 向用户展示友好的回复
- **AND** 如遇错误，解释原因并建议解决方案
