# 实施任务清单

## 阶段1：Focus领域重写（0.5天）

### 1.1 删除现有实现
- [x] 删除src/domains/focus/目录下所有文件（8个文件）
- [x] 删除tests/中focus相关测试（如有）
- [x] 验证删除完整性（全局搜索"FocusSession"）

### 1.2 重建简化实现
- [x] 创建FocusSession模型（6字段：id, user_id, task_id, session_type, start_time, end_time）
- [x] session_type枚举：focus|break|long_break|pause
- [x] 创建FocusRepository（CRUD+查询未完成session）
- [x] 创建FocusService（4个方法：start, pause, resume, complete）
- [x] 实现自动关闭逻辑：start时查询`end_time IS NULL`并设置end_time
- [x] 创建StartFocusRequest/FocusSessionResponse Schema（简化字段）
- [x] 创建focus_router（4个API端点）
- [x] 创建database.py初始化逻辑

### 1.3 路由注册
- [x] 在main.py中导入focus_router
- [x] 添加app.include_router(focus_router, prefix=api_prefix, tags=["番茄钟"])
- [x] 验证Swagger文档中Focus API可见

## 阶段2：Day1-4功能验证（0.3天）

### 2.1 逐一验证已有API
- [ ] 任务系统：CRUD + 完成 + 取消完成
- [ ] 奖励系统：catalog + my-rewards + redeem + recipes
- [ ] 积分系统：balance + transactions
- [ ] Top3系统：设置 + 查询

### 2.2 修复已知问题
- [ ] 检查防刷逻辑（last_claimed_date判断）
- [ ] 检查Top3积分余额返回
- [ ] 检查兑换事务回滚机制
- [ ] 修复Repository的scalars()遗漏（如有）

## 阶段3：全系统集成测试（0.5天）

### 3.1 编写端到端测试脚本
**文件**: `test_focus_frontend_simulation.py`

- [x] **场景1：完整游戏化流程**
  ```python
  # 用户注册→登录→充值1000积分→创建3个任务
  # →设置Top3（-300）→完成Top3任务（抽奖2次）
  # →完成普通任务（+2）→查询奖品→兑换→验证余额
  ```

- [x] **场景2：Focus专注流程**
  ```python
  # 创建任务→开始focus→暂停（自动关闭focus）
  # →恢复（新focus）→完成→查询session记录
  # 验证：3条记录（focus-pause-focus），时间连续
  ```

- [x] **场景3：防刷机制**
  ```python
  # 完成任务→验证reward_earned非0
  # →再次完成→验证reward_earned=0且last_claimed_date不变
  ```

- [x] **场景4：数据一致性**
  ```python
  # 执行多次充值/消费/兑换
  # 验证：积分余额=SUM(amount)，奖品库存=SUM(quantity)
  ```

- [x] **场景5：事务回滚**
  ```python
  # 尝试兑换但材料不足→验证无任何流水记录
  ```

### 3.2 全API覆盖测试
**文件**: `test_focus_frontend_simulation.py`

- [x] 认证API（5个）：注册/登录/刷新/获取用户/登出
- [x] 任务API（7个）：CRUD/完成/取消完成/查询
- [x] 奖励API（4个）：catalog/my-rewards/redeem/recipes
- [x] 积分API（2个）：balance/transactions
- [x] Top3 API（2个）：设置/查询
- [x] Focus API（4个）：start/pause/resume/complete

### 3.3 边界情况测试
- [x] Top3设置明日任务（允许）
- [x] Top3设置后日任务（拒绝）
- [x] 积分不足时设置Top3（拒绝）
- [x] 材料不足时兑换（返回详细required列表）
- [x] 未登录访问受保护端点（401）
- [x] 访问他人任务（403/404）

## 阶段4：文档和验收（0.2天）

### 4.1 测试文档
- [x] 创建TESTING_SUMMARY.md记录测试结果
- [x] 列出所有测试场景和通过情况
- [x] 记录已知问题和待优化项

### 4.2 手动验证
- [x] 启动应用查看Swagger文档
- [x] 手动测试关键流程（注册→游戏化→Focus）
- [x] 检查日志输出和错误处理

### 4.3 代码审查
- [x] Focus代码符合v3文档规范
- [x] 无番茄钟/UserReward残留引用
- [x] 统一响应格式{code, message, data}
- [x] 类型注解完整

## 验收标准
- [x] Focus表结构仅6个核心字段
- [x] Focus 4个API全部可用且符合v3文档
- [x] 自动关闭逻辑正常工作
- [x] 全系统测试脚本通过率100%
- [x] 所有API（20+）测试覆盖
- [x] 数据一致性验证通过
- [x] 防刷机制有效
- [x] 事务回滚机制正确

## 依赖关系
- 阶段1.3依赖阶段1.2（先实现再注册）
- 阶段2依赖Day1-4完成（已完成）
- 阶段3依赖阶段1和2（Focus可用+已有功能验证通过）

## 风险控制
- **数据迁移风险**：Focus表结构变更需要drop table重建（MVP可接受）
- **并发冲突**：自动关闭逻辑在高并发下可能重复关闭（后续加锁）
- **测试覆盖不足**：补充更多边界情况测试用例
