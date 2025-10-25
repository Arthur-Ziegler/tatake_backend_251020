# 聊天工具：任务CRUD

## 目标
实现任务的创建、更新、删除工具，支持通过自然语言管理任务。

## 动机
用户需要通过对话创建、修改、删除任务。

## 核心变更
- 新增3个工具：
  1. `create_task` - 创建任务（支持全字段）
  2. `update_task` - 更新任务
  3. `delete_task` - 删除任务（软删除）

## 影响范围
- 新增文件：`src/domains/chat/tools/task_crud.py`
- 新增测试：`tests/domains/chat/test_task_crud.py`

## 依赖关系
- ⚠️ **依赖sub1**：需要utils.py的辅助函数

## 风险与限制
- datetime字段需要ISO格式字符串
