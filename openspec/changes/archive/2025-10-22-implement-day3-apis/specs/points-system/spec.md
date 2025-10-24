## ADDED Requirements
### Requirement: Points Balance Query
系统 SHALL 提供积分余额查询功能，使用聚合计算实时余额。

#### Scenario: Get points balance
- **WHEN** 用户调用GET /points/balance
- **THEN** 系统返回用户当前积分余额
- **AND** 余额基于points_transactions表SUM(amount)聚合计算
- **AND** 返回{code, message, data}统一格式

### Requirement: Points Transaction History with v3 Pagination
系统 SHALL 提供积分流水查询功能，严格按照v3文档分页格式。

#### Scenario: Get points transactions
- **WHEN** 用户调用GET /points/transactions?page=1&page_size=20
- **THEN** 系统返回积分流水记录列表
- **AND** 包含交易ID、数量、来源类型、来源ID、创建时间
- **AND** 严格按照v3文档格式返回pagination：{current_page, total_pages, total_count}
- **AND** 按创建时间倒序排列

## MODIFIED Requirements
### Requirement: Source Type Standardization
积分流水source_type SHALL 完全按照v3文档标准。

#### Scenario: Record points transaction
- **WHEN** 记录积分流水时
- **THEN** source_type使用：task_complete | task_complete_top3 | top3_cost | lottery_points | recharge
- **AND** Top3任务发放积分时使用task_complete_top3
- **AND** Top3设置消耗积分时使用top3_cost
- **AND** 抽奖获得积分时使用lottery_points

### Requirement: API Response Format Unification
所有积分API SHALL 返回统一响应格式。

#### Scenario: Unified response format
- **WHEN** 调用任何积分相关API
- **THEN** 返回{code: 200, message: "success", data: {...}}格式
- **AND** 错误情况下返回相应的错误码和错误信息