# Unify Extended Domain UUID Architecture

## MODIFIED Requirements

### Requirement: Reward Service UUID Unification
RewardService所有方法MUST使用UUID参数，移除ensure_str函数依赖。

#### Scenarios:
- **redeem_reward**: user_id参数改为UUID类型
- **top3_lottery**: user_id参数改为UUID类型
- **get_reward_transactions**: user_id参数改为UUID类型
- **compose_rewards**: user_id参数改为UUID类型

### Requirement: Points Service UUID Implementation
PointsService MUST实现UUID类型安全，移除字符串参数支持。

#### Scenarios:
- **calculate_balance**: user_id参数使用UUID类型
- **add_points**: user_id参数使用UUID类型
- **get_transactions**: user_id参数使用UUID类型
- **get_statistics**: user_id参数使用UUID类型

### Requirement: Top3 Service UUID Migration
Top3Service MUST移除显式UUID转换，使用Repository层转换。

#### Scenarios:
- **set_top3**: 移除str(user_id)显式转换
- **get_user_top3**: 移除str(user_id)显式转换
- **is_task_in_today_top3**: 统一UUID参数类型
- **所有查询**: 使用UUID对象参数

### Requirement: Focus Service UUID Support
FocusService MUST实现UUID类型参数支持。

#### Scenarios:
- **start_focus_session**: user_id参数使用UUID类型
- **get_user_sessions**: user_id参数使用UUID类型
- **end_focus_session**: session_id和user_id使用UUID类型

## ADDED Requirements

### Requirement: Extended Domain Repository Pattern
所有扩展领域MUST实现Repository模式UUID转换。

#### Scenarios:
- **RewardRepository**: UUID↔String转换实现
- **PointsRepository**: UUID参数查询支持
- **Top3Repository**: UUID类型安全操作
- **FocusRepository**: UUID参数和转换逻辑

### Requirement: Extended API UUID Documentation
扩展领域API的Swagger文档MUST包含UUID格式说明。

#### Scenarios:
- **Reward API**: 所有端点的UUID参数文档
- **Points API**: 查询参数UUID格式验证
- **Top3 API**: 路径和查询参数UUID文档
- **Focus API**: 会话管理UUID格式说明

### Requirement: Cross Domain UUID Integration
扩展领域MUST支持与其他领域的UUID类型安全交互。

#### Scenarios:
- **Task-Reward**: 任务完成奖励的UUID传递
- **Task-Top3**: Top3任务的UUID关联
- **User-Points**: 用户积分查询UUID安全
- **Auth-Focus**: 用户会话UUID验证

### Requirement: Project Wide UUID Cleanup
全项目MUST清理遗留的类型转换逻辑。

#### Scenarios:
- **移除ensure_str**: 删除所有ensure_str函数调用
- **移除ensure_str_uuid**: 删除临时转换函数
- **统一UUIDConverter**: 全项目使用统一转换器
- **清理导入**: 移除不必要的UUID导入