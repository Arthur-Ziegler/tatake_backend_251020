# Proposal: 修复架构基础问题

## Why
测试暴露三个P0架构问题：UUID类型不一致导致SQLite绑定失败、服务依赖缺失导致初始化失败、SQLModel API过时导致查询失败。阻塞所有业务功能开发。

## What Changes
- **UUID统一**：所有模型UUID字段改为str类型
- **依赖注入**：Service构造函数显式声明PointsService依赖
- **API更新**：Repository使用`session.execute().scalars()`替代`session.exec()`

## Impact
- 修复20个失败测试
- 测试通过率从10%提升到90%+
- 解除业务功能开发阻塞
