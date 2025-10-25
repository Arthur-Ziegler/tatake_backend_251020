# 聊天工具：批量创建子任务

## 目标
实现批量创建子任务工具，用于任务拆分场景。

## 动机
用户需要将宏大任务拆分为多个可执行的子任务。

## 核心变更
- 新增1个工具：
  - `batch_create_subtasks` - 批量创建子任务（支持部分成功）

## 影响范围
- 新增文件：`src/domains/chat/tools/task_batch.py`
- 新增测试：`tests/domains/chat/test_task_batch.py`

## 依赖关系
- ⚠️ **依赖sub1**：需要utils.py的辅助函数

## 风险与限制
- 接受部分成功（不修改TaskService）
- 返回详细的成功和失败列表
