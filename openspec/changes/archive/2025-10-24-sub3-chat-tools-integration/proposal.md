# 聊天工具：LangGraph集成

## 目标
将所有任务管理工具集成到LangGraph图中，使其可被AI调用。

## 动机
完成工具开发后，需要绑定到LangGraph图才能使用。

## 核心变更
- 修改 `src/domains/chat/graph.py`
- 导入所有7个工具
- 更新ToolNode注册（从1个扩展到8个）
- 更新模型bind_tools
- 验证State传递机制

## 影响范围
- 修改文件：`src/domains/chat/graph.py`
- 修改文件：`src/domains/chat/tools/__init__.py`

## 依赖关系
- ⚠️ **依赖sub2.1, sub2.2, sub2.3, sub2.4**：需要所有7个工具已实现

## 风险与限制
- ToolNode从1个工具扩展到8个，需确保不影响现有工具
