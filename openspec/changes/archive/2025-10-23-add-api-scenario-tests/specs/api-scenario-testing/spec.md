# API场景测试规范

## ADDED Requirements

### Requirement: 任务完整流程场景测试
系统SHALL提供任务完整流程的端到端场景测试，验证从任务创建到奖励兑换的完整业务逻辑。

#### Scenario: 普通任务完成获得积分并兑换
- **GIVEN** 测试用户已登录
- **WHEN** 创建任务 → 完成任务 → 查询积分余额 → 查询奖品目录 → 兑换奖品
- **THEN** 任务状态为completed，积分增加2点，奖品兑换成功

#### Scenario: 任务树完成度自动更新
- **GIVEN** 存在父任务和2个子任务
- **WHEN** 完成1个子任务
- **THEN** 父任务完成度自动更新为50%

### Requirement: Top3特殊奖励场景测试
系统SHALL提供Top3任务的特殊奖励流程测试，验证300积分消耗和50%概率高价值奖励机制。

#### Scenario: 设置Top3并完成获得特殊奖励
- **GIVEN** 用户积分余额≥300
- **WHEN** 设置3个任务为Top3 → 完成其中1个Top3任务
- **THEN** 积分扣除300，完成任务获得100积分或随机奖品（50%概率）

#### Scenario: Top3任务当日重复完成无奖励
- **GIVEN** 已完成一个Top3任务并领取奖励
- **WHEN** 同日再次完成同一任务
- **THEN** 任务状态更新但不再发放奖励

### Requirement: 跨模块组合场景测试
系统SHALL提供跨模块业务场景测试，验证任务、Focus、奖励系统的协同工作。

#### Scenario: 任务关联Focus并完成
- **GIVEN** 创建任务A
- **WHEN** 开始Focus会话关联任务A → 完成Focus → 完成任务A
- **THEN** Focus记录正确保存，任务完成获得奖励，两者数据关联正确

#### Scenario: 多任务协作完成流程
- **GIVEN** 存在父任务P和子任务C1、C2
- **WHEN** 对C1执行Focus → 完成C1 → 对C2执行Focus → 完成C2
- **THEN** 父任务P完成度100%，Focus记录完整，积分累计正确

### Requirement: Focus番茄钟场景测试
系统SHALL提供Focus番茄钟完整流程测试，验证会话状态管理和时间记录。

#### Scenario: Focus完整流程
- **GIVEN** 存在任务T
- **WHEN** 开始Focus → 暂停 → 恢复 → 完成 → 查询历史
- **THEN** 所有会话记录正确，开始/结束时间准确，pause和resume会话关联正确

#### Scenario: 自动关闭前一会话
- **GIVEN** 存在进行中的Focus会话S1
- **WHEN** 开始新的Focus会话S2
- **THEN** S1自动关闭（end_time设置），S2成功创建

### Requirement: 测试数据管理
系统SHALL提供自动化的测试数据创建和清理机制，确保测试独立性和可重复性。

#### Scenario: 测试用户自动创建和清理
- **GIVEN** 开始运行场景测试
- **WHEN** pytest执行测试文件
- **THEN** 自动创建测试用户，测试结束后自动清理所有关联数据

#### Scenario: 每个测试文件共享用户
- **GIVEN** 一个测试文件包含多个场景
- **WHEN** 运行该测试文件
- **THEN** 所有场景共享同一测试用户，但任务和奖励数据独立

### Requirement: 测试执行和报告
系统SHALL支持灵活的测试执行方式和清晰的测试报告输出。

#### Scenario: 独立运行特定场景
- **GIVEN** 场景测试套件已部署
- **WHEN** 执行`uv run pytest tests/scenarios/test_01_task_flow.py -v`
- **THEN** 仅运行任务流程场景，其他场景不执行

#### Scenario: 测试失败不中断其他场景
- **GIVEN** test_01中某个断言失败
- **WHEN** 继续执行test_02、test_03、test_04
- **THEN** 所有场景都执行完毕，最后汇总报告显示失败详情

#### Scenario: 查看测试文档
- **GIVEN** 新开发者需要了解场景测试
- **WHEN** 查看`tests/scenarios/README.md`
- **THEN** 文档包含测试目的、运行方式、场景说明、数据清理方法
