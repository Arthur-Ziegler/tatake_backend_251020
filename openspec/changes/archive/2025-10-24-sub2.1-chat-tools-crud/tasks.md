# 实施任务：CRUD工具

## 任务列表

### 1. 创建模块
- [ ] 创建 `src/domains/chat/tools/task_crud.py`
- [ ] 导入utils辅助函数

### 2. 实现create_task
- [ ] 定义工具签名（8个参数+state）
- [ ] UUID转换（user_id, parent_id）
- [ ] datetime解析（3个时间字段）
- [ ] 构造CreateTaskRequest
- [ ] 调用TaskService.create_task()
- [ ] 返回标准JSON

### 3. 实现update_task
- [ ] 定义工具签名（6个参数+state）
- [ ] UUID转换（task_id, user_id）
- [ ] datetime解析（due_date）
- [ ] 构造UpdateTaskRequest
- [ ] 调用TaskService.update_task_with_tree_structure()
- [ ] 返回标准JSON

### 4. 实现delete_task
- [ ] 定义工具签名（task_id+state）
- [ ] UUID转换
- [ ] 调用TaskService.delete_task()
- [ ] 返回删除确认

### 5. 编写单元测试
- [ ] Mock get_task_service_context
- [ ] Mock InjectedState
- [ ] 测试create_task成功和失败场景
- [ ] 测试update_task成功和失败场景
- [ ] 测试delete_task成功和失败场景
- [ ] 测试UUID/datetime解析错误

## 验证
```bash
uv run pytest tests/domains/chat/test_task_crud.py -v
```

## 预估工作量
2小时
