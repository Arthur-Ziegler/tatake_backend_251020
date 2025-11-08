# TaKeKe Backend Docker 部署指南

## 📋 概述

这是专门为 **tatake-backend** 项目定制的Docker镜像构建和部署方案。基于成熟的部署脚本优化，支持一键部署到远程服务器。

### 🎯 特性

- ✅ **专为tatake-backend优化** - 基于项目实际结构定制
- ✅ **uv包管理** - 使用项目现有的uv依赖管理
- ✅ **端口可配置** - 通过.env文件灵活配置端口
- ✅ **多架构支持** - 支持x86_64、arm64等架构
- ✅ **微服务就绪** - 自动连接已部署的微服务
- ✅ **健康检查** - 内置健康检查端点
- ✅ **分步部署** - 便于调试和维护

## 🚀 快速开始

### 1. 配置部署参数

编辑 `deploy.env` 文件：

```bash
# 镜像配置
DOCKER_VERSION=1.0.0
DOCKER_IMAGE_NAME=tatake-backend
DOCKER_PLATFORMS=x86_64,arm64  # 支持所有平台

# 服务器配置
SERVER_HOST=45.152.65.130     # 你的服务器IP
SERVER_PORT=22
SERVER_USER=ubuntu
SSH_IDENTITY_FILE=/Users/zalelee/.ssh/tencent_4c4g

# 容器配置
CONTAINER_NAME=tatake-backend
HOST_PORT=8001                # 可以修改为任意端口
CONTAINER_PORT=8001

# 部署目录
DEPLOY_DIR=/home/ubuntu/docker_images/tatake_backend
```

### 2. 配置应用环境

确保 `.env.production` 文件包含正确的微服务地址：

```bash
# 认证微服务（已部署）
AUTH_MICROSERVICE_URL=http://localhost:8987

# Task微服务（已部署）
TASK_SERVICE_URL=http://127.0.0.1:20252/api/v1

# 聊天微服务（已部署）
CHAT_SERVICE_URL=http://45.152.65.130:20252
```

### 3. 执行部署

**一键部署（推荐）**：
```bash
./scripts/deploy-all.sh
```

**分步执行**：
```bash
# 1. 构建镜像
./scripts/01-build-image.sh

# 2. 导出镜像
./scripts/02-export-image.sh

# 3. 上传到服务器
./scripts/03-upload-image.sh

# 4. 部署容器
./scripts/04-deploy-image.sh

# 5. 测试部署
./scripts/05-test-deployment.sh
```

## 🔧 高级配置

### 端口配置

修改 `deploy.env` 中的端口设置：

```bash
# 修改访问端口（例如改为9001）
HOST_PORT=9001
CONTAINER_PORT=9001
```

### 多架构部署

支持自动构建多架构镜像：

```bash
# 只构建x86_64
DOCKER_PLATFORMS=x86_64

# 构建所有架构
DOCKER_PLATFORMS=x86_64,arm64
```

### 环境切换

```bash
# 开发环境部署
cp .env.development .env.production
./scripts/deploy-all.sh

# 生产环境部署
cp .env.production.example .env.production
# 编辑配置...
./scripts/deploy-all.sh
```

## 📊 验证部署

### 1. 健康检查

```bash
curl http://45.152.65.130:8001/api/v1/health
```

预期响应：
```json
{
  "code": 200,
  "message": "服务运行正常",
  "data": {
    "status": "healthy",
    "app_name": "TaKeKe Backend",
    "version": "1.0.0",
    "timestamp": "2024-xx-xx xx:xx:xx",
    "environment": "production"
  }
}
```

### 2. API文档访问

- Swagger UI: http://45.152.65.130:8001/docs
- ReDoc: http://45.152.65.130:8001/redoc

### 3. 服务状态检查

```bash
# SSH到服务器
ssh ubuntu@45.152.65.130

# 查看容器状态
docker ps | grep tatake-backend

# 查看容器日志
docker logs tatake-backend

# 查看实时日志
docker logs -f tatake-backend
```

## 🔍 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 修改deploy.env中的HOST_PORT
   HOST_PORT=8002
   ```

2. **微服务连接失败**
   ```bash
   # 检查.env.production中的微服务URL
   # 确保微服务已正确部署并运行
   ```

3. **容器启动失败**
   ```bash
   # 查看详细日志
   docker logs tatake-backend
   ```

### 调试模式

```bash
# 预演模式（不实际执行）
./scripts/deploy-all.sh --dry-run

# 跳过测试
./scripts/deploy-all.sh --skip-tests

# 从特定步骤开始
./scripts/deploy-all.sh --start-from 3
```

## 📝 部署流程图

```
┌─────────────────┐
│   本地环境      │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  构建Docker镜像 │  (uv + Python 3.11)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  导出并压缩     │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   上传到服务器  │  (SSH + 环境配置)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   部署容器      │  (连接微服务)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   健康检查      │  (API + 服务测试)
└─────────────────┘
```

## 🎉 完成！

部署完成后，您的tatake-backend服务将在以下地址可用：

- **API服务**: http://45.152.65.130:8001
- **API文档**: http://45.152.65.130:8001/docs
- **健康检查**: http://45.152.65.130:8001/api/v1/health

## 📞 技术支持

如遇问题，请检查：
1. 服务器Docker环境是否正常
2. 微服务是否已部署
3. 网络连接是否正常
4. 配置文件是否正确

---

**注意**: 此方案专为tatake-backend项目优化，假设其他微服务已正确部署。