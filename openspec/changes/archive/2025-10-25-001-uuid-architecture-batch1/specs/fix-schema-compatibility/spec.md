# Fix Pydantic V2 Schema Compatibility

## ADDED Requirements

### Requirement: Custom Enum Schema Generation
TaskStatus、TaskPriority、SessionType MUST支持Pydantic V2的`__get_pydantic_core_schema__`方法。

#### Scenarios:
- **Schema注册**: 修复"got an unexpected keyword argument 'ref_template'"错误
- **JSON Schema**: 生成正确的OpenAPI 3.0兼容schema
- **类型验证**: 支持Pydantic V2的字段验证机制

## ADDED Requirements

### Requirement: Pydantic V2 Core Schema Method
所有自定义枚举类型 MUST实现正确的`__get_pydantic_core_schema__`方法签名。

#### Scenarios:
- **方法签名**: `def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any`
- **Literal Schema**: 使用`core_schema.literal_schema`而非`core_schema.literal_str`
- **Validator Function**: 使用`core_schema.no_info_after_validator_function`

### Requirement: Schema Registry Validation
Schema Registry MUST验证所有自定义类型的兼容性。

#### Scenarios:
- **注册验证**: 检查所有schema是否成功注册到OpenAPI
- **错误报告**: 详细记录注册失败的schema和原因
- **自动修复**: 提供schema兼容性自动检测和修复建议