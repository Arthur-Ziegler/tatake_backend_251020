# Enhance LangGraph Chat Persistence and Context Management

## Why

当前的 LangGraph 聊天系统虽然功能基本完整，但在数据持久化和多轮对话管理方面存在以下问题：

1. **聊天历史未真正持久化**: `data/chat.db` 目录一直为空，聊天记录只存储在内存中
2. **会话列表功能未实现**: `list_sessions` 返回空列表，用户无法查看历史会话
3. **多轮对话上下文管理不足**: 缺少有效的上下文窗口控制机制
4. **数据库连接配置问题**: SqliteSaver 未正确配置到指定路径

## What Changes

基于 KISS 和 YAGNI 原则，提出以下增强方案：

### 1. 聊天历史持久化

**纯粹依赖 LangGraph SqliteSaver**，确保数据库文件正确保存到 `data/chat.db`

- 修复数据库连接配置，确保聊天记录真正持久化
- 基于现有 checkpointer 机制优化查询逻辑
- 避免复杂的数据同步逻辑

### 2. 多轮对话上下文管理

**基于 MessagesState 的智能上下文窗口管理**

- 创建 ContextManager 类，支持消息数量和token数量双重限制
- 实现智能截断策略，保留重要信息
- 集成到 ChatGraph 的 _agent_node 中，自动优化历史消息

### 3. API和集成测试

**完整的测试覆盖，确保所有修改的正确性**

- 数据持久化集成测试
- 会话管理功能测试
- 上下文管理集成测试
- API 端到端集成测试