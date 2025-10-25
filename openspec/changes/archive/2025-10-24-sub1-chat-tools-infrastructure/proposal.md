# 聊天工具基础设施

## 目标
创建任务管理工具的基础设施，提供Session管理、UUID转换、日期解析等通用功能。

## 动机
后续所有工具都需要这些基础功能，必须先完成。

## 核心变更
- 创建 `src/domains/chat/tools/utils.py`
- 实现5个辅助函数：
  1. `get_task_service_context()` - Session管理
  2. `safe_uuid_convert()` - UUID转换
  3. `parse_datetime()` - 日期解析
  4. `_success_response()` - 成功响应
  5. `_error_response()` - 错误响应

## 影响范围
- 新增文件：`src/domains/chat/tools/utils.py`
- 新增测试：`tests/domains/chat/test_task_tools_utils.py`

## 依赖关系
- ✅ 无依赖，可立即执行

## 风险与限制
- 无
