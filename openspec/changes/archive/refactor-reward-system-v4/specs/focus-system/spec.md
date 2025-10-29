# focus-system Specification

## ADDED Requirements

### Requirement: 自动关闭未完成会话
系统 MUST 在创建新会话时自动关闭用户的旧会话，确保用户同时只有1个进行中会话。

#### Scenario: 开始新会话时自动关闭旧会话
```
GIVEN 用户已有一个进行中的专注会话（end_time = NULL）
WHEN 用户开始新的专注会话
THEN 旧会话的end_time设置为当前时间
AND 新会话正常创建
AND 数据库中只有1个进行中会话
```

#### Scenario: 无旧会话时正常创建
```
GIVEN 用户无进行中的会话
WHEN 用户开始新会话
THEN 直接创建新会话
AND 不执行关闭逻辑
```

#### Scenario: 暂停会话也触发自动关闭
```
GIVEN 用户处于专注会话中
WHEN 用户请求暂停（session_type=pause）
THEN 当前专注会话被关闭
AND 创建新的暂停会话
AND 专注时长可累计（focus-pause-focus合并计算）
```

### Requirement: API文档完整性
SwaggerUI MUST 展示自动关闭会话的说明。

#### Scenario: SwaggerUI展示自动关闭说明
```
GIVEN 访问/docs SwaggerUI
WHEN 查看POST /focus/sessions API
THEN 描述中包含"自动终止前一个未完成的session"说明
AND 请求参数包含session_type枚举值
AND 响应示例展示完整会话对象
```

## MODIFIED Requirements

### Requirement: 会话创建逻辑
系统 SHALL 在创建会话前先清理用户的旧会话。

#### Scenario: 会话创建完整流程
```
GIVEN 用户请求创建新会话
WHEN 执行会话创建
THEN 步骤1：查询用户是否有进行中会话
AND 步骤2：如有，设置旧会话的end_time
AND 步骤3：创建新会话（end_time = NULL）
AND 步骤4：返回新会话详情和当前时间
```
