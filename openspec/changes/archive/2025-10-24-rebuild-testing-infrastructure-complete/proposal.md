## Why
测试基础设施完全损坏，pytest无法运行，无法验证v3业务规则和功能完整性

## What Changes
- **BREAKING**：重建完整的测试框架和fixtures
- 修复所有导入路径和依赖问题
- 为每个领域创建独立的单元测试
- 构建基于v3文档的场景测试
- 实现测试数据库隔离和清理机制

## Impact
- Affected specs: `api-layer-testing`, `service-layer-testing`, `api-scenario-testing`, `task-crud`, `focus-system`, `chat-domain`
- Affected code: 所有领域测试文件、全局测试配置、pytest fixtures