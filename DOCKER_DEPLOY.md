# SuperTool Docker 部署指南

## 📋 概述

这是一个完整的Docker镜像构建和部署方案，支持一键将SuperTool服务部署到远程服务器。采用分步骤脚本设计，便于调试和维护。

### 🎯 特性

- ✅ **分步骤部署** - 独立步骤脚本，便于调试和故障排除
- ✅ **一键部署** - 一个命令完成构建、打包、上传、部署、测试
- ✅ **多架构支持** - 支持x86_64、arm64等架构
- ✅ **安全传输** - 支持压缩包密码保护
- ✅ **健康检查** - 自动验证服务状态
- ✅ **回滚机制** - 支持保留旧版本镜像
- ✅ **配置管理** - 所有配置从.env文件读取

## 🚀 快速开始

### 1. 准备环境文件

```bash
# 复制环境配置模板
cp .env.example .env

# 复制部署配置模板
cp deploy.env.example deploy.env
```

### 2. 配置环境变量

编辑 `.env` 文件（应用配置）：
```bash
# 数据库配置
DB_HOST=your_db_host
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_NAME=postgres

# 嵌入服务配置
EMBEDDING_MODEL=qwen3
EMBEDDING_API_BASE=http://your_embedding_service:8002/v1
EMBEDDING_API_KEY=your_api_key
EMBEDDING_DIMENSIONS=1024
```

编辑 `deploy.env` 文件（部署配置）：
```bash
# 镜像配置
DOCKER_VERSION=1.0.0
DOCKER_IMAGE_NAME=supertool
DOCKER_PLATFORMS=x86_64

# 服务器配置
SERVER_HOST=192.168.1.100
SERVER_PORT=22
SERVER_USER=root
SERVER_PASSWORD=your_server_password
DEPLOY_DIR=/opt/supertool

# 容器配置
CONTAINER_NAME=supertool
HOST_PORT=20001
CONTAINER_PORT=20001
```

### 3. 执行部署

**一键部署（推荐）**：
```bash
# 执行所有步骤
./scripts/deploy-all.sh

# 使用特定配置文件
./scripts/deploy-all.sh production.env

# 预演模式（不实际执行）
./scripts/deploy-all.sh --dry-run

# 跳过测试
./scripts/deploy-all.sh --skip-tests
```

**分步执行**：
```bash
# 步骤1: 构建Docker镜像
./scripts/01-build-image.sh

# 步骤2: 导出Docker镜像
./scripts/02-export-image.sh

# 步骤3: 上传到服务器
./scripts/03-upload-image.sh

# 步骤4: 在服务器部署
./scripts/04-deploy-image.sh

# 步骤5: 测试部署结果
./scripts/05-test-deployment.sh
```

## 📁 文件结构

```
├── Dockerfile                 # Docker镜像构建文件
├── deploy.env.example         # 部署配置模板
├── DOCKER_DEPLOY.md          # 本文档
└── scripts/
    ├── 01-build-image.sh     # 步骤1: 构建镜像
    ├── 02-export-image.sh    # 步骤2: 导出镜像
    ├── 03-upload-image.sh    # 步骤3: 上传服务器
    ├── 04-deploy-image.sh    # 步骤4: 部署容器
    ├── 05-test-deployment.sh # 步骤5: 测试验证
    ├── deploy-all.sh         # 一键部署脚本
    └── README.md            # 脚本使用说明
```

## 📋 脚本详解

### 1. 01-build-image.sh - 构建Docker镜像

**功能**: 构建包含SuperTool应用的Docker镜像

**支持特性**:
- 单架构和多架构构建
- 依赖检查
- 镜像验证

**使用方法**:
```bash
./scripts/01-build-image.sh [配置文件]
```

### 2. 02-export-image.sh - 导出Docker镜像

**功能**: 将构建好的Docker镜像导出为压缩文件

**支持特性**:
- 自动压缩
- 可选密码保护
- 文件大小显示
- 可配置输出目录（相对路径支持）

**使用方法**:
```bash
./scripts/02-export-image.sh [配置文件]
```

**配置选项**:
- `DOCKER_IMAGES_OUTPUT`: 镜像输出目录（默认: ./docker-images）

### 3. 03-upload-image.sh - 上传到服务器

**功能**: 将镜像文件和环境配置上传到目标服务器

**支持特性**:
- 服务器连接测试
- Docker环境检查
- 环境文件自动上传

**使用方法**:
```bash
./scripts/03-upload-image.sh [配置文件]
```

### 4. 04-deploy-image.sh - 在服务器部署

**功能**: 在目标服务器上加载镜像并启动容器

**支持特性**:
- 自动停止旧容器
- 端口冲突检查
- 健康检查
- 日志输出

**使用方法**:
```bash
./scripts/04-deploy-image.sh [配置文件]
```

### 5. 05-test-deployment.sh - 测试部署结果

**功能**: 验证部署是否成功并测试API功能

**支持特性**:
- 健康检查
- API功能测试
- 容器状态检查
- 系统资源监控

**使用方法**:
```bash
./scripts/05-test-deployment.sh [配置文件]
```

## ⚙️ 配置详解

### Docker镜像配置

```bash
DOCKER_VERSION=1.0.0              # 镜像版本号
DOCKER_IMAGE_NAME=supertool        # 镜像名称
DOCKER_PLATFORMS=x86_64            # 目标架构
                                   # x86_64 - Intel/AMD 64位
                                   # arm64 - ARM 64位
                                   # x86_64,arm64 - 多架构
DOCKER_IMAGES_OUTPUT=./docker-images  # 镜像输出目录（相对路径）
                                   # 支持相对路径和绝对路径
                                   # 默认: ./docker-images
```

### 服务器配置

```bash
SERVER_HOST=192.168.1.100         # 服务器IP或域名
SERVER_PORT=22                    # SSH端口
SERVER_USER=root                  # SSH用户名
SERVER_PASSWORD=your_password     # SSH密码
DEPLOY_DIR=/opt/supertool         # 部署目录
```

### 容器配置

```bash
CONTAINER_NAME=supertool          # 容器名称
HOST_PORT=20001                   # 主机端口
CONTAINER_PORT=20001              # 容器端口
STOP_OLD_CONTAINER=true           # 是否停止旧容器
CLEANUP_OLD_IMAGES=true           # 是否清理旧镜像
```

### 安全配置

```bash
SSH_TIMEOUT=30                    # SSH连接超时（秒）
COMPRESS_PASSWORD=                # 压缩包密码（可选）
```

### 测试配置

```bash
RUN_TESTS=true                    # 是否运行测试
HEALTH_CHECK_TIMEOUT=60           # 健康检查超时（秒）
TEST_API_URL=http://localhost:20001/health  # 测试URL
```

## 🔧 高级用法

### 预演模式

查看将要执行的步骤，不实际操作：

```bash
./scripts/deploy-all.sh --dry-run
```

### 分步执行

从特定步骤开始执行：

```bash
# 从第3步开始执行
./scripts/deploy-all.sh --start-from 3

# 只执行前3步
./scripts/deploy-all.sh --stop-at 3

# 从第2步执行到第4步
./scripts/deploy-all.sh --start-from 2 --stop-at 4
```

### 跳过测试

跳过最后的测试步骤：

```bash
./scripts/deploy-all.sh --skip-tests
# 或
./scripts/05-test-deployment.sh --skip-tests
```

### 分环境部署

```bash
# 开发环境
cp deploy.env.example dev.env
# 编辑 dev.env...
./scripts/deploy-all.sh dev.env

# 生产环境
cp deploy.env.example prod.env
# 编辑 prod.env...
./scripts/deploy-all.sh prod.env
```

## 🔍 故障排除

### 常见问题

#### 1. 脚本权限问题

```bash
chmod +x scripts/*.sh
```

#### 2. Docker构建失败

```bash
# 检查Docker环境
docker --version
docker info

# 清理Docker缓存
docker system prune -f
```

#### 3. SSH连接失败

```bash
# 测试SSH连接
ssh root@your_server_ip

# 检查SSH配置
vim ~/.ssh/config
```

#### 4. 单独调试某个步骤

```bash
# 单独执行构建步骤
./scripts/01-build-image.sh

# 查看详细日志
bash -x ./scripts/01-build-image.sh
```

#### 5. 健康检查失败

```bash
# 手动检查服务
curl http://your_server_ip:20001/health

# 查看容器日志
ssh root@your_server_ip "docker logs supertool"
```

#### 6. 端口冲突

```bash
# 检查端口占用
ssh root@your_server_ip "netstat -tlnp | grep 20001"

# 修改配置文件中的端口
HOST_PORT=20002
```

### 调试模式

```bash
# 保留临时文件用于调试
./scripts/deploy-all.sh --keep-temp

# 查看详细日志
bash -x ./scripts/deploy-all.sh
```

### 日志查看

```bash
# 查看容器状态
ssh root@server_ip "docker ps | grep supertool"

# 查看容器日志
ssh root@server_ip "docker logs supertool"

# 查看实时日志
ssh root@server_ip "docker logs -f supertool"
```

## 🔐 安全建议

### 1. SSH密钥认证（推荐）

```bash
# 生成SSH密钥对
ssh-keygen -t rsa -b 4096 -C "deploy_key"

# 复制公钥到服务器
ssh-copy-id root@your_server_ip

# 修改部署脚本使用密钥认证
# 在scripts中修改scp和ssh命令
```

### 2. 环境变量安全

- 不要在代码中硬编码密码
- 定期更换密码和API密钥
- 使用强密码

### 3. 网络安全

- 配置防火墙规则
- 限制SSH访问IP
- 使用VPN或专用网络

## 📊 监控和维护

### 查看容器状态

```bash
# SSH到服务器
ssh root@your_server_ip

# 查看容器状态
docker ps | grep supertool

# 查看容器资源使用
docker stats supertool

# 查看容器日志
docker logs supertool
```

### 更新部署

```bash
# 更新版本号
vim deploy.env  # 修改 DOCKER_VERSION

# 重新部署
./scripts/deploy-all.sh
```

### 回滚操作

```bash
# 停止当前容器
ssh root@your_server_ip "docker stop supertool"

# 启动旧版本（如果有保存）
ssh root@your_server_ip "docker run -d --name supertool_old supertool:old_version"
```

## 📝 部署流程图

```
┌─────────────────┐
│   本地环境      │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  构建Docker镜像 │  (01-build-image.sh)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  导出并压缩     │  (02-export-image.sh)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   上传到服务器  │  (03-upload-image.sh)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   部署容器      │  (04-deploy-image.sh)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   健康检查      │  (05-test-deployment.sh)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   部署完成      │
└─────────────────┘
```

## 🆘 获取帮助

```bash
# 查看主脚本帮助
./scripts/deploy-all.sh --help

# 查看各步骤脚本帮助
./scripts/01-build-image.sh --help
./scripts/02-export-image.sh --help
./scripts/03-upload-image.sh --help
./scripts/04-deploy-image.sh --help
./scripts/05-test-deployment.sh --help

# 查看版本信息
./scripts/deploy-all.sh --version
```

## 🚨 注意事项

1. **确保目标服务器已安装Docker**
2. **检查服务器防火墙设置**
3. **确认数据库连接配置正确**
4. **验证端口未被其他服务占用**
5. **备份重要数据后再部署**

---

**注意**: 此脚本专为简化版部署设计，生产环境建议使用Docker Registry或CI/CD流水线。