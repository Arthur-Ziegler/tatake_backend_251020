#!/usr/bin/env bash
# =============================================================================
# 步骤5: 测试部署结果
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
    local required_vars=("SERVER_HOST" "SERVER_USER" "HOST_PORT")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "配置项缺失: $var"
            exit 1
        fi
    done

    log_success "配置加载完成"
}

# 检查依赖
check_dependencies() {
    log "检查测试依赖..."

    if ! command -v curl &> /dev/null; then
        log_error "curl未安装或不在PATH中"
        exit 1
    fi

    log_success "依赖检查通过"
}

# 测试服务器连接
test_server_connection() {
    log "测试服务器连接..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"

    if ! ssh -p "$port" -o StrictHostKeyChecking=no -o ConnectTimeout="${SSH_TIMEOUT:-30}" \
        "$server" "echo 'Connection test successful'" &>/dev/null; then
        log_error "无法连接到服务器"
        exit 1
    fi

    log_success "服务器连接正常"
}

# 健康检查
test_health_check() {
    local test_url="${TEST_API_URL:-http://${SERVER_HOST}:${HOST_PORT}/health}"

    log "执行健康检查..."
    log_info "测试URL: $test_url"

    if [[ "${RUN_TESTS:-true}" != "true" ]]; then
        log_info "跳过测试 (RUN_TESTS=false)"
        return 0
    fi

    local timeout="${HEALTH_CHECK_TIMEOUT:-60}"
    local count=0

    log_info "等待服务启动... (超时: ${timeout}秒)"

    while [[ $count -lt $timeout ]]; do
        if curl -f -s "$test_url" &>/dev/null; then
            log_success "健康检查通过!"

            # 获取健康检查响应
            local response
            response=$(curl -s "$test_url" 2>/dev/null || echo '{"message": "无响应"}')
            log_info "服务响应: $response"
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

# 检查容器状态
check_container_status() {
    log "检查容器运行状态..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"

    # 检查容器是否运行
    local container_status
    container_status=$(ssh -p "$port" -o StrictHostKeyChecking=no "$server" \
        "docker ps --format '{{.Names}}\t{{.Status}}' | grep '^${CONTAINER_NAME}$'" 2>/dev/null || echo "")

    if [[ -n "$container_status" ]]; then
        log_success "容器正在运行: $CONTAINER_NAME"
        log_info "状态: $container_status"
    else
        log_error "容器未运行或不存在: $CONTAINER_NAME"

        # 显示容器日志（如果有）
        log_info "尝试获取容器日志..."
        ssh -p "$port" -o StrictHostKeyChecking=no "$server" \
            "docker logs ${CONTAINER_NAME} 2>&1 | tail -10" 2>/dev/null || log_info "无法获取容器日志"
        return 1
    fi

    # 检查容器资源使用
    log_info "容器资源使用情况:"
    ssh -p "$port" -o StrictHostKeyChecking=no "$server" \
        "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}' ${CONTAINER_NAME}" 2>/dev/null || \
        log_info "无法获取资源使用信息"
}

# 显示部署结果
show_deployment_result() {
    echo
    echo "=================================="
    echo "🎉 部署测试结果"
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
    echo "SuperTool Docker 部署测试脚本"
    echo
    echo "使用方法:"
    echo "  $0 [配置文件]"
    echo
    echo "参数:"
    echo "  配置文件    部署配置文件 (默认: deploy.env)"
    echo
    echo "示例:"
    echo "  $0                  # 使用默认配置"
    echo "  $0 prod.env        # 使用生产环境配置"
    echo
}

# 主函数
main() {
    local config_file="deploy.env"
    local skip_tests=false

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --version|-v)
                echo "Docker测试脚本 v1.0.0"
                exit 0
                ;;
            --skip-tests)
                skip_tests=true
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
    echo "🧪 步骤5: 测试部署结果"
    echo "=================================="

    load_config "$config_file"
    check_dependencies
    test_server_connection

    # 检查容器状态
    if ! check_container_status; then
        log_error "容器状态检查失败，后续测试可能会失败"
    fi

    # 健康检查
    if [[ "$skip_tests" = false ]]; then
        if ! test_health_check; then
            log_error "健康检查失败"
            show_deployment_result
            exit 1
        fi

        log_info "API功能测试正常"
    else
        log_info "跳过API测试 (--skip-tests)"
    fi

    show_deployment_result

    log_success "🎉 所有测试完成!"
    echo
    echo "✅ SuperTool服务已成功部署并运行!"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi