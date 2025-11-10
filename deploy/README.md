# TaKeKe Backend Docker 部署指南

## 📋 目录

- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [部署流程](#部署流程)
- [回滚操作](#回滚操作)
- [故障排查](#故障排查)

## 🚀 快速开始

### 1. 首次部署

```bash
# 1. 复制配置模板
cp deploy/deploy.env.example deploy/deploy.env

# 2. 编辑配置文件
vim deploy/deploy.env

# 3. 一键部署
./deploy/deploy.sh
```

### 2. 更新部署

```bash
# 修改版本号
sed -i '' 's/VERSION=.*/VERSION=1.0.1/' deploy/deploy.env

# 部署新版本（零停机）
./deploy/deploy.sh
```

### 3. 紧急回滚

```bash
# 一键回滚到上一版本
./deploy/rollback.sh
```

## ⚙️ 配置说明

### 必填配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `VERSION` | 版本号 | `1.0.0` |
| `SSH_ALIAS` | SSH别名 | `your-server` |
| `SERVER_HOST` | 服务器IP | `45.152.65.130` |
| `DEPLOY_USER` | 部署用户 | `zale` |
| `HOST_PORT` | 宿主机端口 | `2025` |

### 可选配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `ENABLE_BLUE_GREEN` | 蓝绿部署 | `true` |
| `ENABLE_ROLLBACK` | 自动回滚 | `true` |
| `KEEP_VERSIONS` | 保留版本数 | `2` |
| `MEMORY_LIMIT` | 内存限制 | `2g` |
| `CPU_LIMIT` | CPU限制 | `2` |

## 📦 部署流程

### 标准流程

```
1. 加载配置 (deploy.env)
2. 检查依赖 (Docker, SSH)
3. 构建镜像 (x86架构)
4. 推送镜像 (SSH管道)
5. 蓝绿部署:
   ├─ 启动新容器（蓝）
   ├─ 健康检查
   ├─ 切换流量
   └─ 停止旧容器（绿）
6. 清理旧版本
7. 保存回滚信息
```

### 蓝绿部署示意图

```
部署前:
  [主容器] ──> 服务流量

部署中:
  [主容器(绿)] ──> 服务流量
  [新容器(蓝)] ──> 健康检查

切换后:
  [新容器(主)] ──> 服务流量
  [旧容器(停止)]
```

## 🔄 回滚操作

### 自动回滚

部署失败时自动触发（需配置 `ENABLE_ROLLBACK=true`）

### 手动回滚

```bash
./deploy/rollback.sh
```

回滚会：
1. 恢复上一版本容器
2. 切换服务流量
3. 验证健康检查

## 🔍 故障排查

### 问题1：镜像构建失败

**现象**：
```
ERROR: failed to solve...
```

**解决**：
1. 检查Dockerfile语法
2. 检查网络连接
3. 清理Docker缓存：`docker system prune -a`

### 问题2：SSH连接失败

**现象**：
```
Permission denied (publickey)
```

**解决**：
1. 检查SSH配置：`cat ~/.ssh/config`
2. 测试连接：`ssh ${SSH_ALIAS}`
3. 检查密钥权限：`chmod 600 ~/.ssh/id_rsa`

### 问题3：健康检查失败

**现象**：
```
健康检查超时
```

**解决**：
1. 手动检查容器日志：
   ```bash
   ssh ${SERVER_HOST} "docker logs ${CONTAINER_NAME}"
   ```
2. 检查端口映射：
   ```bash
   ssh ${SERVER_HOST} "docker ps"
   ```
3. 增加超时时间：修改 `HEALTH_CHECK_TIMEOUT`

### 问题4：端口被占用

**现象**：
```
port is already allocated
```

**解决**：
1. 检查端口占用：
   ```bash
   ssh ${SERVER_HOST} "lsof -i:${HOST_PORT}"
   ```
2. 停止冲突容器：
   ```bash
   ssh ${SERVER_HOST} "docker stop <container>"
   ```

## 📊 监控和维护

### 查看容器状态

```bash
ssh ${SERVER_HOST} "docker ps"
```

### 查看容器日志

```bash
ssh ${SERVER_HOST} "docker logs -f ${CONTAINER_NAME}"
```

### 查看资源使用

```bash
ssh ${SERVER_HOST} "docker stats ${CONTAINER_NAME}"
```

### 手动清理

```bash
# 清理未使用的镜像
ssh ${SERVER_HOST} "docker image prune -a"

# 清理未使用的容器
ssh ${SERVER_HOST} "docker container prune"
```

## 🔐 安全建议

1. **SSH密钥**：使用密钥认证，禁用密码登录
2. **环境变量**：敏感信息使用 `.env` 文件
3. **非root用户**：容器以 `app` 用户运行
4. **资源限制**：设置内存和CPU限制
5. **日志管理**：配置日志轮转

## 📝 最佳实践

1. **版本控制**：使用语义化版本号（v1.0.0）
2. **渐进部署**：先部署到测试环境
3. **保留历史**：至少保留2个版本用于回滚
4. **监控告警**：集成健康检查和告警
5. **文档更新**：记录每次部署的变更

## 🆘 紧急操作

### 立即停止服务

```bash
ssh ${SERVER_HOST} "docker stop ${CONTAINER_NAME}"
```

### 强制删除容器

```bash
ssh ${SERVER_HOST} "docker rm -f ${CONTAINER_NAME}"
```

### 查看完整日志

```bash
ssh ${SERVER_HOST} "docker logs --tail 1000 ${CONTAINER_NAME}"
```

## 📞 联系支持

遇到问题？
- 查看日志：`docker logs ${CONTAINER_NAME}`
- 检查健康：`curl http://localhost:${PORT}/health`
- 联系团队：team@example.com
