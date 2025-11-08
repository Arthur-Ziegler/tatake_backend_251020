#!/bin/bash
# 使用密码认证的SSH连接测试脚本

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

log_info() {
    echo -e "${YELLOW}[ℹ]${NC} $1"
}

echo "=================================="
echo "🔧 SSH密码认证测试脚本"
echo "=================================="

# 加载配置
if [[ -f "deploy.env" ]]; then
    source deploy.env
    log_success "配置文件加载完成"
else
    log_error "配置文件不存在: deploy.env"
    exit 1
fi

# 从注释中提取密码
SERVER_PASSWORD="d3kIpv2lOJOD"

# 测试连接
log "测试SSH密码认证连接到 ${SERVER_USER}@${SERVER_HOST}:${SERVER_PORT:-22}"

if sshpass -p "$SERVER_PASSWORD" ssh -p "${SERVER_PORT:-22}" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -o UserKnownHostsFile=/dev/null \
    "${SERVER_USER}@${SERVER_HOST}" \
    "echo 'SSH连接测试成功!'"; then

    log_success "SSH连接正常"

    # 测试Docker是否可用
    log "检查Docker服务状态..."
    if sshpass -p "$SERVER_PASSWORD" ssh -p "${SERVER_PORT:-22}" \
        -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 \
        -o UserKnownHostsFile=/dev/null \
        "${SERVER_USER}@${SERVER_HOST}" \
        "docker --version"; then

        log_success "Docker服务正常"
    else
        log_error "Docker服务不可用"
        exit 1
    fi

else
    log_error "SSH连接失败"
    log_info "请检查："
    log_info "1. 服务器地址和端口是否正确"
    log_info "2. 用户名和密码是否正确"
    log_info "3. 服务器SSH服务是否运行"
    log_info "4. 网络连接是否正常"
    exit 1
fi

log_success "所有检查通过！可以使用密码认证方式进行部署。"