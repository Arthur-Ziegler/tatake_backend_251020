# 任务清单

## 数据库层
- [ ] 删除`rewards`表的`stock_quantity`字段（迁移脚本）
- [ ] 删除`rewards`表的`cost_type`和`cost_value`字段（已被积分兑换替代）
- [ ] 验证`reward_transactions`表完整性（确保所有变动可追溯）

## 配置层
- [ ] 保留`game_config.py`中的`TransactionSource`枚举
- [ ] 删除`lottery_reward_pool`配置（改为数据库动态获取）
- [ ] 删除未使用的`default_rewards`和`default_recipes`配置
- [ ] 保留`top3_lottery_points_amount`（默认100积分）

## Service层
- [ ] `RewardService.top3_lottery()`：移除`stock_quantity > 0`检查
- [ ] `RewardService.redeem_reward()`：移除库存扣减逻辑
- [ ] `TaskCompletionService.complete_task()`：修正返回格式为`reward_earned`（而非`completion_result`）
- [ ] `FocusService`：实现新会话自动关闭旧会话逻辑

## API层
- [ ] 修正`POST /tasks/{id}/complete`响应Schema：
  ```json
  {
    "code": 200,
    "data": {
      "task": {...},
      "reward_earned": {
        "type": "points|reward",
        "transaction_id": "uuid",
        "reward_id": "uuid|null",
        "amount": 10
      }
    }
  }
  ```
- [ ] 验证`POST /focus/sessions` API文档完整性
- [ ] 确保SwaggerUI展示自动关闭会话说明

## 测试
- [ ] 单元测试：验证纯流水记录的库存计算
- [ ] 集成测试：验证Top3抽奖无库存限制
- [ ] 集成测试：验证积分兑换奖品流程
- [ ] 集成测试：验证番茄钟自动关闭会话
- [ ] API测试：验证任务完成响应格式

## 文档
- [ ] 更新`docs/开发目标/TaKeKe_API方案_v4.md`：
  - 明确3条奖品获取路径
  - 补充积分兑换API定义
  - 修正Top3抽奖池规则
  - 补充番茄钟自动关闭说明
- [ ] 更新数据库表结构文档（移除`stock_quantity`）
- [ ] 更新游戏化配置说明文档

## 验收
- [ ] 执行`openspec validate refactor-reward-system-v4 --strict`
- [ ] 所有测试通过
- [ ] v4文档与代码完全对齐
