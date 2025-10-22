# LangGraph 聊天系统增强设计文档

## 架构设计

### 现状分析

当前聊天系统架构如下：

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Router    │───▶│   Chat Service   │───▶│   Chat Graph    │
│  (FastAPI)      │    │   (Business)     │    │  (LangGraph)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Database Manager │    │   Tools         │
                       │  (SqliteSaver)   │    │ (Sesame Opener) │
                       └──────────────────┘    └─────────────────┘
```

**问题识别**：
1. SqliteSaver 连接配置问题导致数据未真正持久化
2. 缺少有效的会话列表查询机制
3. 上下文管理缺少窗口控制

### 增强后架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Router    │───▶│ Enhanced Chat    │───▶│ Enhanced Chat   │
│  (FastAPI)      │    │    Service       │    │     Graph       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Fixed Database   │    │ Context Manager │
                       │   Manager        │    │  (Window Ctrl)  │
                       │  (SqliteSaver)   │    └─────────────────┘
                       └──────────────────┘              │
                                │                        ▼
                                ▼                ┌─────────────────┐
                       ┌──────────────────┐    │   Tools         │
                       │   Session Store  │    │ (Sesame Opener) │
                       │  (Checkpoints)   │    └─────────────────┘
                       └──────────────────┘
```

## 核心组件设计

### 1. 数据库配置修复

**问题**: 当前 SqliteSaver 配置导致数据库文件未创建在正确位置

**解决方案**:
```python
# 当前问题代码
conn = sqlite3.connect(db_path, check_same_thread=False)

# 修复后代码
from langgraph.checkpoint.sqlite import SqliteSaver

def create_chat_checkpointer() -> SqliteSaver:
    db_path = get_chat_database_path()  # data/chat.db
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return SqliteSaver.from_conn_string(db_path)
```

### 2. 会话管理增强

**新增功能**:
- 基于检查点的会话列表查询
- 会话元数据管理
- 真正的会话删除功能

**实现策略**:
```python
def list_sessions(self, user_id: str, limit: int = 20) -> List[Dict]:
    """通过遍历检查点获取用户会话列表"""
    sessions = []

    # 查询所有可能的 thread_id
    for checkpoint in self._checkpointer.list({"configurable": {}}):
        metadata = checkpoint.metadata or {}
        if metadata.get("user_id") == user_id:
            sessions.append({
                "session_id": checkpoint.config["configurable"]["thread_id"],
                "created_at": checkpoint.metadata.get("created_at"),
                "message_count": len(checkpoint.checkpoint.get("channel_values", {}).get("messages", [])),
                "title": checkpoint.metadata.get("title", "未命名会话")
            })

    return sessions[:limit]
```

### 3. 上下文窗口管理

**设计理念**: 基于 LangGraph MessagesState 的智能上下文管理

**实现方案**:
```python
class EnhancedChatState(MessagesState):
    max_context_messages: int = 20  # 最大上下文消息数

    def trim_context(self):
        """自动裁剪上下文窗口"""
        if len(self.messages) > self.max_context_messages:
            # 保留系统消息和最近的对话
            system_msgs = [msg for msg in self.messages if isinstance(msg, SystemMessage)]
            recent_msgs = self.messages[-(self.max_context_messages - len(system_msgs)):]
            self.messages = system_msgs + recent_msgs
```

## 数据流设计

### 聊天消息处理流程

```
1. 用户发送消息
   ↓
2. API Router → Enhanced Chat Service
   ↓
3. 检查并裁剪上下文窗口
   ↓
4. 调用 Enhanced Chat Graph
   ↓
5. LangGraph 处理消息
   ↓
6. 自动保存到 SqliteSaver (data/chat.db)
   ↓
7. 返回 AI 回复
```

### 会话列表查询流程

```
1. 请求会话列表
   ↓
2. API Router → Enhanced Chat Service
   ↓
3. 遍历 SqliteSaver 检查点
   ↓
4. 按 user_id 过滤会话
   ↓
5. 构建会话元数据
   ↓
6. 返回会话列表
```

## 技术决策

### 1. 为什么选择纯 SqliteSaver 方案？

**优势**:
- 架构简单，符合 KISS 原则
- 数据一致性有保障
- 原生支持 LangGraph 的所有功能
- 支持时间旅行调试

**劣势及缓解**:
- 查询性能相对较低 → 通过合理的数据结构和索引优化
- 功能相对受限 → 满足当前需求，后续可扩展

### 2. 为什么选择 MessagesState 增强管理？

**优势**:
- 基于成熟的 LangGraph 状态机制
- 实现简单，稳定性好
- 性能开销小
- 易于理解和维护

**设计原则**:
- 保持简单，避免过度抽象
- 优先考虑稳定性和性能
- 为未来扩展预留空间

## 性能考虑

### 1. 数据库性能

- SQLite 文件大小控制: 定期清理过期检查点
- 查询优化: 合理使用索引和查询条件
- 连接管理: 使用连接池避免频繁创建连接

### 2. 内存性能

- 上下文窗口控制: 避免长对话占用过多内存
- 消息缓存: 合理使用 LangGraph 的缓存机制
- 垃圾回收: 及时清理不再使用的检查点

### 3. 并发性能

- 线程安全: SqliteSaver 的线程安全配置
- 会话隔离: 通过 thread_id 确保用户数据隔离
- 资源竞争: 避免数据库锁竞争

## 安全考虑

### 1. 数据隔离

- 用户隔离: 严格的 user_id 隔离机制
- 会话隔离: 通过 thread_id 确保会话独立
- 权限控制: JWT 认证 + 用户数据验证

### 2. 数据保护

- 数据库文件权限: 适当的文件系统权限设置
- 敏感信息处理: 避免在日志中泄露敏感信息
- 备份策略: 定期备份聊天数据库

## 监控和调试

### 1. 监控指标

- 数据库连接状态
- 检查点数量和大小
- API 响应时间
- 错误率统计

### 2. 调试工具

- LangGraph 时间旅行调试
- 检查点内容查看
- 日志详细记录
- 健康检查端点

## 测试策略

### 1. 单元测试

- 数据库连接和配置
- 会话管理功能
- 上下文窗口控制
- 数据查询和过滤

### 2. 集成测试

- API 端点完整流程
- 多用户并发场景
- 长对话上下文管理
- 数据持久化验证

### 3. 性能测试

- 大量消息处理性能
- 并发用户会话性能
- 数据库查询性能
- 内存使用情况

## 未来扩展

### 1. 可能的增强

- 聊天搜索功能
- 对话摘要生成
- 多模态消息支持
- 实时协作功能

### 2. 架构演进

- 微服务拆分
- 分布式存储
- 缓存层优化
- 负载均衡

设计保持简单和可扩展性，为未来功能增强预留空间。