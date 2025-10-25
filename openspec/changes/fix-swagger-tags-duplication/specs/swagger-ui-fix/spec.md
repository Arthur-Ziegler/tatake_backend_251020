# Swagger UI修复规范

## MODIFIED Requirements

### Requirement: main.py注册router时MUST NOT覆盖tags
main.py的include_router MUST NOT传递tags参数，router的tags SHALL由各领域router内部定义。

#### Scenario: 注册auth_router时不传tags参数
```
GIVEN auth_router在router.py中已定义tags=["认证系统"]
WHEN main.py执行app.include_router(auth_router, prefix=config.api_prefix)
THEN Swagger UI中认证系统分组只显示一次
AND 该分组包含所有auth相关端点
```

---

### Requirement: FastAPI实例MUST包含完整description
FastAPI初始化时description MUST NOT为空字符串，MUST提供有意义的API描述。

#### Scenario: 创建FastAPI实例时提供描述
```
GIVEN 应用名称为TaKeKe API
WHEN 初始化FastAPI(description="TaKeKe API服务，提供认证和任务管理功能")
THEN Swagger UI首页显示该描述
AND description不为空字符串
```

---

### Requirement: openapi.py的setup_openapi MUST NOT定义路由
openapi.py的setup_openapi()函数SHALL只负责OpenAPI配置，MUST NOT使用@app.get()定义路由端点。

#### Scenario: setup_openapi只配置不定义路由
```
GIVEN openapi.py的setup_openapi()函数
WHEN 调用setup_openapi(app)
THEN app不会注册任何新路由
AND 只修改app.openapi函数指向custom_openapi
```

---

## REMOVED Requirements

### Requirement: 删除x-tag-groups和x-changelog扩展
OpenAPI schema MUST NOT包含x-tag-groups、x-changelog等非标准扩展字段。

#### Scenario: OpenAPI schema不包含自定义扩展
```
GIVEN 生成的OpenAPI schema
WHEN 检查schema内容
THEN schema不包含x-tag-groups字段
AND schema不包含x-changelog字段
```

---

### Requirement: 删除冗余的api_prefix条件判断
main.py注册router时MUST直接传递prefix参数，SHALL NOT使用if/else判断api_prefix是否为空。

#### Scenario: 简化router注册代码
```
GIVEN auth_router需要注册
AND config.api_prefix可能为空字符串或有值
WHEN 执行app.include_router(auth_router, prefix=config.api_prefix)
THEN 无论api_prefix为空或非空都正常工作
AND 代码从if/else简化为单行
```

---

### Requirement: 精简OpenAPI examples为核心示例
openapi.py的get_examples() MUST只保留SuccessResponse和ErrorResponse两个示例，SHALL删除TaskCompletionReward和AuthenticationSuccess示例。

#### Scenario: examples只包含两个核心示例
```
GIVEN openapi.py的get_examples()函数
WHEN 返回examples字典
THEN 字典只包含SuccessResponse和ErrorResponse两个key
AND 不包含TaskCompletionReward和AuthenticationSuccess
```
