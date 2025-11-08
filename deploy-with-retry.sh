#!/bin/bash
# 带重试机制的部署脚本

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

# SSH连接函数（带重试）
ssh_with_retry() {
    local server="$1"
    local command="$2"
    local max_attempts=5
    local attempt=1
    local wait_time=30

    while [ $attempt -le $max_attempts ]; do
        log "SSH连接尝试 $attempt/$max_attempts..."

        if ssh -i ~/.ssh/YcY_Root \
            -p 22 \
            -o StrictHostKeyChecking=no \
            -o ConnectTimeout=10 \
            -o ServerAliveInterval=30 \
            -o ServerAliveCountMax=3 \
            "$server" \
            "$command"; then
            return 0
        fi

        if [ $attempt -lt $max_attempts ]; then
            log "连接失败，${wait_time}秒后重试..."
            sleep $wait_time
            # 增加等待时间
            wait_time=$((wait_time + 10))
        fi

        ((attempt++))
    done

    log_error "SSH连接失败，已尝试 $max_attempts 次"
    return 1
}

echo "=================================="
echo "🚀 带重试机制的Docker容器部署"
echo "=================================="

# 加载配置
if [[ -f "deploy.env" ]]; then
    source deploy.env
    log_success "配置文件加载完成"
else
    log_error "配置文件不存在: deploy.env"
    exit 1
fi

server="root@${SERVER_HOST}"

# 测试连接
log "测试服务器连接..."
if ! ssh_with_retry "$server" "echo '连接成功'"; then
    log_error "无法连接到服务器"
    log_info "请检查："
    log_info "1. 服务器状态是否正常"
    log_info "2. 网络连接是否正常"
    log_info "3. SSH服务是否正在运行"
    exit 1
fi

log_success "服务器连接正常"

# 加载并运行原有部署脚本
log "执行原有部署脚本..."
if ./deploy/04b-deploy-container.sh; then
    log_success "🎉 部署完成!"
else
    log_error "自动部署失败"
    log_info "请尝试手动部署："
    log_info "  ./manual-deploy-commands.sh"
    exit 1
fi