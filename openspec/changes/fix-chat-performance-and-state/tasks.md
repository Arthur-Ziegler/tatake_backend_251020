# 实施任务

## 1. 更新State模型（基础）
- [ ] 修改`models.py:ChatState`增加字段：
  - `session_title: str = "新会话"`
  - `created_at: str` (UTC ISO格式)
- [ ] 移除`user_id`和`session_id`的Optional，改为必填
- [ ] 更新`create_chat_state()`辅助函数

## 2. 修复会话初始化性能
- [ ] `service.py:create_session`调用`_create_session_record_directly`
- [ ] 删除`_create_session_with_langgraph()`方法（line 812-848）
- [ ] `_create_session_record_directly`设置created_at字段
- [ ] 返回固定欢迎消息（不调用LLM）

## 3. 实现Graph单例缓存
- [ ] `service.py:ChatService`新增`_graph`缓存属性
- [ ] 新增`_get_or_create_graph()`方法：
  - 首次调用编译graph
  - 后续返回缓存实例
- [ ] `send_message`使用缓存graph替代临时创建

## 4. 简化工具绑定策略
- [ ] `graph.py:_get_model()`移除模型名判断
- [ ] 总是执行`model.bind_tools(all_tools)`
- [ ] 绑定失败直接raise异常（不吞错误）
- [ ] 日志记录绑定成功的工具数量

## 5. 修复聊天历史重复
- [ ] `service.py:get_chat_history`改用`graph.get_state(config)`
- [ ] 提取`snapshot.values["messages"]`
- [ ] 删除遍历checkpoints逻辑（line 268-306）
- [ ] 应用limit截断（取最新N条）

## 6. 调整API返回格式
- [ ] 保留`schemas.py:ChatMessageItem`结构（兼容性）
- [ ] `get_chat_history`序列化LangChain messages：
  - 保留type、content、id字段
  - 增加tool_calls、additional_kwargs（如存在）
- [ ] `send_message`响应增加timestamp字段

## 7. 测试与验证
- [ ] 单元测试：
  - `test_create_session_直接写checkpoint`
  - `test_graph_缓存单例`
  - `test_get_history_无重复`
  - `test_tool_binding_失败抛异常`
- [ ] 集成测试：
  - 完整对话流程（创建→发送→历史）
  - 工具调用场景（计算器、任务CRUD）
- [ ] 性能测试：
  - 会话创建<100ms
  - 10轮对话无性能退化
- [ ] 数据一致性：
  - Title在所有API一致
  - Created_at正确持久化

## 依赖关系
- 任务1必须先完成（其他任务依赖State定义）
- 任务2-6可并行
- 任务7最后执行
