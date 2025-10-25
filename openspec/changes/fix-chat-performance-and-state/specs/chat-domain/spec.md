# Chat Domain Spec Delta

## MODIFIED Requirements

### Requirement: Chat Session Management
系统 SHALL提供完整的会话生命周期管理功能。

#### Scenario: Session Creation (MODIFIED)
- **GIVEN** 用户需要创建新会话
- **WHEN** 调用创建会话时
- **THEN** 系统 SHALL生成UUID4作为session_id
- **AND** 直接写入checkpoint数据（不调用LLM）
- **AND** 设置created_at为UTC时间戳
- **AND** 返回固定欢迎消息
- **AND** 响应时间<100ms

**REMOVED**: ~~初始化LangGraph会话状态~~（改为直接写checkpoint）

#### Scenario: History Retrieval (MODIFIED)
- **GIVEN** 需要获取会话历史
- **WHEN** 查询历史时
- **THEN** 系统 SHALL使用`graph.get_state(config)`获取最新状态
- **AND** 提取`snapshot.values["messages"]`
- **AND** 返回LangChain原生格式（包含id、tool_calls等字段）
- **AND** 应用limit截断取最新N条消息

**REMOVED**: ~~从checkpointer遍历所有checkpoint~~（导致重复）

### Requirement: LangGraph Integration
系统 SHALL集成LangGraph框架实现对话管理和状态持久化。

#### Scenario: Graph Compilation (MODIFIED)
- **GIVEN** 需要编译LangGraph
- **WHEN** 初始化聊天服务时
- **THEN** 系统 SHALL首次调用时编译graph并缓存
- **AND** 后续请求重用缓存的graph实例
- **AND** graph作为ChatService的单例属性存储

**REMOVED**: ~~每次请求创建临时graph~~（性能问题）

#### Scenario: Tool Binding (MODIFIED)
- **GIVEN** 需要绑定工具到模型
- **WHEN** 编译LangGraph时
- **THEN** 系统 SHALL总是执行`model.bind_tools(all_tools)`
- **AND** 绑定失败直接抛出异常（快速失败）
- **AND** 日志记录成功绑定的工具数量

**REMOVED**: ~~基于模型名称判断是否绑定~~（逻辑复杂）
**REMOVED**: ~~吞掉绑定异常~~（隐藏问题）

## ADDED Requirements

### Requirement: Chat State Design
系统 SHALL使用ChatState存储会话业务数据，确保持久化。

#### Scenario: State Schema
- **GIVEN** 需要定义聊天状态
- **WHEN** 设计State时
- **THEN** ChatState SHALL继承MessagesState
- **AND** 包含必填字段：`user_id: str`, `session_id: str`
- **AND** 包含业务字段：`session_title: str = "新会话"`, `created_at: str`
- **AND** created_at使用UTC ISO 8601格式

#### Scenario: State Persistence
- **GIVEN** 会话数据需要持久化
- **WHEN** 创建或更新会话时
- **THEN** title和created_at SHALL存储在State中
- **AND** 通过checkpoint机制自动持久化
- **AND** 所有API获取的title保证一致

**RATIONALE**: metadata在invoke时不持久化，业务数据应存State

### Requirement: API Response Format
系统 SHALL返回LangGraph原生格式，减少转换开销。

#### Scenario: Message List Response
- **GIVEN** 需要返回消息历史
- **WHEN** 序列化messages时
- **THEN** 系统 SHALL保留LangChain字段：
  - `type`: 消息类型（human/ai/tool）
  - `content`: 消息内容
  - `id`: 消息唯一标识
  - `tool_calls`: 工具调用数组（AI消息）
  - `additional_kwargs`: 额外元数据
- **AND** 不进行自定义格式转换

#### Scenario: State Snapshot Response
- **GIVEN** 需要返回会话详情
- **WHEN** 获取会话信息时
- **THEN** 系统 SHALL直接返回State字段：
  - `session_id`, `user_id`, `session_title`, `created_at`
  - `message_count`: 从messages数组长度计算
