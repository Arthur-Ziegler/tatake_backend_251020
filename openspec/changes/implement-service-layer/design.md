# 服务层实现设计文档

## Context
基于现有的数据层（Repository层）实现，需要建立服务层来处理API设计文档中定义的复杂业务逻辑。数据层已经提供了完整的数据访问能力，包括4个Repository类（UserRepository、TaskRepository、FocusRepository、RewardRepository）和丰富的业务方法。服务层将在此基础上构建完整的业务逻辑层，为未来的API实现提供支撑。

## Goals / Non-Goals
### Goals
- **厚服务层实现**：Service层承担完整业务逻辑，包括复杂的事务处理和跨Repository协作
- **异常传播错误处理**：采用自定义异常机制，提供丰富的上下文错误信息用于快速定位问题
- **全面测试覆盖**：实现单元测试和集成测试，确保服务层的质量和可靠性
- **简单依赖注入**：采用构造函数依赖注入，保持代码简洁和可测试性
- **业务逻辑封装**：将API设计文档中的复杂业务规则封装在Service层

### Non-Goals
- **不直接实现API层**：本次变更只实现服务层，不涉及FastAPI路由或API接口
- **不修改数据层**：不修改现有的Repository层和数据模型
- **不引入复杂框架**：避免引入过度复杂的依赖注入容器或框架
- **不处理外部服务**：不涉及外部API调用、消息队列等外部服务集成

## Decisions

### Decision 1: 厚服务层架构
**选择理由**：API设计文档包含大量复杂业务逻辑（如任务完成触发抽奖、专注会话管理、奖励兑换等），这些逻辑涉及多个Repository的协作和复杂的事务处理。

**技术实现**：
- Service类包含完整的业务逻辑
- 跨Repository的业务流程在Service层统一处理
- 复杂事务边界在Service层明确控制

### Decision 2: 异常传播错误处理
**选择理由**：能够提供最详细的错误上下文信息，满足快速定位bug的要求。

**技术实现**：
```python
class BusinessException(Exception):
    def __init__(self, error_code: str, message: str, details: dict = None,
                 user_message: str = None, suggestions: List[str] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.user_message = user_message or message
        self.suggestions = suggestions or []
        super().__init__(message)
```

**错误信息结构**：
- **error_code**: 错误代码，便于程序化处理
- **message**: 技术错误消息，用于开发者调试
- **details**: 详细错误上下文，包含参数、状态等信息
- **user_message**: 用户友好的错误消息
- **suggestions**: 修复建议

### Decision 3: 简单依赖注入
**选择理由**：保持代码简洁，避免过度工程化，便于测试和调试。

**技术实现**：
```python
class UserService:
    def __init__(self, user_repo: UserRepository, task_repo: TaskRepository,
                 reward_repo: RewardRepository):
        self.user_repo = user_repo
        self.task_repo = task_repo
        self.reward_repo = reward_repo

def create_user_service(session: Session) -> UserService:
    return UserService(
        UserRepository(session),
        TaskRepository(session),
        RewardRepository(session)
    )
```

### Decision 4: 事务管理策略
**选择理由**：Service层通过Repository接口操作数据库，Repository层已经提供了事务管理能力。

**技术实现**：
- 简单操作：Repository自动处理事务
- 复杂操作：Service层通过session上下文控制事务边界
- 禁止直接访问数据库：所有数据库操作必须通过Repository层

## Risks / Trade-offs

### Risk 1: Service层可能过重
**风险**：Service类可能变得复杂，包含过多业务逻辑
**缓解措施**：
- 按业务域拆分Service类（用户、任务、专注、奖励、统计、AI对话）
- 保持单一职责原则，每个Service专注于一个业务域
- 提取公共逻辑到工具类或基类

### Risk 2: 异常传播可能复杂
**风险**：异常传播链可能难以追踪和调试
**缓解措施**：
- 提供详细的异常上下文信息
- 使用结构化日志记录异常
- 在测试中验证异常传播路径

### Risk 3: 依赖注入可能产生代码重复
**风险**：在不同地方创建Service实例可能产生重复代码
**缓解措施**：
- 提供Service工厂方法
- 在测试中使用依赖注入容器
- 保持依赖关系简单明了

## Migration Plan

### 阶段1：基础架构搭建
1. 创建`src/services/`目录结构
2. 实现Service基类和异常类
3. 配置测试环境和工具

### 阶段2：核心Service实现
1. 实现AuthService（用户认证相关业务）
2. 实现UserService（用户管理业务）
3. 实现TaskService（任务管理业务）
4. 实现FocusService（专注会话业务）

### 阶段3：扩展Service实现
1. 实现RewardService（奖励系统业务）
2. 实现StatisticsService（统计分析业务）
3. 实现ChatService（AI对话业务）

### 阶段4：测试和优化
1. 编写全面的单元测试
2. 编写集成测试
3. 性能优化和代码重构

## Open Questions

### 1. Service生命周期管理
**问题**：Service实例是每次请求创建还是可以复用？
**选项**：
- A. 每次请求创建：无状态，简单直接
- B. 依赖作用域复用：有状态，需要管理生命周期

**建议**：优先选择每次请求创建，后续根据性能需求考虑复用。

### 2. 异步处理策略
**问题**：某些操作（如发送通知、生成报表）是否需要异步处理？
**选项**：
- A. 同步处理：简单直接，便于测试
- B. 异步处理：性能更好，适合耗时操作

**建议**：第一阶段采用同步处理，后续根据需求引入异步处理。

### 3. Service测试策略
**问题**：如何平衡单元测试和集成测试？
**选项**：
- A. 单元测试为主：快速反馈，依赖Mock
- B. 集成测试为主：真实环境测试，可靠性高
- C. 混合策略：核心业务集成测试，边缘情况单元测试

**建议**：采用混合策略，确保核心业务逻辑的可靠性。