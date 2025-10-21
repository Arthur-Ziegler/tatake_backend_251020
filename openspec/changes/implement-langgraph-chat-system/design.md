## Context
本变更引入LangGraph作为新的技术栈组件，用于构建AI对话系统。LangGraph是一个基于图的对话流框架，支持状态持久化和工具调用。需要在现有DDD架构中集成LangGraph，同时保持架构的一致性。

## Goals / Non-Goals
- Goals:
  - 实现基于LangGraph的对话管理系统
  - 提供完整的会话管理和消息处理功能
  - 集成简单的工具调用机制
  - 保持与现有DDD架构的一致性
- Non-Goals:
  - 性能优化（当前不考虑）
  - 复杂的多轮对话管理
  - 高级工具集成（仅占位工具）

## Decisions
- Decision: 使用LangGraph作为对话管理框架
  - 理由: LangGraph提供原生的状态持久化和工具调用，符合需求
  - 替代方案: 自建对话系统（更复杂）
- Decision: 聊天域独立数据库
  - 理由: 避免与现有系统耦合，利用LangGraph的SQLiteMemory
  - 替代方案: 共享数据库（增加复杂性）
- Decision: 不使用user_sessions表，完全依赖LangGraph
  - 理由: 遵循KISS原则，降低复杂性
  - 替代方案: 额外的会话表（增加数据同步负担）

## Risks / Trade-offs
- Risk: LangGraph学习曲线
  - 缓解: 使用简单对话模式，避免复杂特性
- Risk: 会话查询性能
  - 缓解: 当前无性能要求，后续可优化
- Trade-off: 简单性 vs 功能完整性
  - 选择: 优先简单性，功能后续迭代

## Migration Plan
1. 安装LangGraph相关依赖
2. 创建聊天域目录结构
3. 实现LangGraph图定义和工具
4. 创建聊天API路由
5. 集成JWT认证链路
6. 编写测试
7. 验证API功能

## Open Questions
- 无重大未解决问题