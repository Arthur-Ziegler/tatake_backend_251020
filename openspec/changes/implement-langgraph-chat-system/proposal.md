## Why
基于TaKeKe API设计文档，需要实现AI对话系统功能，为用户提供智能对话体验。当前系统缺少聊天功能，需要集成LangGraph框架来构建状态化的对话管理系统。

## What Changes
- 新增独立的聊天域（chat domain）作为DDD架构的一部分
- 实现基于LangGraph的对话管理系统，使用SQLiteMemory进行状态持久化
- 创建4个核心API端点：创建会话、发送消息、获取历史、获取会话列表
- 集成简单的工具调用机制（加减法计算器）
- 建立JWT认证到LangGraph配置的传递链路

## Impact
- **新增capabilities**: `chat-domain` (聊天域)
- **修改specs**: `api-layer-architecture` (添加聊天API)
- **新增代码文件**:
  - `src/domains/chat/` 完整的聊天域实现
  - `src/api/chat.py` 聊天API路由
  - 独立的SQLite数据库文件 `data/chat.db`
- **新增依赖**: langgraph, langchain-openai
- **无性能要求**: 完全依赖LangGraph原生能力，包括会话查询