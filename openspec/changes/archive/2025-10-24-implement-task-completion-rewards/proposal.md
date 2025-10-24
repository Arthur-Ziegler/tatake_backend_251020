# Proposal: 实现任务完成与奖励系统

## Why
v3 API方案核心功能缺失：任务完成API不存在、奖励逻辑错误（普通30分应2分、Top3固定50应抽奖）、Top3抽奖错误（安慰50应100、奖品池配置错）、防刷错误（24小时应永久）、缺父任务完成度更新和配方合成。

## What Changes
- **完成API**：POST /tasks/{id}/complete和uncomplete
- **奖励修正**：普通2分、Top3抽奖（50%获100分，50%获奖品）
- **防刷升级**：last_claimed_date不为空永久拒绝
- **Top3检测**：is_task_in_today_top3方法
- **递归更新**：父任务completion_percentage自动计算
- **配方合成**：多奖品→新奖品，transaction_group关联

## Impact
- 补齐v3方案核心功能
- 修正所有奖励逻辑
- 实现完整防刷机制
- 需更新v3文档防刷说明
