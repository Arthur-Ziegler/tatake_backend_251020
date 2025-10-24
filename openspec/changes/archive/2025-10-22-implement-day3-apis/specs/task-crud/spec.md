## MODIFIED Requirements
### Requirement: Task Completion with Rewards and Transaction Consistency
用户完成任务时，系统 SHALL 根据任务类型发放相应奖励并更新任务状态，确保事务一致性。

#### Scenario: Complete normal task
- **WHEN** 用户完成普通任务且当日未领取过奖励
- **THEN** 系统在数据库事务中完成：更新任务状态→发放2积分→更新完成度
- **AND** 返回统一格式响应包含task和reward_earned字段
- **AND** 奖励记录包含transaction_id和source_type="task_complete"

#### Scenario: Complete Top3 task
- **WHEN** 用户完成Top3任务且当日未领取过奖励
- **THEN** 系统基于v3文档判断任务是否在当日Top3中
- **AND** 50%概率发放100积分，50%概率从奖品池随机选择奖品
- **AND** 在数据库事务中完成所有操作
- **AND** 返回奖励发放详情和transaction_id

#### Scenario: Complete task already claimed today
- **WHEN** 用户重复完成当日已领取奖励的任务
- **THEN** 系统更新任务状态但不发放奖励
- **AND** 返回reward_earned字段包含amount=0

#### Scenario: Task completion transaction rollback
- **WHEN** 任务完成过程中的任何步骤失败
- **THEN** 系统回滚整个事务到初始状态
- **AND** 不发放奖励，不更新任务状态，不更新完成度

#### Scenario: API path without version prefix
- **WHEN** 调用POST /tasks/{id}/complete
- **THEN** 返回{code, message, data}统一格式响应
- **AND** data包含完整的task对象和reward_earned对象
- **AND** 不包含心情反馈字段