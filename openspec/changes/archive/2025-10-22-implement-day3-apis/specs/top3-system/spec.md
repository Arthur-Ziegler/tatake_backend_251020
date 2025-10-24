## ADDED Requirements
### Requirement: Top3 Task Management
系统 SHALL 提供Top3任务设置和查询功能，用户可设置3个重要任务，消耗300积分。

#### Scenario: Set Top3 tasks
- **WHEN** 用户调用POST /tasks/top3设置Top3任务
- **THEN** 系统验证积分余额≥300，扣除300积分
- **AND** 创建Top3记录，限制每天只能设置一次
- **AND** 验证所有任务属于当前用户
- **AND** 返回设置成功信息和剩余积分

#### Scenario: Query Top3 tasks
- **WHEN** 用户调用GET /tasks/top3/{date}查询指定日期Top3
- **THEN** 系统返回该日期的Top3任务列表
- **AND** 包含任务位置信息和完整任务详情

#### Scenario: Top3 task completion reward
- **WHEN** 用户完成Top3任务且当日未领取过奖励
- **THEN** 系统50%概率发放100积分，50%概率发放奖品
- **AND** 更新任务状态和奖励流水记录
- **AND** 在响应中包含奖励发放详情

## MODIFIED Requirements
### Requirement: Top3 Task Identification with Position
系统 SHALL 基于当日Top3记录判断任务是否属于Top3任务，支持位置信息。

#### Scenario: Check if task is Top3
- **WHEN** 系统需要判断任务是否为Top3任务
- **THEN** 查询用户当日Top3记录
- **AND** 解析JSON格式的task_ids列表，包含position字段
- **AND** 格式：[{'task_id': 'uuid', 'position': 1}, {'task_id': 'uuid', 'position': 2}]
- **AND** 返回任务是否在当日Top3中的布尔值

#### Scenario: Set Top3 with positions
- **WHEN** 用户设置Top3任务时
- **THEN** 系统记录每个任务的位置信息（1-3）
- **AND** 按position排序存储任务列表
- **AND** 查询时按position顺序返回任务