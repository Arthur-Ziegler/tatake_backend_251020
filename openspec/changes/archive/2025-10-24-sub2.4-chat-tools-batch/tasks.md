# 实施任务：批量工具

## 任务列表

### 1. 创建模块
- [ ] 创建 `src/domains/chat/tools/task_batch.py`
- [ ] 导入utils辅助函数

### 2. 实现batch_create_subtasks
- [ ] 定义工具签名（parent_id, subtasks, state）
- [ ] UUID转换（parent_id, user_id）
- [ ] 预验证父任务存在且有权限
- [ ] 循环创建子任务
  - 构造CreateTaskRequest
  - 调用TaskService.create_task()
  - 收集成功和失败结果
- [ ] 返回部分成功结果JSON

### 3. 编写单元测试
- [ ] Mock get_task_service_context
- [ ] 测试全部成功场景
- [ ] 测试部分失败场景（第3个失败）
- [ ] 测试父任务不存在场景
- [ ] 测试返回格式正确性

## 验证
```bash
uv run pytest tests/domains/chat/test_task_batch.py -v
```

## 预估工作量
1.5小时
