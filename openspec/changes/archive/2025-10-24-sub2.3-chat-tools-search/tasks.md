# 实施任务：搜索工具

## 任务列表

### 1. 创建模块
- [ ] 创建 `src/domains/chat/tools/task_search.py`
- [ ] 导入utils辅助函数

### 2. 实现search_tasks
- [ ] 定义工具签名（query, limit, state）
- [ ] 调用TaskService.list_tasks()获取所有任务（最多limit个）
- [ ] 简化任务信息（id, title, status, priority, 时间字段）
- [ ] 返回任务列表JSON
- [ ] 附加提示信息供LLM分析

### 3. 编写单元测试
- [ ] Mock get_task_service_context
- [ ] 测试search_tasks返回字段正确性
- [ ] 测试limit参数
- [ ] 测试简化逻辑
- [ ] 估算token消耗

## 验证
```bash
uv run pytest tests/domains/chat/test_task_search.py -v
```

## 预估工作量
1小时
