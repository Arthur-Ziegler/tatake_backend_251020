# 配方查询API规范

## ADDED Requirements

### 配方列表端点

**Requirement**: 新增GET /rewards/recipes端点，返回所有可用兑换配方列表。

#### Scenario: 查询所有可用配方（含完整奖品信息）
- Given 系统中存在多个兑换配方
- When 用户调用GET /rewards/recipes
- Then 返回{code: 200, data: {recipes: [...]}}
- And recipes数组包含所有配方
- And 每个配方包含id, name, result_reward, materials字段
- And result_reward包含完整奖品信息{id, name, description, points_value}
- And materials数组每项包含{reward_id(UUID), reward_name, quantity}

#### Scenario: 配方为空时返回空列表
- Given 系统中不存在任何配方
- When 用户调用GET /rewards/recipes
- Then 返回{code: 200, data: {recipes: []}}

### 配方格式规范

**Requirement**: 配方数据必须包含完整的兑换信息，便于前端展示。

#### Scenario: 配方数据结构完整（enriched格式）
- Given 存在配方：10个小金币→1个钻石
- When 查询配方列表
- Then 配方数据包含：
  - id: 配方唯一标识（UUID）
  - name: 配方名称（如"金币兑换钻石"）
  - result_reward: {id: "uuid", name: "钻石", description: "珍贵奖品", points_value: 100}
  - materials: [{reward_id: "uuid", reward_name: "小金币", quantity: 10}]

#### Scenario: 配方信息填充（name到UUID转换）
- Given 配方的materials字段存储为[{reward_id: "小金币", quantity: 10}]（字符串ID）
- When Service调用get_all_recipes_enriched方法
- Then 系统通过name="小金币"查询Reward表获取UUID
- And 填充reward_id为查询到的UUID
- And 填充reward_name为"小金币"
- And 保持quantity=10不变
- And 返回enriched_materials包含完整信息
