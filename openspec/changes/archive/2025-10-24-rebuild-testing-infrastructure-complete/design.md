## Context
测试基础设施完全损坏，pytest无法运行，无法验证核心业务逻辑（如任务完成API重复调用问题）。

## Goals / Non-Goals
- Goals: 重建完整测试体系，支持DDD领域测试+场景测试，验证v3所有功能
- Non-Goals: 性能测试、压力测试、UI测试

## Decisions
- **Database策略**: 每个领域使用独立内存SQLite数据库，确保测试隔离
- **测试结构**: 领域测试在各自路径下，全局场景测试在tests/目录
- **Mock策略**: LangGraph使用真实API，微信OpenID使用模拟字符串
- **清理机制**: 每个测试函数后自动清理数据，避免状态泄露

## Risks / Trade-offs
- 内存SQLite可能缺少某些SQL特性 → 验证关键查询兼容性
- LangGraph真实API调用可能影响测试速度 → 接受作为端到端测试的一部分

## Migration Plan
1. 先修复全局测试配置
2. 逐个领域重建测试
3. 构建场景测试
4. 集成CI/CD覆盖率报告

## Open Questions
- 测试数据集初始化的最佳实践
- 异步测试的标准模式