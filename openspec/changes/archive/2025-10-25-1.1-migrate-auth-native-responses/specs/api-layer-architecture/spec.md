# api-layer-architecture Delta

## MODIFIED Requirements

### Requirement: Unified Response Format
系统 SHALL使用FastAPI原生Pydantic模型实现统一响应格式，替代JSONResponse辅助函数。

#### Scenario: Generic Response Model
- **GIVEN** 需要类型安全的统一响应格式
- **WHEN** 定义响应模型时
- **THEN** 系统 SHALL使用泛型Pydantic模型：
  ```python
  from typing import Generic, TypeVar

  T = TypeVar('T')

  class UnifiedResponse(BaseModel, Generic[T]):
      code: int
      data: Optional[T] = None
      message: str
  ```
- **AND** 每个端点 SHALL指定具体的响应类型（如`UnifiedResponse[AuthTokenData]`）
- **AND** FastAPI SHALL自动在OpenAPI文档中生成完整的schema定义

#### Scenario: Auth Token Response
- **GIVEN** 认证端点需要返回令牌数据
- **WHEN** 定义Auth响应模型时
- **THEN** 系统 SHALL定义`AuthTokenData` schema：
  ```python
  class AuthTokenData(BaseModel):
      user_id: str
      is_guest: bool
      access_token: str
      refresh_token: str
      token_type: str = "bearer"
      expires_in: int
  ```
- **AND** 所有认证端点 SHALL使用`UnifiedResponse[AuthTokenData]`作为`response_model`

#### Scenario: Native Pydantic Response
- **GIVEN** 路由函数需要返回响应
- **WHEN** 实现端点逻辑时
- **THEN** 函数 SHALL直接返回Pydantic模型实例：
  ```python
  @router.post("/login", response_model=UnifiedResponse[AuthTokenData])
  async def login(...) -> UnifiedResponse[AuthTokenData]:
      result = service.login(...)
      return UnifiedResponse(
          code=200,
          data=AuthTokenData(**result),
          message="success"
      )
  ```
- **AND** 函数 SHALL NOT使用`create_success_response()`或`JSONResponse`
- **AND** FastAPI SHALL自动验证返回值与`response_model`匹配

## REMOVED Requirements

### Requirement: JSONResponse Helper Functions
~~系统 SHALL提供`create_success_response()`辅助函数简化响应创建。~~

#### Scenario: Removed Helper Functions
- **GIVEN** 路由层已迁移到Pydantic模型
- **WHEN** 清理代码时
- **THEN** 系统 SHALL删除`router.py`中的本地辅助函数：
  - ~~`create_success_response(data: Dict) -> JSONResponse`~~
  - ~~`create_error_response(status_code: int, message: str) -> JSONResponse`~~
- **AND** 系统 MAY保留`src/api/responses.py`中的全局辅助函数用于其他领域
