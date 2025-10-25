# 设计文档

## 技术决策

### 决策1：使用泛型而非继承
**原因**：
- ✅ 单一`UnifiedResponse[T]`类，符合DRY原则
- ✅ FastAPI完美支持泛型，自动推断类型
- ✅ 避免为每个响应创建Wrapper类的冗余
- ❌ 略微增加代码复杂度（需要导入Generic和TypeVar）

**替代方案**：为每个端点创建专门Wrapper类（被拒绝，过于冗余）

### 决策2：保留统一响应格式
**原因**：
- ✅ 前端无需改造，接口向后兼容
- ✅ 错误响应格式保持一致
- ✅ 符合项目既定架构设计
- ⚠️ 需要确保`response_model`正确设置

### 决策3：Service层继续返回dict
**原因**：
- ✅ 最小化改动范围，降低风险
- ✅ Service层不关心序列化格式
- ✅ 路由层负责转换为Pydantic模型
- ⚠️ 路由层需要手动构造AuthTokenData

### 决策4：分领域迁移而非一次性
**原因**：
- ✅ 降低单次变更风险
- ✅ 每个提案可独立验证和回滚
- ✅ 逐步积累经验，优化后续提案
- ❌ 多个提案增加管理成本

## 技术细节

### 泛型实现
```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T')

class UnifiedResponse(BaseModel, Generic[T]):
    code: int
    data: Optional[T] = None
    message: str

    model_config = ConfigDict(from_attributes=True)
```

### 端点改造模式
**改造前**：
```python
@router.post("/login", response_model=UnifiedResponse)
async def login(...) -> JSONResponse:
    result = auth_service.wechat_login(...)
    return create_success_response(result)
```

**改造后**：
```python
@router.post("/login", response_model=UnifiedResponse[AuthTokenData])
async def login(...) -> UnifiedResponse[AuthTokenData]:
    result = auth_service.wechat_login(...)
    return UnifiedResponse(
        code=200,
        data=AuthTokenData(**result),
        message="success"
    )
```

### 异常处理保持不变
继续使用全局异常处理器，确保错误响应也是`{code, data, message}`格式。

## 风险与缓解

### 风险1：Pydantic验证失败
**场景**：Service返回的dict字段不匹配AuthTokenData
**缓解**：
1. 仔细对比Service返回值和Schema定义
2. 添加单元测试验证转换逻辑
3. 使用`model_validate()`而非`**dict`展开

### 风险2：破坏现有测试
**场景**：测试依赖JSONResponse的特定行为
**缓解**：
1. 运行测试套件发现问题
2. 更新测试断言为Pydantic模型检查
3. 保持响应JSON格式不变，只改内部实现

### 风险3：性能下降
**场景**：Pydantic验证增加开销
**缓解**：
1. Pydantic v2性能优异，影响可忽略
2. 如有问题，可使用`model_construct()`跳过验证
3. 生产环境监控响应时间

## 测试策略
1. **单元测试**：验证AuthTokenData schema定义
2. **集成测试**：验证每个端点响应格式
3. **手动测试**：检查Swagger UI显示效果
4. **回归测试**：确保现有测试全部通过
