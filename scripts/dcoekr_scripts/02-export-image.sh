#!/usr/bin/env bash
# =============================================================================
# 步骤2: 导出Docker镜像
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
    local required_vars=("DOCKER_VERSION" "DOCKER_IMAGE_NAME")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "配置项缺失: $var"
            exit 1
        fi
    done

    # 设置默认输出目录
    DOCKER_IMAGES_OUTPUT="${DOCKER_IMAGES_OUTPUT:-./docker-images}"

    log_success "配置加载完成"
}

# 检查镜像是否存在
check_image() {
    local image_name="${DOCKER_IMAGE_NAME}:${DOCKER_VERSION}"

    log "检查镜像是否存在..."

    if ! docker images "$image_name" --format "{{.Repository}}:{{.Tag}}" | grep -q "^$image_name$"; then
        log_error "镜像不存在: $image_name"
        log_info "请先运行: ./scripts/01-build-image.sh"
        exit 1
    fi

    log_success "镜像检查通过"
}

# 创建输出目录
create_output_dir() {
    local output_dir="${DOCKER_IMAGES_OUTPUT:-./docker-images}"

    # 转换相对路径为绝对路径
    if [[ "$output_dir" == ./* ]]; then
        output_dir="$(pwd)/${output_dir#./}"
    fi

    # 创建目录
    if ! mkdir -p "$output_dir"; then
        log_error "无法创建输出目录: $output_dir"
        exit 1
    fi

    echo "$output_dir"
}

# 导出镜像
export_image() {
    local image_name="${DOCKER_IMAGE_NAME}:${DOCKER_VERSION}"
    local output_dir
    output_dir=$(create_output_dir)
    local export_file="${output_dir}/supertool_deploy_${DOCKER_VERSION}.tar"
    local compressed_file="${export_file}.gz"

    log "导出Docker镜像..."
    log_info "镜像名称: $image_name"
    log_info "输出目录: $output_dir"
    log_info "导出文件: $export_file"

    # 导出镜像
    if ! docker save "$image_name" -o "$export_file"; then
        log_error "镜像导出失败"
        exit 1
    fi

    # 压缩镜像
    log_info "压缩镜像文件..."
    if [[ -n "${COMPRESS_PASSWORD:-}" ]]; then
        log_info "使用密码压缩..."
        echo "$COMPRESS_PASSWORD" | gzip -c "$export_file" > "$compressed_file"
        rm "$export_file"
    else
        gzip "$export_file"
    fi

    # 显示文件信息
    local file_size
    file_size=$(du -h "$compressed_file" | cut -f1)
    log_success "镜像导出完成"
    log_info "压缩文件: $compressed_file"
    log_info "文件大小: $file_size"

    # 保存文件路径到临时文件，供下一个脚本使用
    echo "$compressed_file" > /tmp/supertool_last_export.txt
}

# 显示帮助
show_help() {
    cat << EOF
SuperTool Docker 镜像导出脚本

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
            echo "Docker导出脚本 v1.0.0"
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
    echo "📦 步骤2: 导出Docker镜像"
    echo "=================================="

    load_config "$config_file"
    check_image
    export_image

    log_success "🎉 镜像导出完成!"
    echo
    echo "下一步: 运行 ./scripts/03-upload-image.sh"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi