#!/usr/bin/env bash
# =============================================================================
# 步骤4.3: 健康检查和清理
# =============================================================================

set -euo pipefail

# 加载SSH工具函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/ssh-utils.sh"

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
        "SERVER_HOST" "SERVER_USER" "HOST_PORT" "CONTAINER_NAME"
    )
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "配置项缺失: $var"
            exit 1
        fi
    done

    log_success "配置加载完成"
}

# 全局SSH选项
SSH_OPTS=""

# 初始化SSH选项
init_ssh_opts() {
    local port="${SERVER_PORT:-22}"
    SSH_OPTS=$(get_ssh_opts "$port" "${SSH_TIMEOUT:-30}" "${SSH_IDENTITY_FILE:-}")
}

# 检查服务器连接
check_server_connection() {
    log "检查服务器连接..."

    local server="${SERVER_USER}@${SERVER_HOST}"

    if ! ssh_exec "$server" "echo 'Connection test successful'" "$SSH_OPTS" &>/dev/null; then
        log_error "无法连接到服务器"
        exit 1
    fi

    log_success "服务器连接正常"
}

# 检查容器状态
check_container_status() {
    log "检查容器运行状态..."

    local server="${SERVER_USER}@${SERVER_HOST}"

    # 检查容器是否运行
    local container_check
    container_check=$(ssh_exec "$server" "docker ps --format '{{.Names}}' | grep '^${CONTAINER_NAME}$'" "$SSH_OPTS" 2>/dev/null || echo "")

    if [[ -n "$container_check" ]]; then
        # 获取容器状态
        local container_status
        container_status=$(ssh_exec "$server" "docker ps --format '{{.Names}}\t{{.Status}}' | grep '^${CONTAINER_NAME}\t'" "$SSH_OPTS" 2>/dev/null || echo "")

        log_success "容器正在运行: $CONTAINER_NAME"
        log_info "状态: $container_status"
    else
        log_error "容器未运行或不存在: $CONTAINER_NAME"
        return 1
    fi
}

# 健康检查
perform_health_check() {
    log "执行服务健康检查..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"
    local health_url="http://${HTTP_HOST}:${HOST_PORT}/health"
    local timeout="${HEALTH_CHECK_TIMEOUT:-60}"

    log_info "健康检查URL: $health_url"
    log_info "超时时间: ${timeout}秒"

    # 直接在本地执行健康检查
    local count=0
    log_info "等待服务响应..."

    while [[ $count -lt $timeout ]]; do
        if curl -f -s "$health_url" &>/dev/null; then
            log_success "健康检查通过!"

            # 获取健康检查响应
            local response
            response=$(curl -s "$health_url" 2>/dev/null || echo '{"message": "无响应"}')
            log_info "服务响应: $response"

            log_success "健康检查完成!"
            return 0
        fi

        count=$((count + 5))
        log_info "等待服务启动... (${count}/${timeout}s)"
        sleep 5
    done

    log_error "健康检查失败: 服务在${timeout}秒内未响应"
    log_info "请检查:"
    log_info "  - 容器是否正常运行"
    log_info "  - 端口是否正确映射"
    log_info "  - 防火墙设置"
    return 1
}

# 获取容器资源使用情况
get_container_stats() {
    log "获取容器资源使用情况..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"

    # 获取容器统计信息
    local container_stats
    container_stats=$(ssh -p "$port" -o StrictHostKeyChecking=no "$server" \
        "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}' ${CONTAINER_NAME}" 2>/dev/null || echo "无法获取统计信息")

    log_info "容器资源使用情况:"
    echo "$container_stats"
}

# 清理旧镜像
cleanup_old_images() {
    if [[ "${CLEANUP_OLD_IMAGES:-true}" != "true" ]]; then
        log_info "跳过旧镜像清理 (CLEANUP_OLD_IMAGES=false)"
        return 0
    fi

    log "清理旧Docker镜像..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"

    if ! ssh -p "$port" -o StrictHostKeyChecking=no "$server" "docker image prune -f"; then
        log_error "镜像清理失败"
        return 1
    fi

    log_success "旧镜像清理完成"
}

# 显示部署结果
show_deployment_result() {
    echo
    echo "=================================="
    echo "🎉 容器部署成功"
    echo "=================================="
    echo "🖥️  服务器: ${SERVER_USER}@${SERVER_HOST}"
    echo "📁 部署目录: ${DEPLOY_DIR}"
    echo "🐳 容器名称: ${CONTAINER_NAME}"
    echo "🌐 访问地址: http://${SERVER_HOST}:${HOST_PORT}"
    echo "📚 API文档: http://${SERVER_HOST}:${HOST_PORT}/docs"
    echo "🔍 健康检查: http://${SERVER_HOST}:${HOST_PORT}/health"
    echo "=================================="
    echo
    echo "📋 常用管理命令:"
    echo "  查看容器状态: ssh ${SERVER_USER}@${SERVER_HOST} docker ps | grep ${CONTAINER_NAME}"
    echo "  查看容器日志: ssh ${SERVER_USER}@${SERVER_HOST} docker logs ${CONTAINER_NAME}"
    echo "  重启容器: ssh ${SERVER_USER}@${SERVER_HOST} docker restart ${CONTAINER_NAME}"
    echo "  停止容器: ssh ${SERVER_USER}@${SERVER_HOST} docker stop ${CONTAINER_NAME}"
    echo "  进入容器: ssh ${SERVER_USER}@${SERVER_HOST} docker exec -it ${CONTAINER_NAME} bash"
    echo
}

# 显示帮助
show_help() {
    cat << EOF
SuperTool Docker 健康检查脚本

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
    local skip_health_check=false

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --version|-v)
                echo "Docker健康检查脚本 v1.0.0"
                exit 0
                ;;
            --skip-health-check)
                skip_health_check=true
                shift
                ;;
            -*)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
            *)
                if [[ "$config_file" == "deploy.env" ]]; then
                    config_file="$1"
                else
                    log_error "只能指定一个配置文件"
                    exit 1
                fi
                shift
                ;;
        esac
    done

    echo "=================================="
    echo "🔍 步骤4.3: 健康检查和清理"
    echo "=================================="

    load_config "$config_file"
    init_ssh_opts
    check_server_connection

    # 检查容器状态
    if ! check_container_status; then
        log_error "容器状态检查失败，无法继续健康检查"
        exit 1
    fi

    # 健康检查
    if [[ "$skip_health_check" = false ]]; then
        if ! perform_health_check; then
            log_error "健康检查失败"
            exit 1
        fi
        log_info "服务健康检查通过"
    else
        log_info "跳过健康检查 (--skip-health-check)"
    fi

    # 获取资源使用情况
    get_container_stats

    # 清理旧镜像
    cleanup_old_images

    # 显示部署结果
    show_deployment_result

    log_success "🎉 所有检查和清理完成!"
    echo
    echo "✅ SuperTool服务已成功部署并通过健康检查!"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi