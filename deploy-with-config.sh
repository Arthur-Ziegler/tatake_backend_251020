#!/bin/bash
# 使用SSH配置文件的部署脚本

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

echo "=================================="
echo "🚀 使用SSH配置文件部署容器"
echo "=================================="

# 加载配置
if [[ -f "deploy.env" ]]; then
    source deploy.env
    log_success "配置文件加载完成"
else
    log_error "配置文件不存在: deploy.env"
    exit 1
fi

# 使用SSH配置文件中的主机别名
SSH_ALIAS="YCY_4C8G_Root"

# 测试连接
log "测试SSH连接到 $SSH_ALIAS..."

if ssh "$SSH_ALIAS" "echo '连接测试成功'"; then
    log_success "SSH连接正常"
else
    log_error "SSH连接失败"
    log_info "请检查 ~/.ssh/config 中的配置"
    exit 1
fi

# 检查Docker镜像
log "检查Docker镜像..."
image_name="${DOCKER_IMAGE_NAME}:${DOCKER_VERSION}"

if ! ssh "$SSH_ALIAS" "docker images '$image_name' --format '{{.Repository}}:{{.Tag}}' | grep -q '^$image_name$'"; then
    log_error "Docker镜像未加载: $image_name"
    log_info "请先运行镜像提取脚本"
    exit 1
fi

log_success "Docker镜像检查通过"

# 清理旧容器
if [[ "${STOP_OLD_CONTAINER:-true}" == "true" ]]; then
    log "清理旧容器..."

    if ssh "$SSH_ALIAS" "docker ps -a --format '{{.Names}}' | grep -q '^${CONTAINER_NAME}$'"; then
        ssh "$SSH_ALIAS" "docker stop '${CONTAINER_NAME}' || true"
        ssh "$SSH_ALIAS" "docker rm '${CONTAINER_NAME}' || true"
        log_success "旧容器已清理"
    else
        log_info "没有找到旧容器"
    fi
fi

# 部署新容器
log "部署新容器..."

# 创建部署命令
deploy_cmd="
docker run -d \\
    --name '${CONTAINER_NAME}' \\
    --restart unless-stopped \\
    -p '${HOST_PORT}:${CONTAINER_PORT}' \\
    --env-file '${DEPLOY_DIR}/.env' \\
    -e HOST_PORT='${HOST_PORT}' \\
    -e CONTAINER_PORT='${CONTAINER_PORT}' \\
    --add-host=host.docker.internal:host-gateway \\
    --log-driver json-file \\
    --log-opt max-size=10m \\
    --log-opt max-file=3 \\
    '${image_name}'
"

log "执行部署命令..."
if ssh "$SSH_ALIAS" "$deploy_cmd"; then
    log_success "容器部署命令执行完成"
else
    log_error "容器部署失败"
    exit 1
fi

# 等待容器启动
log "等待容器启动..."
sleep 10

# 检查容器状态
if ssh "$SSH_ALIAS" "docker ps --format '{{.Names}}' | grep -q '^${CONTAINER_NAME}$'"; then
    log_success "容器启动成功"

    # 显示容器信息
    echo "=================================="
    echo "📊 容器部署信息"
    echo "=================================="
    echo "容器名称: ${CONTAINER_NAME}"
    echo "镜像名称: ${image_name}"
    echo "访问地址: http://${HTTP_HOST}:${HOST_PORT}"
    echo "API文档: http://${HTTP_HOST}:${HOST_PORT}/docs"
    echo "健康检查: http://${HTTP_HOST}:${HOST_PORT}/health"
    echo "=================================="

    log_success "🎉 容器部署完成!"
else
    log_error "容器启动失败"
    log_info "查看容器日志:"
    ssh "$SSH_ALIAS" "docker logs '${CONTAINER_NAME}'" || true
    exit 1
fi