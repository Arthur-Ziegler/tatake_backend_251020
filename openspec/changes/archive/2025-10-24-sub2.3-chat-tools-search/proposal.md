# 聊天工具：任务搜索

## 目标
实现任务搜索工具，返回简化任务列表供LLM分析匹配。

## 动机
用户需要通过自然语言描述搜索相关任务。

## 核心变更
- 新增1个工具：
  - `search_tasks` - 返回所有任务供LLM分析（方案D）

## 影响范围
- 新增文件：`src/domains/chat/tools/task_search.py`
- 新增测试：`tests/domains/chat/test_task_search.py`

## 依赖关系
- ⚠️ **依赖sub1**：需要utils.py的辅助函数

## 风险与限制
- Token消耗高（100任务约8000 tokens）
- MVP阶段可接受，未来升级向量搜索
