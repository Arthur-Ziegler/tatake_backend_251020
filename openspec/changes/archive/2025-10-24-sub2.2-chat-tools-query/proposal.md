# 聊天工具：任务查询

## 目标
实现任务的条件查询和详情获取工具。

## 动机
用户需要通过对话查询任务列表和查看任务详情。

## 核心变更
- 新增2个工具：
  1. `query_tasks` - 条件查询（状态、父任务、分页）
  2. `get_task_detail` - 获取任务详情（含子任务）

## 影响范围
- 新增文件：`src/domains/chat/tools/task_query.py`
- 新增测试：`tests/domains/chat/test_task_query.py`

## 依赖关系
- ⚠️ **依赖sub1**：需要utils.py的辅助函数

## 风险与限制
- 查询结果可能很大，需要分页
