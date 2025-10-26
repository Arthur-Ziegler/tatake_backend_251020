# unit-testing Specification

## Purpose
TBD - created by archiving change establish-comprehensive-unit-testing. Update Purpose after archive.
## Requirements
### Requirement: 单元测试覆盖率标准
系统 SHALL 为所有源代码文件（除 `__init__.py`）提供对应的单元测试，整体覆盖率 MUST ≥ 95%，关键业务逻辑分支覆盖率 MUST 达到 100%。

#### Scenario: 覆盖率验证通过
- **WHEN** 运行 `uv run pytest tests/units/ --cov=src --cov-fail-under=95`
- **THEN** 测试通过且覆盖率报告显示 ≥ 95%
- **AND** HTML 报告生成在 `htmlcov/index.html`

#### Scenario: 覆盖率不达标时失败
- **WHEN** 某模块覆盖率 < 95%
- **THEN** pytest 返回非 0 退出码
- **AND** 终端显示缺失覆盖的行号

### Requirement: 测试文件路径映射规则
每个源文件 SHALL 在 `tests/units/` 下有对应测试文件，路径映射规则为 `src/a/b/c.py` → `tests/units/a/b/test_c.py`。

#### Scenario: 标准模块测试映射
- **WHEN** 源文件位于 `src/domains/auth/service.py`
- **THEN** 测试文件 MUST 位于 `tests/units/domains/auth/test_service.py`

#### Scenario: 嵌套模块测试映射
- **WHEN** 源文件位于 `src/api/middleware/cors.py`
- **THEN** 测试文件 MUST 位于 `tests/units/api/middleware/test_cors.py`

#### Scenario: 工具模块测试映射
- **WHEN** 源文件位于 `src/domains/chat/tools/calculator.py`
- **THEN** 测试文件 MUST 位于 `tests/units/domains/chat/tools/test_calculator.py`

### Requirement: 测试规范文档
系统 SHALL 提供统一测试规范文档 `tests/TESTING_GUIDE.md`，包含命名规范、Mock 策略、AAA 模式、覆盖率要求等内容。

#### Scenario: 开发者查阅测试规范
- **WHEN** 开发者访问 `tests/TESTING_GUIDE.md`
- **THEN** 文档包含测试命名规范章节
- **AND** 文档包含 Mock 策略及复杂 Mock 停止信号定义
- **AND** 文档包含 AAA 模式示例代码
- **AND** 文档包含测试评审检查清单

#### Scenario: 新成员编写测试
- **WHEN** 新成员参照 TESTING_GUIDE 编写测试
- **THEN** 测试符合项目规范（命名、结构、断言）
- **AND** 测试通过 Code Review 检查清单

### Requirement: Mock 策略与复杂度控制
单元测试 SHALL 优先使用真实依赖（内存数据库、真实模型类），仅对外部服务（LLM API、第三方 API）使用 Mock。当满足复杂 Mock 触发条件时，MUST 停止测试编写并重构源码。

#### Scenario: 外部 API Mock
- **WHEN** 测试涉及 LangChain LLM 调用
- **THEN** 使用 `mocker.patch` Mock LLM 响应
- **AND** Mock 设置代码 ≤ 10 行
- **AND** 测试验证业务逻辑而非 LLM 内部

#### Scenario: 数据库使用真实依赖
- **WHEN** 测试 Repository 层数据访问
- **THEN** 使用 `sqlite:///:memory:` 内存数据库
- **AND** 不 Mock SQLAlchemy Session
- **AND** 每个测试独立数据库会话

#### Scenario: 触发复杂 Mock 停止信号
- **WHEN** 测试需要 Mock 链超过 2 层 OR 单测试 Mock 超 4 个依赖 OR Mock 设置代码超 15 行 OR 需 Mock 私有方法
- **THEN** 停止测试编写
- **AND** 提交源码重构讨论（记录问题：文件路径、原因、建议方案）

### Requirement: 测试命名与结构规范
测试函数 SHALL 遵循 `test_<方法名>_<场景>_<预期结果>` 命名模式，测试代码 SHALL 采用 AAA（Arrange-Act-Assert）结构。

#### Scenario: 正常路径测试命名
- **WHEN** 测试 `AuthService.init_guest_account` 成功场景
- **THEN** 函数名为 `test_init_guest_account_creates_valid_token`
- **AND** docstring 描述为"初始化游客账号应生成有效令牌"

#### Scenario: 异常路径测试命名
- **WHEN** 测试微信注册重复 openid
- **THEN** 函数名为 `test_wechat_register_raises_error_on_duplicate_openid`
- **AND** 使用 `pytest.raises` 验证异常类型和消息

#### Scenario: AAA 结构清晰
- **WHEN** 编写任何单元测试
- **THEN** Arrange 部分准备测试数据和依赖
- **AND** Act 部分仅执行一个被测操作
- **AND** Assert 部分验证结果和副作用
- **AND** 三个部分之间有空行分隔

### Requirement: 参数化测试与边界值覆盖
当相同逻辑需要多个输入值验证时，SHALL 使用 `pytest.mark.parametrize` 实现参数化测试，MUST 覆盖边界值（最小值、最大值、0、负数、空值）。

#### Scenario: 优先级分数计算参数化
- **WHEN** 测试 `calculate_priority_score` 函数
- **THEN** 使用 `@pytest.mark.parametrize` 覆盖所有优先级枚举值
- **AND** 参数列表包含 `("low", 1), ("medium", 3), ("high", 5), ("urgent", 10)`

#### Scenario: 边界值测试
- **WHEN** 测试任务标题长度验证
- **THEN** 参数化测试包含空字符串、1 字符、最大长度、超长字符串
- **AND** 验证边界值的正确处理（接受/拒绝）

### Requirement: 数据库测试隔离性
每个数据库测试 SHALL 使用独立的内存数据库会话（scope="function"），测试结束后 MUST 清理所有表，确保测试间无数据污染。

#### Scenario: 独立数据库会话
- **WHEN** 执行任意数据库测试
- **THEN** 使用 `test_db_session` fixture 创建独立会话
- **AND** 测试开始前执行 `SQLModel.metadata.create_all(test_engine)`
- **AND** 测试结束后执行 `SQLModel.metadata.drop_all(test_engine)`

#### Scenario: 测试间数据隔离
- **WHEN** test_A 创建用户后，test_B 执行
- **THEN** test_B 数据库中无 test_A 创建的用户
- **AND** 两个测试可以任意顺序执行

### Requirement: AI/LangChain 混合测试策略
LangChain 相关功能 SHALL 在单元测试中 Mock LLM 响应，在集成测试（`tests/integration/`）中使用真实 API 调用。单元测试 MUST 验证业务逻辑而非 LLM 内部。

#### Scenario: 单元测试 Mock LLM
- **WHEN** 测试 `ChatService.send_message`
- **THEN** Mock `langchain_anthropic.ChatAnthropic.invoke` 返回固定响应
- **AND** 验证消息处理、状态更新、数据库持久化逻辑
- **AND** 不发起真实 API 调用

#### Scenario: 集成测试真实 LLM
- **WHEN** 运行 `tests/integration/test_chat_real_llm.py`
- **THEN** 使用真实 Anthropic API Key
- **AND** 标记为 `@pytest.mark.integration` 和 `@pytest.mark.slow`
- **AND** CI 中跳过执行（本地手动触发）

### Requirement: 测试分阶段实施
测试构建 SHALL 按领域依赖关系分 3 阶段实施：Phase 1（核心领域：auth/task/user），Phase 2（业务领域：chat/focus/reward/points/top3），Phase 3（基础设施：api/core/database/utils）。

#### Scenario: Phase 1 完成验证
- **WHEN** Phase 1 所有任务完成
- **THEN** 运行 `uv run pytest tests/units/domains/{auth,task,user}/ --cov=src/domains/{auth,task,user} --cov-fail-under=95` 通过
- **AND** 生成覆盖率 HTML 报告确认 ≥ 95%

#### Scenario: Phase 间依赖管理
- **WHEN** Phase 2 开始前
- **THEN** Phase 1 覆盖率已达标
- **AND** Phase 1 所有测试稳定通过
- **AND** 可以独立运行 Phase 2 测试（不依赖 Phase 1 测试状态）

### Requirement: 测试执行性能要求
单个单元测试执行时间 SHOULD < 1 秒，整个 `tests/units/` 套件执行时间 MUST < 5 分钟。慢速测试（> 1 秒）MUST 标记 `@pytest.mark.slow`。

#### Scenario: 快速测试执行
- **WHEN** 运行 `uv run pytest tests/units/ --durations=10`
- **THEN** 前 10 慢速测试中至少 8 个 < 1 秒
- **AND** 总执行时间 < 5 分钟

#### Scenario: 慢速测试标记
- **WHEN** 测试执行时间 > 1 秒（如批量导入测试）
- **THEN** 添加 `@pytest.mark.slow` 标记
- **AND** 可通过 `pytest -m "not slow"` 跳过

### Requirement: 现有测试审查与重构
现有 `tests/units/` 下约 70 个测试文件 SHALL 逐个审查，不符合测试规范的 MUST 重构至符合标准（命名、结构、覆盖率、Mock 策略）。

#### Scenario: 测试文件审查流程
- **WHEN** 审查 `tests/units/domains/auth/test_auth_service.py`
- **THEN** 检查是否遵循命名规范（`test_<方法>_<场景>_<结果>`）
- **AND** 检查是否有 AAA 结构
- **AND** 检查是否过度 Mock 内部实现
- **AND** 检查覆盖率是否 ≥ 95%

#### Scenario: 不合格测试重构
- **WHEN** 发现测试命名为 `test_case1` 或使用魔法数字
- **THEN** 重构为符合规范的命名和结构
- **AND** 添加必要 docstring
- **AND** 重新运行确保测试通过

### Requirement: 备份文件清理
系统 SHALL 删除所有 `*.backup` 和 `*.backup.*` 文件，保持代码库整洁。

#### Scenario: 删除备份文件
- **WHEN** 执行清理任务
- **THEN** 删除 `src/api/main.py.backup`
- **AND** 删除 `src/api/openapi.py.backup.20251025_120841`
- **AND** 运行 `find src -name "*.backup*"` 返回空结果

