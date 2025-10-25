# chat-tools-utils Specification

## ADDED Requirements

### Requirement: Task Service Context Management
系统 SHALL提供TaskService上下文管理器，供工具使用。

#### Scenario: Get Task Service Context
- **GIVEN** 工具需要访问TaskService
- **WHEN** 使用get_task_service_context()时
- **THEN** 系统 SHALL创建新的Session
- **AND** 注入TaskService和PointsService
- **AND** 使用yield返回task_service
- **AND** 执行完成后关闭Session
- **AND** 异常时回滚Session

### Requirement: UUID Conversion Utility
系统 SHALL提供UUID安全转换功能。

#### Scenario: Convert Valid UUID String
- **GIVEN** UUID字符串"123e4567-e89b-12d3-a456-426614174000"
- **WHEN** 调用safe_uuid_convert()时
- **THEN** 系统 SHALL返回UUID对象

#### Scenario: Handle None Value
- **GIVEN** None值
- **WHEN** 调用safe_uuid_convert()时
- **THEN** 系统 SHALL返回None

#### Scenario: Handle Invalid UUID
- **GIVEN** 无效UUID字符串"invalid"
- **WHEN** 调用safe_uuid_convert()时
- **THEN** 系统 SHALL抛出ValueError
- **AND** 错误信息包含"无效的任务ID格式"

### Requirement: DateTime Parsing Utility
系统 SHALL提供ISO日期解析功能。

#### Scenario: Parse ISO DateTime with Z
- **GIVEN** 日期字符串"2024-12-31T23:59:59Z"
- **WHEN** 调用parse_datetime()时
- **THEN** 系统 SHALL返回datetime对象
- **AND** 时区为UTC

#### Scenario: Parse ISO DateTime with Offset
- **GIVEN** 日期字符串"2024-12-31T23:59:59+08:00"
- **WHEN** 调用parse_datetime()时
- **THEN** 系统 SHALL返回datetime对象

#### Scenario: Handle None DateTime
- **GIVEN** None值
- **WHEN** 调用parse_datetime()时
- **THEN** 系统 SHALL返回None

#### Scenario: Handle Invalid DateTime
- **GIVEN** 无效日期字符串"invalid-date"
- **WHEN** 调用parse_datetime()时
- **THEN** 系统 SHALL抛出ValueError
- **AND** 错误信息包含日期格式要求

### Requirement: Response Formatting Utilities
系统 SHALL提供统一的响应格式化功能。

#### Scenario: Format Success Response
- **GIVEN** 成功数据
- **WHEN** 调用_success_response()时
- **THEN** 系统 SHALL返回JSON字符串
- **AND** 包含{"success": true, "data": {...}}

#### Scenario: Format Error Response
- **GIVEN** 错误信息
- **WHEN** 调用_error_response()时
- **THEN** 系统 SHALL返回JSON字符串
- **AND** 包含{"success": false, "error": "..."}
