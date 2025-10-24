# Day5：专注系统重写+全系统集成测试

## Why
Day1-4已完成任务/奖励/Top3系统，但Focus领域实现与v3文档不符（表结构复杂、未注册路由），且缺少全系统端到端测试验证数据一致性。

## What Changes

### Focus领域完全重写
- **简化表结构**：删除7个冗余字段（planned_duration, actual_duration, status, pause_duration, interruptions_count, notes, satisfaction），仅保留6个核心字段（id, user_id, task_id, session_type, start_time, end_time, created_at）
- **扩展session_type**：支持focus|break|long_break|pause
- **4个显式API**：
  - `POST /focus/sessions`（开始专注，自动关闭前一个未完成session）
  - `POST /focus/sessions/{id}/pause`（暂停当前session，创建pause session）
  - `POST /focus/sessions/{id}/resume`（恢复专注，创建新focus session）
  - `POST /focus/sessions/{id}/complete`（显式完成当前session）
- **自动关闭逻辑**：每次start新session前，查询`end_time IS NULL`的session并设置end_time为当前时间
- **路由注册**：在main.py注册focus_router

### 全系统集成测试
- **完整游戏化流程**：注册→充值→创建任务→设置Top3→完成任务→抽奖→兑换奖品→验证余额
- **Focus会话流程**：创建任务→开始focus→暂停→恢复→完成→查询记录
- **数据一致性验证**：
  - 积分余额 = SUM(points_transactions.amount)
  - 奖品库存 = SUM(reward_transactions.quantity) GROUP BY reward_id
  - 兑换失败时零流水（事务回滚）
- **防刷机制**：同任务同日重复完成返回amount=0
- **全API覆盖测试**：覆盖所有已实现的API端点（20+接口）

### 技术债务清理
- 删除现有focus领域全部代码（models/schemas/service/repository/router/database/exceptions）
- 重建极简Focus实现（无状态管理、无duration计算）
- 清理测试用例中的旧Focus引用

## Impact
- **Affected domains**: focus（完全重写）, main.py（注册路由）
- **Database**: focus_sessions表结构变更（删除7列）
- **New files**: tests/e2e/test_full_system.py（全系统测试脚本）
- **Breaking changes**: Focus API行为变更（session自动关闭机制）

## Technical Decisions

### 为何完全重写而非修改？
v3文档极简设计理念（仅记录时段，不计算duration/管理status），与现有实现（13字段+复杂状态机）差异过大，修改成本高于重写。

### pause如何累计番茄时长？
数据库不负责计算，前端/统计服务根据task_id和时间范围累计：
```
focus(10:00-10:25) + pause(10:25-10:30) + focus(10:30-10:55) = 50分钟专注
```

### 自动关闭逻辑的并发安全性？
MVP阶段依赖数据库默认隔离级别，后续可加行锁：
```python
active = session.query(FocusSession).filter(
    FocusSession.user_id == user_id,
    FocusSession.end_time.is_(None)
).with_for_update().first()  # 行锁
```

## Out of Scope
- 性能优化（索引/缓存）
- 高并发场景处理
- Focus统计聚合API（后续版本）
- 取消完成API（POST /tasks/{id}/uncomplete）
