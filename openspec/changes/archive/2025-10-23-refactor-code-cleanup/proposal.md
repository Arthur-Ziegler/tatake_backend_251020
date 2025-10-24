## Why
项目存在大量冗余代码，影响可维护性和开发效率，需要系统性清理。

## What Changes
- **删除过时文件**: docs/archive/init_database.py, run_server.py, 全部tests/archive/
- **整合重复服务**: 保留service_v2版本，删除旧版本
- **合并路由器**: src/domains/task/completion_router.py 合并到主router
- **重构测试架构**: 删除tests/api/和tests/unit/，保留tests/scenarios/，删除tests/integration/
- **清理代码质量**: 移除所有调试代码和无用导入
- **配置清理**: 删除测试配置文件

## Impact
- 减少代码量30-40%
- 提升构建和测试速度
- 简化项目结构
- 降低认知负担