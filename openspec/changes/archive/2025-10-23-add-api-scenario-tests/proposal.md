# 提案：API场景测试套件

## Why
现有API已实现32个端点，但缺乏系统化场景测试验证业务逻辑正确性。需要模拟真实用户操作流程，确保跨模块业务场景端到端正确运行。

## What Changes
- 新增`tests/scenarios/`目录，包含场景测试套件
- 基于pytest+httpx实现4类核心业务场景测试
- 实现测试数据自动创建和清理机制
- 提供README文档说明测试运行方式

## Impact
- 新增specs: `api-scenario-testing`
- 新增代码: `tests/scenarios/`目录及相关fixtures
- 测试覆盖: 32个API端点通过场景组合测试
- 运行时间: 预计15分钟内完成全部场景
