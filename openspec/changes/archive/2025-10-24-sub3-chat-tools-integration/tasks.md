# 实施任务：LangGraph集成

## 任务列表

### 1. 更新工具导入
- [ ] 修改 `src/domains/chat/tools/__init__.py`
- [ ] 导出所有7个新工具
- [ ] 保留现有工具（sesame_opener）

### 2. 更新graph.py
- [ ] 导入所有新工具
  ```python
  from .tools.task_crud import create_task, update_task, delete_task
  from .tools.task_query import query_tasks, get_task_detail
  from .tools.task_search import search_tasks
  from .tools.task_batch import batch_create_subtasks
  ```
- [ ] 更新ToolNode注册
  ```python
  tool_node = ToolNode([
      sesame_opener,  # 保留
      create_task, update_task, delete_task,
      query_tasks, get_task_detail,
      search_tasks, batch_create_subtasks
  ])
  ```
- [ ] 更新模型bind_tools
  ```python
  model = model.bind_tools([所有8个工具])
  ```

### 3. 验证State传递
- [ ] 确认ChatState.user_id字段存在
- [ ] 测试InjectedState在工具中正确注入
- [ ] 验证user_id从API→Service→Graph→工具的完整链路
- [ ] 添加日志记录user_id传递

### 4. 集成测试
- [ ] 启动服务
- [ ] 发送测试消息
- [ ] 验证LLM能看到所有8个工具
- [ ] 验证工具调用成功

## 验证
```bash
uv run python -c "from src.domains.chat.graph import create_chat_graph; print('✓ Graph OK')"
```

## 预估工作量
1小时
