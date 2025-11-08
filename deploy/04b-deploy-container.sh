#!/usr/bin/env bash
# =============================================================================
# 步骤4.2: 部署Docker容器
# =============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
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

# 加载SSH工具函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/ssh-utils.sh"

# 全局SSH选项
SSH_OPTS=""

# 初始化SSH选项
init_ssh_opts() {
    local port="${SERVER_PORT:-22}"
    SSH_OPTS=$(get_ssh_opts "$port" "${SSH_TIMEOUT:-30}" "${SSH_IDENTITY_FILE:-}")
}

# 加载配置
load_config() {
    local config_file="${1:-deploy.env}"

    if [[ ! -f "$config_file" ]]; then
        log_error "配置文件不存在: $config_file"
        exit 1
    fi

    log "加载配置文件: $config_file"

    # 加载配置
    set -a
    # shellcheck source=/dev/null
    source "$config_file"
    set +a

    # 验证必填配置
    local required_vars=(
        "DOCKER_VERSION" "DOCKER_IMAGE_NAME" "SERVER_HOST"
        "SERVER_USER" "DEPLOY_DIR" "CONTAINER_NAME"
        "HOST_PORT" "CONTAINER_PORT"
    )
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "配置项缺失: $var"
            exit 1
        fi
    done

    log_success "配置加载完成"
}

# 检查服务器连接
check_server_connection() {
    log "检查服务器连接..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"
    local max_attempts=3
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log "连接尝试 $attempt/$max_attempts..."

        if ssh -p "$port" -o StrictHostKeyChecking=no -o ConnectTimeout="${SSH_TIMEOUT:-30}" \
            -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
            "$server" "echo 'Connection test successful'" &>/dev/null; then
            log_success "服务器连接正常"
            return 0
        fi

        log_info "连接失败，等待5秒后重试..."
        sleep 5
        ((attempt++))
    done

    log_error "无法连接到服务器（已尝试 $max_attempts 次）"
    log_info "可能的解决方案："
    log_info "1. 检查服务器SSH服务状态"
    log_info "2. 确认SSH密钥权限正确（600）"
    log_info "3. 检查服务器防火墙设置"
    exit 1
}

# 检查镜像是否已加载
check_image_loaded() {
    log "检查Docker镜像..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"
    local image_name="${DOCKER_IMAGE_NAME}:${DOCKER_VERSION}"

    if ! ssh -p "$port" -o StrictHostKeyChecking=no "$server" "docker images '$image_name' --format '{{.Repository}}:{{.Tag}}' | grep -q '^$image_name$'"; then
        log_error "Docker镜像未加载: $image_name"
        log_info "请先运行: ./scripts/04a-extract-image.sh"
        exit 1
    fi

    log_success "Docker镜像检查通过: $image_name"
}

# 清理旧容器
cleanup_old_container() {
    if [[ "${STOP_OLD_CONTAINER:-true}" != "true" ]]; then
        log_info "跳过旧容器清理 (STOP_OLD_CONTAINER=false)"
        return 0
    fi

    log "检查并清理旧容器..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"

    # 创建清理脚本
    local cleanup_script="/tmp/supertool_cleanup.sh"
    cat > "$cleanup_script" << EOF
#!/bin/bash
set -euo pipefail

echo "=================================="
echo "🧹 清理旧容器"
echo "=================================="

CONTAINER_NAME="${CONTAINER_NAME}"

# 检查容器是否存在
if docker ps -a --format '{{.Names}}' | grep -q "^\${CONTAINER_NAME}$"; then
    echo "发现旧容器: \${CONTAINER_NAME}"

    # 获取容器状态和启动时间
    container_status=\$(docker ps -a --format '{{.Status}}' --filter "name=^\${CONTAINER_NAME}$")
    container_created=\$(docker ps -a --format '{{.CreatedAt}}' --filter "name=^\${CONTAINER_NAME}$")

    echo "容器状态: \${container_status}"
    echo "创建时间: \${container_created}"

    # 检查容器是否正在运行
    if docker ps --format '{{.Names}}' | grep -q "^\${CONTAINER_NAME}$"; then
        echo "⚠️  容器正在运行，将强制停止"
        docker stop "\${CONTAINER_NAME}" || echo "停止失败，可能已停止"
    else
        echo "⚠️  容器已停止"
    fi

    # 删除容器
    echo "删除容器: \${CONTAINER_NAME}"
    if docker rm "\${CONTAINER_NAME}"; then
        echo "✅ 旧容器已清理"
    else
        echo "❌ 容器删除失败"
        echo "请手动执行: docker rm \${CONTAINER_NAME}"
        exit 1
    fi
else
    echo "ℹ️  没有找到旧容器"
fi

echo "=================================="
echo "✅ 容器清理完成!"
echo "=================================="
EOF

    # 上传清理脚本
    log "上传清理脚本到服务器..."
    if ! scp -P "$port" -o StrictHostKeyChecking=no -o ConnectTimeout="${SSH_TIMEOUT:-30}" \
        "$cleanup_script" "$server:/tmp/cleanup_commands.sh"; then
        log_error "清理脚本上传失败"
        exit 1
    fi

    # 执行清理脚本
    log "执行容器清理..."
    if ! ssh -p "$port" -o StrictHostKeyChecking=no -o ConnectTimeout="${SSH_TIMEOUT:-30}" \
        "$server" "chmod +x /tmp/cleanup_commands.sh && /tmp/cleanup_commands.sh"; then
        log_error "容器清理失败"
        exit 1
    fi

    # 清理临时脚本
    rm -f "$cleanup_script"

    log_success "旧容器清理完成"
}

# 检查环境文件
check_env_file() {
    log "检查环境文件..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"

    if ! ssh -p "$port" -o StrictHostKeyChecking=no "$server" "[ -f '${DEPLOY_DIR}/.env' ]"; then
        log_error "环境文件不存在: ${DEPLOY_DIR}/.env"
        log_info "请确保 .env 文件已正确配置"
        exit 1
    fi

    log_success "环境文件检查通过"
}

# 检查端口占用
check_port_availability() {
    log "检查端口可用性..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"

    # 检查端口是否被占用
    local port_check_result
    port_check_result=$(ssh -p "$port" -o StrictHostKeyChecking=no "$server" "netstat -tlnp 2>/dev/null | grep ':${HOST_PORT} ' || echo 'available'")

    if [[ "$port_check_result" != "available" ]]; then
        log_error "端口 ${HOST_PORT} 已被占用"
        log_info "占用情况:"
        log_info "$port_check_result"
        log_info "请检查是否有其他服务在使用该端口"
        exit 1
    fi

    log_success "端口 ${HOST_PORT} 可用"
}

# 部署新容器
deploy_container() {
    log "部署新容器..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"
    local image_name="${DOCKER_IMAGE_NAME}:${DOCKER_VERSION}"

    # 创建部署脚本
    local deploy_script="/tmp/${DOCKER_IMAGE_NAME}_deploy.sh"
    cat > "$deploy_script" << EOF
#!/bin/bash
set -euo pipefail

echo "=================================="
echo "🚀 开始部署Docker容器"
echo "=================================="

# 设置变量
DEPLOY_DIR="${DEPLOY_DIR}"
image_name="${image_name}"
CONTAINER_NAME="${CONTAINER_NAME}"
HOST_PORT="${HOST_PORT}"
CONTAINER_PORT="${CONTAINER_PORT}"

echo "📋 部署配置:"
echo "  镜像名称: \$image_name"
echo "  容器名称: \${CONTAINER_NAME}"
echo "  主机端口: \${HOST_PORT}"
echo "  容器端口: \${CONTAINER_PORT}"
echo "  部署目录: \${DEPLOY_DIR}"

# 启动新容器
echo "🚀 启动新容器..."
docker run -d \\
    --name "\${CONTAINER_NAME}" \\
    --restart unless-stopped \\
    -p "\${HOST_PORT}:\${CONTAINER_PORT}" \\
    --env-file "\${DEPLOY_DIR}/.env" \\
    -e HOST_PORT="\${HOST_PORT}" \\
    -e CONTAINER_PORT="\${CONTAINER_PORT}" \\
    --add-host=host.docker.internal:host-gateway \\
    --log-driver json-file \\
    --log-opt max-size=10m \\
    --log-opt max-file=3 \\
    "\${image_name}"

# 等待容器启动
echo "⏳ 等待容器启动..."
sleep 10

# 检查容器状态
if ! docker ps --format '{{.Names}}' | grep -q "^\${CONTAINER_NAME}$"; then
    echo "❌ 容器启动失败"
    echo "容器日志:"
    docker logs "\${CONTAINER_NAME}"
    exit 1
fi

echo "✅ 容器启动成功"

# 显示容器信息
echo "=================================="
echo "📊 容器部署信息"
echo "=================================="
echo "容器名称: \${CONTAINER_NAME}"
echo "镜像名称: \$image_name"
echo "访问地址: http://localhost:\${HOST_PORT}"
echo "API文档: http://localhost:\${HOST_PORT}/docs"
echo "健康检查: http://localhost:\${HOST_PORT}/health"
echo "=================================="

echo "🎉 容器部署完成!"
EOF

    # 上传部署脚本
    log "上传部署脚本到服务器..."
    if ! scp -P "$port" -o StrictHostKeyChecking=no -o ConnectTimeout="${SSH_TIMEOUT:-30}" \
        "$deploy_script" "$server:/tmp/deploy_commands.sh"; then
        log_error "部署脚本上传失败"
        exit 1
    fi

    # 执行部署脚本
    log "执行容器部署..."
    if ! ssh -p "$port" -o StrictHostKeyChecking=no -o ConnectTimeout="${SSH_TIMEOUT:-30}" \
        "$server" "chmod +x /tmp/deploy_commands.sh && /tmp/deploy_commands.sh"; then
        log_error "容器部署失败"
        exit 1
    fi

    # 清理临时脚本
    rm -f "$deploy_script"

    log_success "容器部署完成"
}

# 显示帮助
show_help() {
    cat << EOF
SuperTool Docker 容器部署脚本

使用方法:
    $0 [配置文件]

参数:
    配置文件    部署配置文件 (默认: deploy.env)

示例:
    $0                  # 使用默认配置
    $0 prod.env        # 使用生产环境配置

EOF
}

# 主函数
main() {
    local config_file="deploy.env"

    # 解析参数
    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --version|-v)
            echo "Docker容器部署脚本 v1.0.0"
            exit 0
            ;;
        -*)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
        *)
            if [[ $# -gt 0 ]]; then
                config_file="$1"
            fi
            ;;
    esac

    echo "=================================="
    echo "🚀 步骤4.2: 部署Docker容器"
    echo "=================================="

    load_config "$config_file"
    init_ssh_opts
    check_server_connection
    check_image_loaded
    cleanup_old_container
    check_env_file
    check_port_availability
    deploy_container

    log_success "🎉 容器部署完成!"
    echo
    echo "下一步: 运行 ./scripts/04c-health-check.sh"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi