## Why
实现阶段1 Day3的完整基础API闭环，包含任务完成→奖励发放→基础查询→Top3管理的全部功能，建立完整的游戏化任务管理系统。

## What Changes
- 修改数据模型：RewardTransaction匹配v3文档，TaskTop3支持position字段，统一source_type枚举值
- 修改任务完成API，移除心情反馈，按v3文档发放奖励，集成Top3判断，立即抽奖
- 新增奖品目录API，从.env配置初始化奖品池和兑换配方
- 新增我的奖品API，简化显示无过期时间
- 新增积分余额API（路径改为balance）
- 新增积分流水API，严格按照v3文档分页格式
- 新增Top3设置和查询API，包含300积分消耗机制和位置信息
- 统一所有API响应格式为{code, message, data}
- 实现事务一致性：任务完成→奖励发放→完成度更新原子操作
- 扩展.env配置，包含奖品、配方、奖励参数，保留LLM配置
- 添加详细启动日志记录和HTTP标准错误码处理
- 创建test目录下的专门测试工程，包含测试数据和自动化测试脚本
- 系统启动时自动创建测试用户并初始化测试数据

## Impact
- Affected specs: task-crud, reward-system, points-system, top3-system
- Affected code: src/domains/task/, src/domains/reward/, src/domains/points/, src/domains/top3/, .env配置
- Database: RewardTransaction模型字段调整，TaskTop3模型支持position，新增配置数据
- New directories: test/ (测试工程、测试数据、自动化脚本)