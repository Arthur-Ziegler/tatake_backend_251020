# LangGraph集成规格说明

## 概述

重构ChatService以集成LangGraph框架，实现真实的AI对话功能。使用数据库存储长期记忆，集成任务管理工具，支持Supervisor-Agent模式的多Agent架构。

## ADDED Requirements

### Requirement: LangGraph状态机重构
系统 SHALL使用LangGraph框架重构对话系统，实现状态机驱动的对话流程。

#### Scenario: LangGraph状态机初始化
- **GIVEN** 需要创建对话会话
- **WHEN** 初始化LangGraph状态机时
- **THEN** 系统 SHALL创建StateGraph实例
- **AND** 系统 SHALL配置Supervisor节点作为入口
- **AND** 系统 SHALL配置Task Agent和Chat Agent节点
- **AND** 系统 SHALL设置节点间的转换条件
- **AND** 系统 SHALL编译状态机为可执行图

#### Scenario: 对话状态管理
- **GIVEN** 用户发送消息时
- **WHEN** 处理对话状态时
- **THEN** 系统 SHALL维护消息历史列表
- **AND** 系统 SHALL管理用户上下文信息
- **AND** 系统 SHALL跟踪对话元数据
- **AND** 系统 SHALL识别当前用户意图
- **AND** 系统 SHALL管理需要执行的动作列表

#### Scenario: Supervisor路由决策
- **GIVEN** Supervisor节点收到用户消息
- **WHEN** 分析消息意图时
- **THEN** 系统 SHALL检测任务相关关键词
- **AND** 系统 SHALL识别对话类型（任务管理/一般聊天）
- **AND** 系统 SHALL根据意图路由到相应Agent
- **AND** 系统 SHALL更新当前意图状态
- **AND** 系统 SHALL传递相关上下文给目标Agent

### Requirement: 真实LLM服务集成
系统 SHALL集成真实的LLM API服务，通过环境变量配置。

#### Scenario: LLM服务配置和初始化
- **GIVEN** 系统需要配置LLM服务
- **WHEN** 初始化LLM客户端时
- **THEN** 系统 SHALL从环境变量读取LLM配置
- **AND** 系统 SHALL配置BaseURL和API Key
- **AND** 系统 SHALL设置模型参数（temperature、max_tokens等）
- **AND** 系统 SHALL建立LLM客户端连接
- **AND** 系统 SHALL验证服务可用性

#### Scenario: LLM调用和响应处理
- **GIVEN** Agent需要生成AI回复
- **WHEN** 调用LLM服务时
- **THEN** 系统 SHALL构造适当的提示词
- **AND** 系统 SHALL传递对话上下文给LLM
- **AND** 系统 SHALL处理LLM响应和错误
- **AND** 系统 SHALL解析响应内容
- **AND** 系统 SHALL记录调用日志和性能指标

#### Scenario: LLM错误处理和重试
- **GIVEN** LLM服务调用失败
- **WHEN** 处理API错误时
- **THEN** 系统 SHALL实现自动重试机制
- **AND** 系统 SHALL提供降级回复
- **AND** 系统 SHALL记录错误详情
- **AND** 系统 SHALL监控服务健康状态
- **AND** 系统 SHALL实现服务切换机制

### Requirement: 任务管理工具集成
系统 SHALL为AI Agent集成任务管理工具，实现自然语言操作任务。

#### Scenario: 任务查询工具
- **GIVEN** AI需要查询用户任务
- **WHEN** 调用任务查询工具时
- **THEN** 系统 SHALL解析自然语言查询条件
- **AND** 系统 SHALL转换为结构化查询参数
- **AND** 系统 SHALL调用TaskService查询任务
- **AND** 系统 SHALL格式化查询结果为自然语言
- **AND** 系统 SHALL处理查询错误和异常

#### Scenario: 任务操作工具
- **GIVEN** AI需要操作用户任务
- **WHEN** 调用任务操作工具时
- **THEN** 系统 SHALL验证用户权限和任务状态
- **AND** 系统 SHALL执行任务创建、更新、删除操作
- **AND** 系统 SHALL处理操作结果和错误
- **AND** 系统 SHALL记录操作日志
- **AND** 系统 SHALL触发相关的业务逻辑（奖励、统计等）

#### Scenario: 工具权限和安全控制
- **GIVEN** AI尝试调用任务管理工具
- **WHEN** 验证工具调用权限时
- **THEN** 系统 SHALL验证用户身份和权限
- **AND** 系统 SHALL检查操作类型权限
- **AND** 系统 SHALL限制危险操作（删除大量任务）
- **AND** 系统 SHALL记录所有工具调用
- **AND** 系统 SHALL实现调用频率限制

### Requirement: 数据库长期记忆系统
系统 SHALL使用SQLite数据库实现长期对话记忆，替代Redis功能。

#### Scenario: 对话上下文存储
- **GIVEN** 对话过程中需要保存上下文
- **WHEN** 存储对话记忆时
- **THEN** 系统 SHALL将对话上下文存储到chat_memory表
- **AND** 系统 SHALL分类存储不同类型的记忆
- **AND** 系统 SHALL设置记忆过期时间
- **AND** 系统 SHALL优化存储格式和索引
- **AND** 系统 SHALL实现记忆压缩和摘要

#### Scenario: 长期记忆检索
- **GIVEN** 需要检索用户的长期记忆
- **WHEN** 查询对话记忆时
- **THEN** 系统 SHALL根据会话ID和用户ID查询
- **AND** 系统 SHALL支持按记忆类型筛选
- **AND** 系统 SHALL实现记忆相关性排序
- **AND** 系统 SHALL优化查询性能
- **AND** 系统 SHALL处理记忆过期和清理

#### Scenario: 记忆管理和优化
- **GIVEN** 需要管理大量对话记忆
- **WHEN** 优化记忆存储时
- **THEN** 系统 SHALL实现记忆重要性评分
- **AND** 系统 SHALL定期清理低价值记忆
- **AND** 系统 SHALL压缩和归档历史记忆
- **AND** 系统 SHALL实现记忆搜索功能
- **AND** 系统 SHALL监控存储使用情况

### Requirement: 多模式对话支持
系统 SHALL支持多种对话模式，提供个性化的AI助手体验。

#### Scenario: 任务助手模式
- **GIVEN** 用户选择任务助手模式
- **WHEN** 进行任务相关对话时
- **THEN** 系统 SHALL主动提供任务建议
- **AND** 系统 SHALL分析任务完成情况
- **AND** 系统 SHALL提供时间管理建议
- **AND** 系统 SHALL集成绩效分析和改进建议
- **AND** 系统 SHALL支持任务创建和管理的自然语言交互

#### Scenario: 生产力教练模式
- **GIVEN** 用户选择生产力教练模式
- **WHEN** 寻求生产力建议时
- **THEN** 系统 SHALL分析用户工作习惯
- **AND** 系统 SHALL提供个性化建议
- **AND** 系统 SHALL跟踪用户目标进度
- **AND** 系统 SHALL提供激励和反馈
- **AND** 系统 SHALL推荐最佳实践和方法

#### Scenario: 专注指导模式
- **GIVEN** 用户选择专注指导模式
- **WHEN** 需要专注帮助时
- **THEN** 系统 SHALL提供专注技巧建议
- **AND** 系统 SHALL分析专注历史数据
- **AND** 系统 SHALL提供个性化专注计划
- **AND** 系统 SHALL支持专注会话的AI指导
- **AND** 系统 SHALL提供专注效果反馈

## MODIFIED Requirements

### Requirement: ChatService架构重构
原有的ChatService SHALL完全重构以支持LangGraph集成。

#### Scenario: LangGraph集成架构
- **GIVEN** 需要重构ChatService
- **WHEN** 集成LangGraph时
- **THEN** ChatService SHALL移除原有的简单对话逻辑
- **AND** ChatService SHALL集成LangGraph状态机
- **AND** ChatService SHALL实现数据库记忆管理
- **AND** ChatService SHALL支持工具调用机制
- **AND** ChatService SHALL优化性能和错误处理

### Requirement: 对话API适配
对话API SHALL适配新的LangGraph架构。

#### Scenario: API接口更新
- **GIVEN** 对话API需要支持新架构
- **WHEN** 调用对话API时
- **THEN** API SHALL与LangGraph状态机集成
- **AND** API SHALL支持异步对话处理
- **AND** API SHALL返回结构化的对话结果
- **AND** API SHALL处理工具调用结果
- **AND** API SHALL提供对话状态查询

## 技术实现细节

### LangGraph状态机配置

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from typing import Literal, Dict, Any

def create_chat_graph() -> StateGraph:
    """创建LangGraph对话状态机"""

    # 定义状态
    class ChatState(MessagesState):
        user_id: str
        session_id: str
        current_intent: Optional[str]
        tool_results: Dict[str, Any]
        processing_state: str

    # 创建状态机
    graph = StateGraph(ChatState)

    # 添加节点
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("task_agent", task_agent_node)
    graph.add_node("chat_agent", chat_agent_node)

    # 设置入口点
    graph.add_edge(START, "supervisor")

    # 添加条件边
    graph.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "task_agent": "task_agent",
            "chat_agent": "chat_agent",
            "end": END
        }
    )

    # 返回主节点
    graph.add_edge("task_agent", "supervisor")
    graph.add_edge("chat_agent", "supervisor")

    return graph.compile()
```

### 数据库记忆Schema

```sql
-- 长期记忆表
CREATE TABLE chat_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id UUID NOT NULL,
    user_id UUID NOT NULL,
    memory_type VARCHAR(50) NOT NULL, -- 'context', 'preference', 'summary', 'reference'
    memory_key VARCHAR(255) NOT NULL,
    memory_value TEXT NOT NULL,
    memory_metadata JSONB,
    importance_score INTEGER DEFAULT 1, -- 1-10
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_user (session_id, user_id),
    INDEX idx_memory_type (memory_type),
    INDEX idx_importance (importance_score),
    INDEX idx_expires_at (expires_at)
);

-- 对话摘要表
CREATE TABLE chat_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id UUID NOT NULL,
    user_id UUID NOT NULL,
    summary_text TEXT NOT NULL,
    summary_type VARCHAR(50) NOT NULL, -- 'daily', 'weekly', 'session'
    covered_period_start TIMESTAMP WITH TIME ZONE,
    covered_period_end TIMESTAMP WITH TIME ZONE,
    key_topics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_type (session_id, summary_type),
    INDEX idx_period (covered_period_start, covered_period_end)
);
```

### 工具调用实现

```python
from langchain_core.tools import tool
from typing import Dict, Any, List

@tool
def create_task_from_chat(
    title: str,
    description: str = "",
    priority: str = "medium",
    user_id: str = None
) -> Dict[str, Any]:
    """
    通过对话创建任务

    Args:
        title: 任务标题
        description: 任务描述
        priority: 优先级 (high/medium/low)
        user_id: 用户ID

    Returns:
        创建结果
    """
    # 实现任务创建逻辑
    pass

@tool
def get_task_suggestions(
    user_id: str,
    context: str = ""
) -> List[Dict[str, Any]]:
    """
    获取任务建议

    Args:
        user_id: 用户ID
        context: 对话上下文

    Returns:
        任务建议列表
    """
    # 实现任务建议逻辑
    pass

@tool
def analyze_productivity(
    user_id: str,
    period: str = "week"
) -> Dict[str, Any]:
    """
    分析用户生产力

    Args:
        user_id: 用户ID
        period: 分析周期 (day/week/month)

    Returns:
        生产力分析结果
    """
    # 实现生产力分析逻辑
    pass
```

### 记忆管理器实现

```python
class ChatMemoryManager:
    """对话记忆管理器"""

    def __init__(self, db_session):
        self.db_session = db_session

    async def store_context_memory(
        self,
        session_id: str,
        user_id: str,
        context_data: Dict[str, Any]
    ) -> None:
        """存储上下文记忆"""
        for key, value in context_data.items():
            memory = ChatMemory(
                session_id=session_id,
                user_id=user_id,
                memory_type="context",
                memory_key=key,
                memory_value=json.dumps(value),
                importance_score=self._calculate_importance(key, value)
            )
            self.db_session.add(memory)
        await self.db_session.commit()

    async def retrieve_relevant_memories(
        self,
        session_id: str,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[ChatMemory]:
        """检索相关记忆"""
        # 实现相关性搜索
        memories = await self.db_session.query(ChatMemory).filter(
            ChatMemory.user_id == user_id,
            ChatMemory.expires_at > datetime.now(timezone.utc)
        ).order_by(
            ChatMemory.importance_score.desc(),
            ChatMemory.access_count.desc()
        ).limit(limit).all()

        return memories

    def _calculate_importance(self, key: str, value: Any) -> int:
        """计算记忆重要性"""
        importance = 1

        # 根据关键词评估重要性
        important_keywords = ["goal", "preference", "habit", "deadline"]
        if any(keyword in key.lower() for keyword in important_keywords):
            importance += 3

        # 根据数据类型评估
        if isinstance(value, dict) and len(value) > 5:
            importance += 2

        return min(importance, 10)
```

---

**规格版本**: 1.0.0
**创建日期**: 2025-10-20
**适用模块**: AI对话API + ChatService
**依赖模块**: LangGraph, SQLite数据库, TaskService, LLM API