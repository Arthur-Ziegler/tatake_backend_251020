# implement-api-business-layer 设计文档

## 概述

本文档详细说明第二阶段API业务层实现的技术设计，包括架构决策、数据库设计、LangGraph集成方案、Mock服务策略等关键技术设计。

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Applications                   │
│                (Web, Mobile, WeChat Mini)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    API Layer (FastAPI)                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │   Auth      │ │    Tasks    │ │       AI Chat           │ │
│  │ Middleware  │ │ Middleware  │ │     Middleware          │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │    CORS     │ │    Rate     │ │       Security           │ │
│  │ Middleware  │ │  Middleware  │ │     Middleware          │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Service Layer                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ AuthService │ │ TaskService │ │      ChatService        │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │UserService  │ │FocusService │ │    RewardService        │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Repository Layer                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │UserRepo     │ │  TaskRepo   │ │      ChatRepo           │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Database Layer                             │
│                SQLite + Async SQLAlchemy                   │
└─────────────────────────────────────────────────────────────┘

外部服务集成:
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Mock SMS      │ │   Mock WeChat   │ │   Real LLM API   │
│   Service       │ │   Service       │ │   (via LangGraph) │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 分层架构原则

1. **API层**: 处理HTTP请求/响应，参数验证，权限控制
2. **Service层**: 业务逻辑处理，事务管理，业务规则验证
3. **Repository层**: 数据访问抽象，数据库操作封装
4. **Database层**: 数据持久化，SQLite数据库

### 核心设计模式

1. **ServiceFactory模式**: 统一依赖注入管理
2. **Repository模式**: 数据访问层抽象
3. **Strategy模式**: 多种认证方式支持
4. **Observer模式**: 事件驱动的业务逻辑
5. **State模式**: LangGraph对话状态管理

## 数据库设计

### Redis移除和替代方案

#### 原Redis功能映射到SQLite

| 原Redis功能 | SQLite替代方案 | 表设计 |
|-------------|----------------|--------|
| 验证码存储 | sms_verification表 | 短期验证码存储 |
| 令牌黑名单 | token_blacklist表 | JWT失效管理 |
| 用户会话 | JWT令牌本身 | 无状态认证 |
| 缓存数据 | 应用内存缓存 | 临时数据缓存 |

### 新增数据表设计

#### 1. token_blacklist表 - JWT令牌黑名单

```sql
CREATE TABLE token_blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id VARCHAR(255) NOT NULL UNIQUE,
    user_id UUID NOT NULL,
    token_type VARCHAR(50) NOT NULL, -- 'access' or 'refresh'
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    blacklisted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reason VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token_id (token_id),
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at)
);
```

#### 2. sms_verification表 - 短信验证码

```sql
CREATE TABLE sms_verification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone VARCHAR(20) NOT NULL,
    code VARCHAR(10) NOT NULL,
    user_id UUID,
    verification_type VARCHAR(50) NOT NULL, -- 'login', 'register', 'reset_password'
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 5,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_phone_code (phone, code),
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at)
);
```

#### 3. chat_memory表 - 长期对话记忆

```sql
CREATE TABLE chat_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id UUID NOT NULL,
    user_id UUID NOT NULL,
    memory_type VARCHAR(50) NOT NULL, -- 'context', 'preference', 'summary'
    memory_key VARCHAR(255) NOT NULL,
    memory_value TEXT NOT NULL,
    memory_metadata JSONB,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_memory_type (memory_type),
    INDEX idx_memory_key (memory_key),
    UNIQUE(session_id, memory_type, memory_key)
);
```

### 现有表结构优化

#### 1. users表优化

```sql
-- 添加JWT相关字段
ALTER TABLE users ADD COLUMN jwt_version INTEGER DEFAULT 1;
ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN login_count INTEGER DEFAULT 0;

-- 添加积分和等级相关字段
ALTER TABLE users ADD COLUMN total_points INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN available_points INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1;
ALTER TABLE users ADD COLUMN experience_points INTEGER DEFAULT 0;
```

#### 2. tasks表优化

```sql
-- 添加Top3相关字段
ALTER TABLE tasks ADD COLUMN is_top3 BOOLEAN DEFAULT FALSE;
ALTER TABLE tasks ADD COLUMN top3_date DATE;

-- 添加任务完成奖励字段
ALTER TABLE tasks ADD COLUMN completion_points INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN completion_fragments JSONB; -- 完成获得的碎片
```

#### 3. focus_sessions表优化

```sql
-- 添加专注奖励字段
ALTER TABLE focus_sessions ADD COLUMN completion_points INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN satisfaction_score INTEGER; -- 1-5分满意度
```

## LangGraph集成设计

### LangGraph架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph State Machine                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐
│   Supervisor  │ │Task Agent  │ │Chat Agent │
│    Node       │ │   Node     │ │   Node     │
└───────┬──────┘ └─────┬─────┘ └─────┬─────┘
        │             │             │
        │      ┌──────▼──────┐      │
        │      │ Task Tools   │      │
        │      │   - Query    │      │
        │      │   - Create   │      │
        │      │   - Update   │      │
        │      │   - Delete   │      │
        │      └──────┬──────┘      │
        │             │             │
        └─────────────┼─────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Chat State Management                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │   Messages  │ │   Context   │ │      Memory             │ │
│  │   History   │ │  Data       │ │     Storage             │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### ChatState状态定义

```python
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from langchain_core.messages import BaseMessage

@dataclass
class ChatState:
    """LangGraph聊天状态定义"""

    # 消息历史
    messages: List[BaseMessage] = field(default_factory=list)

    # 用户上下文
    user_context: Dict[str, Any] = field(default_factory=dict)

    # 对话元数据
    conversation_metadata: Dict[str, Any] = field(default_factory=dict)

    # 当前意图识别
    current_intent: Optional[str] = None

    # 需要执行的动作
    required_actions: List[str] = field(default_factory=list)

    # 处理状态
    processing_state: str = "idle"  # idle, processing, completed, error

    # 错误信息
    error_info: Optional[Dict[str, Any]] = None

    # 工具调用结果
    tool_results: Dict[str, Any] = field(default_factory=dict)

    # 长期记忆
    long_term_memory: Dict[str, Any] = field(default_factory=dict)
```

### Supervisor-Agent流程设计

```python
from typing import Literal
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command

def supervisor_node(state: ChatState) -> Command[Literal["task_agent", "chat_agent", END]]:
    """
    Supervisor节点：根据用户意图决定路由到哪个Agent
    """
    # 分析用户消息意图
    last_message = state.messages[-1] if state.messages else None

    if not last_message:
        return Command(goto="chat_agent")

    message_content = last_message.content.lower()

    # 任务相关关键词检测
    task_keywords = ["任务", "task", "todo", "完成", "创建", "删除", "更新"]
    if any(keyword in message_content for keyword in task_keywords):
        return Command(
            goto="task_agent",
            update={"current_intent": "task_management"}
        )

    # 默认路由到聊天Agent
    return Command(
        goto="chat_agent",
        update={"current_intent": "general_chat"}
    )

def task_agent_node(state: ChatState) -> Command[Literal["supervisor"]]:
    """
    任务Agent：处理任务管理相关请求
    """
    try:
        # 调用任务工具
        tool_results = execute_task_tools(state)

        return Command(
            goto="supervisor",
            update={
                "tool_results": tool_results,
                "processing_state": "completed"
            }
        )
    except Exception as e:
        return Command(
            goto="supervisor",
            update={
                "error_info": {"error": str(e)},
                "processing_state": "error"
            }
        )

def chat_agent_node(state: ChatState) -> Command[Literal["supervisor"]]:
    """
    聊天Agent：处理一般聊天请求
    """
    try:
        # 调用LLM生成回复
        llm_response = generate_chat_response(state)

        # 添加AI回复到消息历史
        ai_message = AIMessage(content=llm_response)

        return Command(
            goto="supervisor",
            update={
                "messages": [ai_message],
                "processing_state": "completed"
            }
        )
    except Exception as e:
        return Command(
            goto="supervisor",
            update={
                "error_info": {"error": str(e)},
                "processing_state": "error"
            }
        )
```

### 工具调用设计

#### 任务管理工具

```python
from langchain_core.tools import tool
from typing import Dict, Any, List

@tool
def query_tasks(query: str, user_id: str) -> Dict[str, Any]:
    """
    查询用户任务

    Args:
        query: 查询条件
        user_id: 用户ID

    Returns:
        任务查询结果
    """
    # 实现任务查询逻辑
    pass

@tool
def create_task(title: str, description: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """
    创建新任务

    Args:
        title: 任务标题
        description: 任务描述
        user_id: 用户ID
        **kwargs: 其他任务属性

    Returns:
        创建的任务信息
    """
    # 实现任务创建逻辑
    pass

@tool
def update_task(task_id: str, user_id: str, **updates) -> Dict[str, Any]:
    """
    更新任务

    Args:
        task_id: 任务ID
        user_id: 用户ID
        **updates: 更新的字段

    Returns:
        更新后的任务信息
    """
    # 实现任务更新逻辑
    pass

@tool
def complete_task(task_id: str, user_id: str, satisfaction: int = None) -> Dict[str, Any]:
    """
    完成任务

    Args:
        task_id: 任务ID
        user_id: 用户ID
        satisfaction: 满意度评分(1-5)

    Returns:
        完成结果和奖励信息
    """
    # 实现任务完成逻辑
    pass
```

### 长期记忆系统设计

#### 记忆类型定义

```python
from enum import Enum

class MemoryType(Enum):
    """记忆类型枚举"""
    CONTEXT = "context"        # 上下文记忆
    PREFERENCE = "preference"  # 用户偏好
    SUMMARY = "summary"        # 对话摘要
    REFERENCE = "reference"    # 参考信息
    HABIT = "habit"           # 用户习惯

@dataclass
class ChatMemory:
    """聊天记忆数据结构"""
    session_id: str
    user_id: str
    memory_type: MemoryType
    memory_key: str
    memory_value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
```

#### 记忆管理器

```python
class ChatMemoryManager:
    """聊天记忆管理器"""

    def __init__(self, db_session):
        self.db_session = db_session

    async def store_memory(
        self,
        session_id: str,
        user_id: str,
        memory_type: MemoryType,
        memory_key: str,
        memory_value: Any,
        **kwargs
    ) -> None:
        """存储记忆"""
        # 实现记忆存储逻辑
        pass

    async def retrieve_memory(
        self,
        session_id: str,
        memory_type: MemoryType,
        memory_key: str = None
    ) -> List[ChatMemory]:
        """检索记忆"""
        # 实现记忆检索逻辑
        pass

    async def update_memory(
        self,
        session_id: str,
        memory_type: MemoryType,
        memory_key: str,
        memory_value: Any
    ) -> None:
        """更新记忆"""
        # 实现记忆更新逻辑
        pass

    async def cleanup_expired_memories(self) -> None:
        """清理过期记忆"""
        # 实现记忆清理逻辑
        pass
```

## Mock服务设计

### Mock SMS服务

```python
class MockSMSService:
    """模拟短信服务"""

    def __init__(self):
        self.sent_codes = {}  # 存储已发送的验证码
        self.send_history = []  # 发送历史

    async def send_verification_code(
        self,
        phone: str,
        code: str,
        template: str = None
    ) -> Dict[str, Any]:
        """
        发送验证码（模拟）

        Args:
            phone: 手机号
            code: 验证码
            template: 短信模板

        Returns:
            发送结果

        Note:
            这是一个Mock服务，实际使用时需要替换为真实的短信服务
            替换方式：将 MockSMSService 替换为 AliyunSMSService 或其他真实服务
            需要修改的地方：
            1. 导入真实的SMS SDK
            2. 替换send_verification_code方法实现
            3. 添加错误处理和重试机制
        """
        # 模拟发送延迟
        await asyncio.sleep(0.1)

        # 记录发送历史
        send_record = {
            "phone": phone,
            "code": code,
            "template": template,
            "sent_at": datetime.now(timezone.utc),
            "status": "success",
            "message_id": f"mock_{uuid.uuid4().hex[:8]}"
        }

        self.send_history.append(send_record)
        self.sent_codes[phone] = {
            "code": code,
            "sent_at": send_record["sent_at"],
            "message_id": send_record["message_id"]
        }

        return {
            "success": True,
            "message_id": send_record["message_id"],
            "status": "sent",
            "mock_service": True
        }

    async def verify_code(
        self,
        phone: str,
        code: str
    ) -> bool:
        """验证验证码（模拟）"""
        stored = self.sent_codes.get(phone)
        if not stored:
            return False

        # 模拟5分钟有效期
        if datetime.now(timezone.utc) - stored["sent_at"] > timedelta(minutes=5):
            del self.sent_codes[phone]
            return False

        return stored["code"] == code
```

### Mock WeChat服务

```python
class MockWeChatService:
    """模拟微信服务"""

    def __init__(self):
        self.mock_users = {}  # 模拟微信用户数据库

    async def get_user_info(self, code: str) -> Dict[str, Any]:
        """
        通过微信授权码获取用户信息（模拟）

        Args:
            code: 微信授权码

        Returns:
            用户信息

        Note:
            这是一个Mock服务，实际使用时需要替换为真实的微信API
            替换方式：
            1. 导入微信SDK (wechatpy或类似库)
            2. 配置微信AppID和AppSecret
            3. 实现真实的OAuth2.0流程
            4. 处理微信API错误和限流
        """
        # 模拟API调用延迟
        await asyncio.sleep(0.2)

        # 生成模拟用户数据
        mock_user_id = f"wx_mock_{uuid.uuid4().hex[:12]}"
        mock_data = {
            "openid": mock_user_id,
            "nickname": f"微信用户_{mock_user_id[-6:]}",
            "headimgurl": "https://example.com/avatar.jpg",
            "unionid": f"union_{mock_user_id}",
            "sex": 1,
            "province": "广东",
            "city": "深圳",
            "country": "中国"
        }

        self.mock_users[mock_user_id] = mock_data

        return {
            "success": True,
            "user_info": mock_data,
            "mock_service": True
        }
```

## API Schema设计

### Pydantic Schema目录结构

```
src/api/schemas/
├── __init__.py
├── auth/
│   ├── __init__.py
│   ├── requests.py      # 认证请求模型
│   ├── responses.py     # 认证响应模型
│   └── common.py        # 认证通用模型
├── tasks/
│   ├── __init__.py
│   ├── requests.py      # 任务请求模型
│   ├── responses.py     # 任务响应模型
│   └── common.py        # 任务通用模型
├── focus/
│   ├── __init__.py
│   ├── requests.py      # 专注请求模型
│   ├── responses.py     # 专注响应模型
│   └── common.py        # 专注通用模型
├── rewards/
│   ├── __init__.py
│   ├── requests.py      # 奖励请求模型
│   ├── responses.py     # 奖励响应模型
│   └── common.py        # 奖励通用模型
├── chat/
│   ├── __init__.py
│   ├── requests.py      # 对话请求模型
│   ├── responses.py     # 对话响应模型
│   └── common.py        # 对话通用模型
├── statistics/
│   ├── __init__.py
│   ├── requests.py      # 统计请求模型
│   ├── responses.py     # 统计响应模型
│   └── common.py        # 统计通用模型
└── user/
    ├── __init__.py
    ├── requests.py      # 用户请求模型
    ├── responses.py     # 用户响应模型
    └── common.py        # 用户通用模型
```

### Schema设计示例

#### 认证Schema示例

```python
# src/api/schemas/auth/requests.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from enum import Enum

class LoginMethod(str, Enum):
    PASSWORD = "password"
    SMS_CODE = "sms_code"
    WECHAT = "wechat"

class GuestInitRequest(BaseModel):
    """游客初始化请求"""
    device_id: Optional[str] = Field(None, description="设备ID")
    device_type: Optional[str] = Field(None, description="设备类型")
    app_version: Optional[str] = Field(None, description="应用版本")

class GuestUpgradeRequest(BaseModel):
    """游客升级请求"""
    upgrade_method: LoginMethod = Field(..., description="升级方式")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[str] = Field(None, description="邮箱")
    password: Optional[str] = Field(None, description="密码")
    sms_code: Optional[str] = Field(None, description="短信验证码")
    wechat_code: Optional[str] = Field(None, description="微信授权码")

    @validator('sms_code')
    def validate_sms_code(cls, v, values):
        if values.get('upgrade_method') == LoginMethod.SMS_CODE and not v:
            raise ValueError('短信验证码不能为空')
        return v

# src/api/schemas/auth/responses.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")

class UserInfoResponse(BaseModel):
    """用户信息响应"""
    user_id: str = Field(..., description="用户ID")
    username: Optional[str] = Field(None, description="用户名")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    level: int = Field(default=1, description="等级")
    experience_points: int = Field(default=0, description="经验值")
    total_points: int = Field(default=0, description="总积分")
    available_points: int = Field(default=0, description="可用积分")
    created_at: datetime = Field(..., description="创建时间")
```

## 性能优化设计

### 数据库优化

1. **索引策略**
   - 主键索引：所有表的主键自动索引
   - 外键索引：关联字段建立索引
   - 查询索引：常用查询字段建立复合索引
   - 时间索引：时间字段建立索引支持范围查询

2. **查询优化**
   - 使用SQLAlchemy异步查询
   - 批量操作减少数据库往返
   - 分页查询避免大量数据传输
   - 预加载关联数据减少N+1查询

3. **连接池优化**
   ```python
   engine = create_async_engine(
       database_url,
       pool_size=20,
       max_overflow=30,
       pool_pre_ping=True,
       pool_recycle=3600,
       echo=False
   )
   ```

### 缓存策略

1. **应用层缓存**
   - 用户信息缓存（TTL: 5分钟）
   - 任务统计数据缓存（TTL: 10分钟）
   - 配置信息缓存（TTL: 30分钟）

2. **内存缓存**
   ```python
   from functools import lru_cache
   from datetime import datetime, timedelta

   @lru_cache(maxsize=1000)
   def get_user_config(user_id: str):
       # 用户配置缓存
       pass
   ```

### API响应优化

1. **分页响应**
   - 默认页大小：20条记录
   - 最大页大小：100条记录
   - 游标分页支持大数据集

2. **响应压缩**
   - GZip压缩响应数据
   - 最小压缩大小：1000字节

3. **字段选择**
   - 支持fields参数选择返回字段
   - 减少不必要的数据传输

## 安全设计

### 认证安全

1. **JWT安全**
   - 使用RS256签名算法
   - 短期访问令牌（30分钟）
   - 长期刷新令牌（7天）
   - 令牌版本控制支持强制登出

2. **密码安全**
   - 使用bcrypt哈希算法
   - 强制密码复杂度要求
   - 密码历史记录防止重复使用

3. **验证码安全**
   - 6位数字验证码
   - 5分钟有效期
   - 最大尝试次数限制
   - 发送频率限制（1分钟1次）

### API安全

1. **输入验证**
   - Pydantic模型严格验证
   - SQL注入防护
   - XSS攻击防护
   - 文件上传安全检查

2. **访问控制**
   - 基于用户的权限控制
   - 资源访问权限验证
   - API操作日志记录

3. **限流防护**
   - 基于用户的请求限流
   - 基于IP的请求限流
   - 敏感操作额外限制

## 测试策略

### 测试金字塔

```
        /\
       /  \
      / E2E \     端到端测试 (10%)
     /______\
    /        \
   /Integration\ 集成测试 (30%)
  /____________\
 /              \
/   Unit Tests    \  单元测试 (60%)
/________________\
```

### 测试覆盖目标

1. **单元测试**: > 95%
   - 每个API端点测试
   - Service层业务逻辑测试
   - 工具函数测试
   - 数据模型测试

2. **集成测试**: > 90%
   - API与Service集成测试
   - 数据库操作测试
   - 外部服务集成测试
   - 中间件集成测试

3. **端到端测试**: > 80%
   - 完整业务流程测试
   - 用户场景测试
   - 性能基准测试
   - 安全渗透测试

### 测试工具和框架

1. **测试框架**: pytest + pytest-asyncio
2. **Mock工具**: pytest-mock + unittest.mock
3. **数据库测试**: pytest-postgresql + sqlite内存库
4. **API测试**: httpx + TestClient
5. **覆盖率**: pytest-cov

---

**设计文档版本**: 1.0.0
**创建日期**: 2025-10-20
**更新日期**: 2025-10-20
**适用版本**: TaKeKe API v2.0.0+