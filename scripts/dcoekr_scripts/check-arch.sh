#!/usr/bin/env bash
# =============================================================================
# 架构检查脚本
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

# 检查本地架构
check_local_arch() {
    log "检查本地架构..."

    local local_arch
    case "$(uname -m)" in
        "x86_64")
            local_arch="x86_64"
            ;;
        "arm64"|"aarch64")
            local_arch="arm64"
            ;;
        *)
            log_error "不支持的本地架构: $(uname -m)"
            exit 1
            ;;
    esac

    log_info "本地架构: $local_arch"
    echo "$local_arch"
}

# 检查服务器架构
check_server_arch() {
    local server="${1}"
    local port="${2:-22}"

    log "检查服务器架构: $server"

    local server_arch
    server_arch=$(ssh -p "$port" -o StrictHostKeyChecking=no "$server" "uname -m" 2>/dev/null || echo "unknown")

    case "$server_arch" in
        "x86_64")
            ;;
        "arm64"|"aarch64")
            server_arch="arm64"
            ;;
        *)
            log_error "不支持的服务器架构: $server_arch"
            exit 1
            ;;
    esac

    log_info "服务器架构: $server_arch"
    echo "$server_arch"
}

# 检查Docker镜像架构
check_image_arch() {
    local image_name="${1}"

    log "检查Docker镜像架构: $image_name"

    if ! docker images "$image_name" --format "{{.Repository}}:{{.Tag}}" | grep -q "^$image_name$"; then
        log_error "Docker镜像不存在: $image_name"
        exit 1
    fi

    local image_arch
    image_arch=$(docker image inspect "$image_name" --format '{{.Architecture}}')

    log_info "镜像架构: $image_arch"
    echo "$image_arch"
}

# 显示帮助
show_help() {
    cat << EOF
架构检查脚本

使用方法:
    $0 [选项] [镜像名称]

选项:
    --help, -h              显示帮助信息
    --server USER@HOST      检查服务器架构
    --image IMAGE:TAG       检查镜像架构

示例:
    $0                                          # 检查本地架构
    $0 --server user@192.168.1.100             # 检查服务器架构
    $0 --image supertool:1.0.0                 # 检查镜像架构
    $0 --server user@host --image app:latest   # 检查所有架构

EOF
}

# 主函数
main() {
    local server=""
    local image=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --server)
                server="$2"
                shift 2
                ;;
            --image)
                image="$2"
                shift 2
                ;;
            -*)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    echo "=================================="
    echo "🏗️  架构检查工具"
    echo "=================================="

    # 检查本地架构
    local local_arch
    local_arch=$(check_local_arch)

    # 检查服务器架构
    if [[ -n "$server" ]]; then
        local server_arch
        server_arch=$(check_server_arch "$server")

        # 架构兼容性检查
        if [[ "$local_arch" != "$server_arch" ]]; then
            log_warning "本地架构($local_arch)与服务器架构($server_arch)不匹配"
            log_info "构建时需要指定平台参数: --platform linux/$server_arch"
        else
            log_success "本地架构与服务器架构匹配"
        fi
    fi

    # 检查镜像架构
    if [[ -n "$image" ]]; then
        local image_arch
        image_arch=$(check_image_arch "$image")

        # 与本地架构比较
        if [[ -n "$server" ]]; then
            server_arch=$(check_server_arch "$server")
            if [[ "$image_arch" != "$server_arch" ]]; then
                log_error "镜像架构($image_arch)与服务器架构($server_arch)不匹配"
                log_info "需要重新构建镜像: docker build --platform linux/$server_arch -t $image"
            else
                log_success "镜像架构与服务器架构匹配"
            fi
        fi
    fi

    log_success "架构检查完成"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi