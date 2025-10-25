# 实施任务：查询工具

## 任务列表

### 1. 创建模块
- [ ] 创建 `src/domains/chat/tools/task_query.py`
- [ ] 导入utils辅助函数

### 2. 实现query_tasks
- [ ] 定义工具签名（status, parent_id, limit, offset, state）
- [ ] UUID转换（parent_id如果提供）
- [ ] 调用TaskService.list_tasks()
- [ ] 返回任务列表和分页信息

### 3. 实现get_task_detail
- [ ] 定义工具签名（task_id, state）
- [ ] UUID转换
- [ ] 调用TaskService.get_task()
- [ ] 返回完整任务信息

### 4. 编写单元测试
- [ ] Mock get_task_service_context
- [ ] 测试query_tasks不同过滤条件
- [ ] 测试分页参数
- [ ] 测试get_task_detail成功和失败
- [ ] 测试权限验证

## 验证
```bash
uv run pytest tests/domains/chat/test_task_query.py -v
```

## 预估工作量
1.5小时
