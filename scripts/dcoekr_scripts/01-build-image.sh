#!/usr/bin/env bash
# =============================================================================
# 步骤1: 构建Docker镜像
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

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
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
    local required_vars=("DOCKER_VERSION" "DOCKER_IMAGE_NAME" "DOCKER_PLATFORMS")
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
    log "检查Docker环境..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装或不在PATH中"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行或权限不足"
        exit 1
    fi

    log_success "Docker环境检查通过"
}

# 构建镜像
build_image() {
    local image_name="${DOCKER_IMAGE_NAME}:${DOCKER_VERSION}"
    local platforms="${DOCKER_PLATFORMS}"

    log "构建Docker镜像..."
    log_info "镜像名称: $image_name"
    log_info "目标架构: $platforms"

    # 构建镜像
    if [[ "$platforms" == *","* ]]; then
        # 多架构构建
        log_info "执行多架构构建..."
        if ! docker buildx build --platform "$platforms" -t "$image_name" .; then
            log_error "多架构构建失败"
            exit 1
        fi
        docker buildx imagetools create "$image_name"
    else
        # 单架构构建
        log_info "执行单架构构建..."
        # 确保指定平台架构
        local platform_flag=""
        case "$platforms" in
            "x86_64")
                platform_flag="--platform linux/x86_64"
                ;;
            "arm64")
                platform_flag="--platform linux/arm64"
                ;;
            *)
                log_error "不支持的架构: $platforms，支持的架构: x86_64, arm64"
                exit 1
                ;;
        esac

        log_info "构建平台参数: $platform_flag"
        if ! docker build $platform_flag -t "$image_name" .; then
            log_error "单架构构建失败"
            exit 1
        fi
    fi

    # 验证镜像
    if ! docker images "$image_name" --format "table {{.Repository}}:{{.Tag}}" | grep -q "$image_name"; then
        log_error "镜像构建失败或找不到"
        exit 1
    fi

    # 显示镜像架构信息
    log_info "镜像架构信息:"
    docker image inspect "$image_name" --format '{{.Architecture}}'

    log_success "镜像构建完成"
    docker images "$image_name" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
}

# 显示帮助
show_help() {
    cat << EOF
SuperTool Docker 镜像构建脚本

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
            echo "Docker构建脚本 v1.0.0"
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
    echo "🐳 步骤1: 构建Docker镜像"
    echo "=================================="

    check_dependencies
    load_config "$config_file"

    # 架构兼容性检查
    if [[ -n "${SERVER_HOST:-}" && -n "${SERVER_USER:-}" ]]; then
        log "检查架构兼容性..."
        local local_arch
        local_arch=$(uname -m)

        case "$local_arch" in
            "x86_64") local_arch="x86_64" ;;
            "arm64"|"aarch64") local_arch="arm64" ;;
            *) log_error "不支持的本地架构: $local_arch"; exit 1 ;;
        esac

        log_info "本地架构: $local_arch"
        log_info "目标架构: ${DOCKER_PLATFORMS}"

        if [[ "$local_arch" != "${DOCKER_PLATFORMS}" ]]; then
            log_warning "本地架构与目标架构不匹配，将使用交叉构建"
            log_info "构建参数: --platform linux/${DOCKER_PLATFORMS}"
        fi
    fi

    build_image

    log_success "🎉 镜像构建完成!"
    echo
    echo "下一步: 运行 ./scripts/02-export-image.sh"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi