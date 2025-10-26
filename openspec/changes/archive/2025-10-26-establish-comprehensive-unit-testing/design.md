## Context

TaKeKe Backend 采用 DDD 六边形架构，100 个源文件散布在多个领域（auth/chat/task/user/focus/reward/points/top3）。现有测试覆盖率约 60%，质量参差不齐，缺乏统一规范。需建立严格单元测试体系确保稳定性。

**约束**：
- Python 3.11+，pytest 8.4+
- SQLite 内存数据库 `:memory:`
- pytest.ini 已配置 95% 覆盖率阈值
- 外部依赖：LangGraph、Anthropic API、OpenAI API

## Goals / Non-Goals

**Goals**：
- 95% 代码覆盖率（分支覆盖关键业务逻辑）
- 统一测试规范文档（`tests/TESTING_GUIDE.md`）
- 所有源文件 1:1 对应测试文件（除 `__init__.py`）
- 审查重构现有 70 个测试，确保符合标准

**Non-Goals**：
- 不包含性能/并发/安全测试（保留在 integration/e2e）
- 不测试数据库迁移
- 不包含集成测试重构（本提案仅关注 `tests/units/`）

## Decisions

### 1. 测试路径映射规则
**决策**：`src/a/b/c.py` → `tests/units/a/b/test_c.py`

**理由**：
- 符合 pytest 发现规则（`test_*.py`）
- 目录结构与源码镜像，易于导航
- 现有部分测试已遵循此规则

**替代方案**：
- ❌ 平铺结构 `tests/units/test_c.py`：文件多时难管理
- ❌ 按测试类型分组 `tests/units/services/test_auth_service.py`：与源码结构脱节

### 2. Mock 策略与源码优化触发点
**决策**：优先真实依赖，复杂 Mock 时停止并重构源码

**复杂 Mock 定义**（满足任一即停止）：
- Mock 链超过 2 层
- 单测试 Mock 超 4 个依赖
- Mock 设置代码超 15 行
- 需 Mock 私有方法

**理由**：复杂 Mock 暗示设计缺陷（违反依赖倒置、单一职责）

**替代方案**：
- ❌ 容忍复杂 Mock：测试脆弱，难维护
- ❌ 全部 Mock：失去集成验证价值

### 3. AI/LangChain 测试策略
**决策**：混合策略
- 单元测试：Mock LLM 响应（快速、确定性）
- 集成测试：真实 API 调用（真实性验证）

**示例**：
```python
# 单元测试 - tests/units/domains/chat/test_service.py
@pytest.fixture
def mock_llm_response():
    return {"content": "测试回复", "role": "assistant"}

def test_chat_service_basic_flow(mock_llm_response, mocker):
    mocker.patch("langchain_anthropic.ChatAnthropic.invoke", return_value=mock_llm_response)
    # 测试业务逻辑
```

### 4. 数据库测试策略
**决策**：内存数据库 + 每测试独立会话

**实现**：
```python
# conftest.py 已有实现
@pytest.fixture(scope="function")
def test_db_session():
    SQLModel.metadata.create_all(test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    SQLModel.metadata.drop_all(test_engine)
```

**理由**：
- 速度快（无磁盘 I/O）
- 隔离性强（每测试独立环境）
- 符合现有 conftest.py 实现

### 5. 分阶段实施策略
**决策**：3 阶段推进，按领域依赖关系排序

**Phase 1 - 核心领域**（无外部依赖）：
- `domains/auth/*`（11 个文件）
- `domains/task/*`（10 个文件）
- `domains/user/*`（7 个文件）

**Phase 2 - 业务领域**（依赖核心领域）：
- `domains/chat/*`（21 个文件，依赖 task）
- `domains/focus/*`（9 个文件，依赖 task）
- `domains/reward/*`（11 个文件）
- `domains/points/*`（4 个文件）
- `domains/top3/*`（9 个文件）

**Phase 3 - 基础设施**：
- `api/*`（9 个文件）
- `core/*`（9 个文件）
- `database/*`（2 个文件）
- `utils/*`（4 个文件）

**理由**：先建立核心领域信心，再扩展到依赖领域

## Risks / Trade-offs

### 风险 1：测试执行时间增加
- **现状**：现有测试约 1 分钟
- **预期**：新增测试后约 3-4 分钟
- **缓解**：
  - 使用内存数据库
  - 并行执行（pytest-xdist）
  - 按阶段拆分 CI 流水线

### 风险 2：AI 测试成本
- **问题**：真实 API 调用产生费用
- **缓解**：
  - 单元测试全部 Mock（0 成本）
  - 集成测试使用测试 API Key + 配额限制
  - CI 中跳过真实 API 测试（本地手动触发）

### 风险 3：现有测试重构破坏性
- **问题**：重构可能引入新 Bug
- **缓解**：
  - 先确保现有测试通过
  - 逐个文件重构，立即验证
  - 保留原测试备份至完成验证

### Trade-off：覆盖率 vs 测试价值
- **95% 目标** 可能导致为覆盖而测试（如简单 getter）
- **应对**：pytest.ini 已配置排除 `__repr__`、`Protocol` 等
- **原则**：追求有意义的覆盖率，非数字游戏

## Migration Plan

无需迁移（新增测试），但需协调现有工作流：

1. **第 1 天**：创建 `TESTING_GUIDE.md`，团队评审
2. **第 2-5 天**：Phase 1 实施（核心领域）
3. **第 6-10 天**：Phase 2 实施（业务领域）
4. **第 11-15 天**：Phase 3 实施（基础设施）
5. **全程**：遇复杂 Mock 立即停止，讨论重构

**回滚方案**：
- 提案独立分支，可随时废弃
- 现有测试不受影响（仅新增/重构）

## Open Questions

1. **CI 流水线调整**：是否需要拆分 unit/integration/e2e 为独立 jobs？
2. **覆盖率报告发布**：是否需要接入 Codecov 或类似服务？
3. **测试数据工厂**：是否需要统一 Factory 模式（现有 `tests/factories/` 利用率低）？
