# 修复聊天性能与状态管理问题

## Why
部署后发现4个严重问题：
1. **会话初始化慢**：create_session调用LLM生成欢迎消息，耗时1-3秒
2. **工具调用失败**：每次请求重建Graph，工具绑定策略复杂且容错性差
3. **聊天记录重复**：遍历所有checkpoint导致消息重复（误解checkpoint为增量存储）
4. **Title不一致**：metadata不持久化，get_session_info与list_sessions数据源不同

根本原因：违反LangGraph最佳实践，误解checkpoint机制，过度抽象工具绑定。

## What Changes
1. **直接写checkpoint**：删除`_create_session_with_langgraph`，只用`_create_session_record_directly`
2. **缓存Graph实例**：编译好的graph作为ChatService单例，避免重复创建
3. **只取最新状态**：用`graph.get_state(config)`获取最新checkpoint的messages
4. **State存储业务数据**：title和created_at移入ChatState，保证持久化
5. **简化工具绑定**：总是执行`bind_tools()`，失败抛异常（快速失败）
6. **原生格式返回**：API直接返回LangGraph序列化的messages（保留id、tool_calls等字段）

## Impact
**性能提升：**
- 会话创建从1-3秒降至<100ms
- Graph编译从per-request降至一次性

**稳定性提升：**
- 工具调用错误明确暴露（不再吞异常）
- 消息历史无重复
- Title数据一致

**API变更：**
- messages响应增加`id`、`tool_calls`、`additional_kwargs`字段
- State字段变更（新增`created_at`，`session_title`必填）

**风险：**
- ⚠️ State字段变更需数据库迁移（新字段有默认值，向后兼容）
- ⚠️ API响应格式变化可能需前端适配
