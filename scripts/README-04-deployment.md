# Docker 部署脚本使用指南

## 概述

原来的 `04-deploy-image.sh` 脚本已经被拆分为多个细粒度的步骤脚本，每个步骤都有明确的职责和独立的执行能力。

## 脚本结构

### 主控脚本
- **`04-deploy-image.sh`** - 主控脚本，可执行完整部署流程或指定步骤

### 细分步骤脚本
1. **`04a-extract-image.sh`** - 解压并加载Docker镜像
2. **`04b-deploy-container.sh`** - 部署Docker容器
3. **`04c-health-check.sh`** - 健康检查和清理

## 使用方法

### 1. 执行完整部署流程
```bash
# 使用默认配置文件 (deploy.env)
./scripts/04-deploy-image.sh

# 使用指定配置文件
./scripts/04-deploy-image.sh prod.env
```

### 2. 执行单个步骤
```bash
# 只解压和加载镜像
./scripts/04a-extract-image.sh

# 只部署容器（需要先执行04a）
./scripts/04b-deploy-container.sh

# 只做健康检查（需要先执行04a和04b）
./scripts/04c-health-check.sh
```

### 3. 从指定步骤开始
```bash
# 从容器部署开始（假设镜像已加载）
./scripts/04-deploy-image.sh --start-from deploy

# 从健康检查开始（假设容器已部署）
./scripts/04-deploy-image.sh --start-from health
```

### 4. 在指定步骤停止
```bash
# 只执行镜像解压
./scripts/04-deploy-image.sh --stop-at extract

# 执行镜像解压和容器部署
./scripts/04-deploy-image.sh --stop-at deploy
```

### 5. 跳过健康检查
```bash
# 执行完整部署但跳过健康检查
./scripts/04-deploy-image.sh --skip-health-check
```

### 6. 组合使用
```bash
# 从容器部署开始，但不执行健康检查
./scripts/04-deploy-image.sh --start-from deploy --stop-at deploy

# 使用指定配置文件，从指定步骤开始
./scripts/04-deploy-image.sh prod.env --start-from deploy
```

## 步骤详解

### 4a-extract-image.sh (镜像解压)
**功能：**
- 检查服务器连接和Docker环境
- 验证上传的镜像文件
- 解压并加载Docker镜像
- 显示已加载镜像的信息

**使用场景：**
- 首次部署时加载镜像
- 更新镜像版本时重新加载

### 04b-deploy-container.sh (容器部署)
**功能：**
- 检查Docker镜像是否已加载
- 清理旧容器（可配置）
- 检查环境文件和端口占用
- 部署并启动新容器
- 显示容器部署信息

**使用场景：**
- 部署新容器
- 重新部署现有容器
- 更新容器配置时

### 04c-health-check.sh (健康检查)
**功能：**
- 检查容器运行状态
- 执行服务健康检查
- 获取容器资源使用情况
- 清理旧Docker镜像
- 显示最终部署结果

**使用场景：**
- 验证部署是否成功
- 监控服务状态
- 清理不需要的镜像

## 配置文件

所有脚本都使用相同的配置文件格式（默认为 `deploy.env`）：

```bash
# 基础配置
DOCKER_VERSION=1.0.0
DOCKER_IMAGE_NAME=supertool
SERVER_HOST=192.168.40.41
SERVER_USER=zale
DEPLOY_DIR=/data/home/zale/docker_images/base_project/supertool

# 容器配置
CONTAINER_NAME=supertool
HOST_PORT=20001
CONTAINER_PORT=20001

# 部署选项
STOP_OLD_CONTAINER=true
CLEANUP_OLD_IMAGES=true
HEALTH_CHECK_TIMEOUT=60
```

## 错误处理

每个脚本都有独立的错误处理机制：
- 检查前置条件（如依赖的步骤是否已完成）
- 验证配置文件的完整性
- 检查服务器连接和权限
- 提供详细的错误信息和解决建议

## 最佳实践

1. **首次部署**：使用完整流程 `./scripts/04-deploy-image.sh`
2. **日常更新**：
   - 只更新镜像：`./scripts/04a-extract-image.sh`
   - 只更新容器：`./scripts/04b-deploy-container.sh`
3. **故障排查**：
   - 检查镜像：`./scripts/04a-extract-image.sh`
   - 检查容器：`./scripts/04b-deploy-container.sh`
   - 检查服务：`./scripts/04c-health-check.sh`
4. **开发测试**：使用 `--skip-health-check` 跳过等待时间

## 依赖关系

```
04a-extract-image.sh (独立)
04b-deploy-container.sh (依赖04a)
04c-health-check.sh (依赖04a和04b)
```

每个脚本都会检查前置条件，如果依赖的步骤未完成会给出明确提示。