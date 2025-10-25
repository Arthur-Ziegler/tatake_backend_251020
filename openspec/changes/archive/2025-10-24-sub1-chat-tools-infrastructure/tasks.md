# 实施任务：基础设施

## 任务列表

### 1. 创建utils模块
- [x] 创建 `src/domains/chat/tools/utils.py`
- [x] 添加模块文档字符串

### 2. 实现Session管理
- [x] 实现 `get_task_service_context()`
  - 使用 `get_engine()` 获取引擎
  - 创建Session
  - 注入TaskService和PointsService
  - 实现异常处理和回滚
  - 确保Session正确关闭

### 3. 实现UUID转换
- [x] 实现 `safe_uuid_convert()`
  - 处理None值
  - 捕获ValueError
  - 返回友好错误信息

### 4. 实现日期解析
- [x] 实现 `parse_datetime()`
  - 支持Z时区标记
  - 支持ISO格式
  - 提供详细错误信息

### 5. 实现响应格式化
- [x] 实现 `_success_response()`
- [x] 实现 `_error_response()`

### 6. 编写单元测试
- [x] 创建 `tests/domains/chat/test_task_tools_utils.py`
- [x] 测试Session管理（创建和关闭）
- [x] 测试UUID转换（有效、无效、None）
- [x] 测试日期解析（多种格式）
- [x] 测试响应格式化

## 验证
```bash
uv run pytest tests/domains/chat/test_task_tools_utils.py -v
```

## 预估工作量
1.5小时
