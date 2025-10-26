## Why

项目缺乏完整单元测试体系，导致稳定性无保障、重构风险高、质量难控制。需建立覆盖所有源码的严格单元测试系统，确保 95% 覆盖率。

## What Changes

- **测试规范文档**：创建 `tests/TESTING_GUIDE.md`，定义统一测试标准
- **测试骨架**：为 src 下 100 个源文件建立 1:1 对应测试文件（`src/a/b.py` → `tests/units/a/test_b.py`）
- **审查重构**：审查现有 70 个测试文件，重构不合格测试
- **分阶段实施**：
  - Phase 1：核心领域（auth、task、user）
  - Phase 2：业务领域（chat、focus、reward、points、top3）
  - Phase 3：基础设施（api、core、database、utils）
- **代码清理**：删除 `*.backup` 文件

## Impact

- **受影响规范**：新增 `unit-testing` 规范；关联已有 `api-layer-testing`、`service-layer-testing`
- **受影响代码**：
  - 新增：`tests/TESTING_GUIDE.md`、约 30 个新测试文件
  - 修改：现有 70 个测试文件审查重构
  - 删除：`src/api/main.py.backup`、`src/api/openapi.py.backup.*`
- **覆盖率目标**：从当前约 60% 提升至 95%
- **测试执行时间**：预计增加 2-3 分钟（使用内存数据库）
