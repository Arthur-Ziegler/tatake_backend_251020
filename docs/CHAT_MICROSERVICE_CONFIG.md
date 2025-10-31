# 聊天微服务配置指南

## 概述

TaKeKe后端集成了聊天微服务，提供流式聊天对话功能。本文档说明如何配置聊天微服务连接。

## 微服务端点

- **聊天微服务URL**: `http://45.152.65.130:20252`
- **流式聊天**: `POST /chat/stream`
- **消息历史**: `GET /api/sessions/{session_id}/messages`
- **健康检查**: `GET /health`

## 环境变量配置

### 必需配置

在 `.env` 文件中添加以下配置：

```bash
# ============================================
# 聊天微服务配置
# ============================================
# 聊天微服务URL
CHAT_SERVICE_URL=http://45.152.65.130:20252

# 聊天微服务调用超时时间（秒）
CHAT_SERVICE_TIMEOUT=30
```

### 可选配置

如果需要使用OpenAI直接集成（备用方案）：

```bash
# ============================================
# LLM聊天配置 - 每次都从.env文件中读取
# ============================================
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7

# 通用LLM配置（备用，OPENAI配置优先）
LLM_API_KEY=your-llm-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.7
```

## API接口说明

聊天系统提供4个核心接口：

### 1. 查询所有会话列表
```
GET /chat/sessions
Authorization: Bearer <token>
```

**响应格式**：
```json
{
  "code": 200,
  "message": "获取会话列表成功",
  "data": [
    {
      "session_id": "20251101053000_4a42",
      "title": "会话20251101053000"
    }
  ]
}
```

### 2. 查询聊天记录
```
GET /chat/sessions/{session_id}/messages
Authorization: Bearer <token>
```

**响应格式**：
```json
{
  "code": 200,
  "message": "获取聊天记录成功",
  "data": {
    "session_id": "20251101053000_4a42",
    "title": "会话20251101053000",
    "messages": [
      {
        "role": "human",
        "content": "用户消息",
        "time": "2025-11-01T05:30:15Z"
      },
      {
        "role": "assistant",
        "content": "AI回复",
        "time": "2025-11-01T05:30:20Z"
      }
    ]
  }
}
```

### 3. 删除会话
```
DELETE /chat/sessions/{session_id}
Authorization: Bearer <token>
```

**响应格式**：
```json
{
  "code": 200,
  "message": "删除会话成功",
  "data": {
    "success": true
  }
}
```

### 4. 流式聊天
```
POST /chat/sessions/{session_id}/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "用户消息内容"
}
```

**响应格式**：
```
data: {"type":"token","content":"我"}
data: {"type":"token","content":"是"}
data: {"type":"token","content":"水"}
data: {"type":"token","content":"獭"}
data: {"type":"token","content":"大"}
data: {"type":"token","content":"可"}
data: {"type":"done","content":null}
```

## 会话ID格式

会话ID采用时间戳+随机后缀格式：`YYYYMMDDHHMMSS_XXXX`

- 示例：`20251101053000_4a42`
- 自动生成，确保唯一性
- 支持按时间排序

## 错误处理

### 常见错误码

- `404`: 会话不存在或无权限访问
- `500`: 聊天微服务暂时不可用
- `401`: 认证失败，请检查token

### 错误响应格式

```json
{
  "code": 500,
  "message": "聊天服务暂时不可用",
  "data": null
}
```

## 部署检查清单

### 开发环境

- [ ] `.env` 文件包含 `CHAT_SERVICE_URL`
- [ ] 聊天微服务可访问：`curl http://45.152.65.130:20252/health`
- [ ] 本地测试所有4个接口正常工作

### 生产环境

- [ ] 环境变量配置正确
- [ ] 防火墙允许访问聊天微服务
- [ ] 超时时间根据网络情况调整
- [ ] 监控微服务可用性

## 故障排除

### 连接问题

1. **检查网络连通性**：
   ```bash
   curl -v http://45.152.65.130:20252/health
   ```

2. **检查超时设置**：
   - 默认30秒，可根据网络情况调整
   - 建议生产环境设置为60秒

3. **检查负载均衡**：
   - 确保微服务实例足够
   - 监控CPU和内存使用率

### 性能优化

1. **启用连接池**：
   - HTTP客户端已配置连接复用
   - 可调整并发连接数

2. **监控响应时间**：
   - 流式聊天应该在5秒内开始响应
   - 平均token响应时间<100ms

3. **缓存策略**：
   - 会话列表可缓存1分钟
   - 消息历史可缓存5分钟

## 安全注意事项

1. **API密钥保护**：
   - 不要在代码中硬编码API密钥
   - 使用环境变量存储敏感信息

2. **访问控制**：
   - 所有接口都需要有效的JWT token
   - 验证用户只能访问自己的会话

3. **数据隐私**：
   - 聊天内容可能包含敏感信息
   - 遵循数据保护法规

## 更新日志

- **2025-11-01**: 初始版本，支持4个核心接口
- **微服务URL**: `http://45.152.65.130:20252`
- **支持流式响应**: 实时token流式输出