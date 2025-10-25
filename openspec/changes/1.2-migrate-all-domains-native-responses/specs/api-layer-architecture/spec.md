# api-layer-architecture Delta

## MODIFIED Requirements

### Requirement: Domain Response Models
所有领域 SHALL使用泛型`UnifiedResponse[T]`模型，删除冗余Wrapper类。

#### Scenario: Task Domain Generic Responses
- **GIVEN** Task领域有7个API端点
- **WHEN** 定义响应模型时
- **THEN** 系统 SHALL使用泛型响应模型：
  ```python
  @router.post("/", response_model=UnifiedResponse[TaskResponse])
  @router.get("/{id}", response_model=UnifiedResponse[TaskResponse])
  @router.get("/", response_model=UnifiedResponse[TaskListResponse])
  ```
- **AND** 系统 SHALL删除Wrapper类：
  - ~~`TaskCreateResponse(UnifiedResponse)`~~
  - ~~`TaskGetResponse(UnifiedResponse)`~~
  - ~~`TaskUpdateResponse(UnifiedResponse)`~~
  - ~~`TaskDeleteResponseWrapper(UnifiedResponse)`~~
  - ~~`TaskListResponseWrapper(UnifiedResponse)`~~
  - ~~`TaskCompleteResponseWrapper(UnifiedResponse)`~~
  - ~~`TaskUncompleteResponseWrapper(UnifiedResponse)`~~

#### Scenario: Chat Domain Generic Responses
- **GIVEN** Chat领域有7个API端点
- **WHEN** 定义响应模型时
- **THEN** 系统 SHALL使用泛型响应模型：
  ```python
  @router.post("/sessions", response_model=UnifiedResponse[ChatSessionResponse])
  @router.get("/sessions", response_model=UnifiedResponse[SessionListResponse])
  ```
- **AND** 系统 SHALL移除所有`response_model=dict`声明
- **AND** 系统 SHALL为每个端点指定明确的数据模型类型

#### Scenario: Focus Domain Generic Responses
- **GIVEN** Focus领域有5个API端点
- **WHEN** 定义响应模型时
- **THEN** 系统 SHALL使用泛型响应模型：
  ```python
  @router.post("/sessions", response_model=UnifiedResponse[FocusSessionResponse])
  @router.get("/sessions", response_model=UnifiedResponse[FocusSessionListResponse])
  ```

#### Scenario: Reward Domain Generic Responses
- **GIVEN** Reward领域有6个API端点
- **WHEN** 定义响应模型时
- **THEN** 系统 SHALL使用泛型响应模型：
  ```python
  @router.get("/materials", response_model=UnifiedResponse[UserMaterialsResponse])
  @router.get("/recipes", response_model=UnifiedResponse[AvailableRecipesResponse])
  ```
- **AND** 系统 SHALL删除Wrapper类：
  - ~~`UserMaterialsResponseWrapper(BaseModel)`~~
  - ~~`AvailableRecipesResponseWrapper(BaseModel)`~~
  - ~~`RedeemRecipeResponseWrapper(BaseModel)`~~

#### Scenario: Top3 Domain Generic Responses
- **GIVEN** Top3领域有2个API端点
- **WHEN** 定义响应模型时
- **THEN** 系统 SHALL使用泛型响应模型：
  ```python
  @router.post("/top3", response_model=UnifiedResponse[Top3Response])
  @router.get("/top3/{date}", response_model=UnifiedResponse[GetTop3Response])
  ```
- **AND** 系统 SHALL移除所有`response_model=dict`声明

#### Scenario: User Domain Generic Responses
- **GIVEN** User领域有4个API端点
- **WHEN** 定义响应模型时
- **THEN** 系统 SHALL使用泛型响应模型：
  ```python
  @router.get("/profile", response_model=UnifiedResponse[UserProfileResponse])
  @router.put("/profile", response_model=UnifiedResponse[UserProfileResponse])
  ```
- **AND** 系统 SHALL移除所有`response_model=dict`声明

### Requirement: Unified Implementation Pattern
所有领域 SHALL遵循统一的端点实现模式。

#### Scenario: Standard Endpoint Pattern
- **GIVEN** 任何领域的任何端点
- **WHEN** 实现端点逻辑时
- **THEN** 函数 SHALL遵循标准模式：
  ```python
  @router.method("/path", response_model=UnifiedResponse[DataModel])
  async def endpoint(...) -> UnifiedResponse[DataModel]:
      result = service.method(...)
      return UnifiedResponse(
          code=200,
          data=DataModel(**result),  # 或已有实例
          message="success"
      )
  ```
- **AND** 函数 SHALL NOT使用`JSONResponse`或辅助函数
- **AND** 异常处理 SHALL使用全局异常处理器，保持格式统一

## REMOVED Requirements

### Requirement: Response Wrapper Classes
~~系统 SHALL为每个端点定义专门的响应Wrapper类。~~

#### Scenario: Removed Wrapper Classes
- **GIVEN** 代码库中存在多个Wrapper类
- **WHEN** 清理冗余代码时
- **THEN** 系统 SHALL删除所有继承自`UnifiedResponse`的Wrapper类
- **AND** 系统 SHALL保留业务数据模型（如`TaskResponse`、`ChatSessionResponse`）
- **AND** OpenAPI文档 SHALL仍然包含所有必要的schema定义

## ADDED Requirements

### Requirement: Cross-Domain Consistency
所有领域 SHALL保持响应格式和实现模式的一致性。

#### Scenario: Response Format Consistency
- **GIVEN** 系统有多个业务领域
- **WHEN** 实现任何API端点时
- **THEN** 所有成功响应 SHALL使用格式：
  ```json
  {
    "code": 200,
    "data": { /* 业务数据 */ },
    "message": "success"
  }
  ```
- **AND** 所有错误响应 SHALL使用相同格式（data为null）
- **AND** 所有端点 SHALL在Swagger UI中正确显示响应schema
- **AND** OpenAPI JSON SHALL包含所有数据模型的完整定义
