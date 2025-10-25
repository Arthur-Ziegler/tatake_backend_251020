# 迁移Auth领域到FastAPI原生响应模型

## Why
当前Auth API使用`create_success_response()`返回JSONResponse，导致：
- Swagger UI无法识别响应schema，显示为空
- OpenAPI文档缺失关键数据结构定义
- 前端开发者无法从文档中了解响应格式
- 违反FastAPI最佳实践，未充分利用类型系统

## What Changes
将Auth领域5个API端点从JSONResponse迁移到FastAPI原生Pydantic响应模型：

## 方案
**A2+B2+D1组合**：保留`{code, data, message}`统一格式 + 自定义异常处理 + 泛型响应模型

### 核心改动
1. **泛型响应模型**：改造`UnifiedResponse`为`Generic[T]`，支持类型参数
2. **数据Schema定义**：新建`AuthTokenData`承载业务数据
3. **路由返回类型**：所有端点返回`UnifiedResponse[AuthTokenData]`实例
4. **移除辅助函数**：删除`create_success_response()`，直接构造Pydantic模型

### 技术细节
```python
# 泛型响应模型
class UnifiedResponse(BaseModel, Generic[T]):
    code: int
    data: Optional[T] = None
    message: str

# Auth业务数据
class AuthTokenData(BaseModel):
    user_id: str
    is_guest: bool
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

# 路由使用
@router.post("/login", response_model=UnifiedResponse[AuthTokenData])
async def login(...) -> UnifiedResponse[AuthTokenData]:
    return UnifiedResponse(
        code=200,
        data=AuthTokenData(...),
        message="success"
    )
```

## 影响范围
- **Schema文件**：`src/domains/auth/schemas.py` - 新增泛型和AuthTokenData
- **路由文件**：`src/domains/auth/router.py` - 改造5个端点
- **Service层**：保持不变，继续返回dict
- **前端接口**：响应格式完全不变

## 端点列表
1. `POST /auth/guest/init` - 游客初始化
2. `POST /auth/register` - 微信注册
3. `POST /auth/login` - 微信登录
4. `POST /auth/guest/upgrade` - 游客升级
5. `POST /auth/refresh` - 令牌刷新

## 验证标准
- [ ] Swagger UI正确显示所有响应schema
- [ ] OpenAPI JSON包含`AuthTokenData`定义
- [ ] 5个端点的响应示例完整显示
- [ ] 现有测试全部通过
- [ ] 前端调用无需改动

## 后续提案
- 提案1.2：迁移Task领域（7个端点）
- 提案1.3：迁移Chat领域（7个端点）
- 提案1.4：迁移Focus领域（3个端点）
- 提案1.5：迁移Reward领域（6个端点）
