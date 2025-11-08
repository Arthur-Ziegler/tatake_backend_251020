#!/usr/bin/env bash
# =============================================================================
# 步骤4.1: 在服务器上解压并加载Docker镜像
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
        "DOCKER_VERSION" "DOCKER_IMAGE_NAME" "SERVER_HOST"
        "SERVER_USER" "DEPLOY_DIR"
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
# 全局SSH选项
SSH_OPTS=""

# 初始化SSH选项
init_ssh_opts() {
    local port="${SERVER_PORT:-22}"
    SSH_OPTS=$(get_ssh_opts "$port" "${SSH_TIMEOUT:-30}" "${SSH_IDENTITY_FILE:-}")
}

check_server_connection() {
    log "检查服务器连接..."

    local server="${SERVER_USER}@${SERVER_HOST}"

    if ! ssh_exec "$server" "echo 'Connection test successful'" "$SSH_OPTS" &>/dev/null; then
        log_error "无法连接到服务器"
        exit 1
    fi

    log_success "服务器连接正常"
}

# 检查服务器Docker环境
check_server_docker() {
    log "检查服务器Docker环境..."

    local server="${SERVER_USER}@${SERVER_HOST}"

    if ! ssh_exec "$server" "docker --version" "$SSH_OPTS" &>/dev/null; then
        log_error "服务器上未安装Docker或权限不足"
        exit 1
    fi

    if ! ssh_exec "$server" "docker info" "$SSH_OPTS" &>/dev/null; then
        log_error "服务器上Docker服务未运行或权限不足"
        exit 1
    fi

    log_success "服务器Docker环境检查通过"
}

# 检查镜像文件
check_image_file() {
    log "检查镜像文件..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"
    local remote_archive="${DEPLOY_DIR}/images/${DOCKER_IMAGE_NAME}_deploy_${DOCKER_VERSION}.tar.gz"

    if ! ssh_exec "$server" "[ -f '$remote_archive' ]" "$SSH_OPTS"; then
        log_error "镜像文件不存在: $remote_archive"
        log_info "请先运行上传脚本: ./scripts/03-upload-image.sh"
        exit 1
    fi

    # 获取文件大小
    local file_size
    file_size=$(ssh_exec "$server" "du -h '$remote_archive' | cut -f1" "$SSH_OPTS")

    log_success "镜像文件检查通过"
    log_info "文件大小: $file_size"
}

# 解压并加载镜像
extract_and_load_image() {
    log "解压并加载Docker镜像..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"
    local remote_archive="${DEPLOY_DIR}/images/${DOCKER_IMAGE_NAME}_deploy_${DOCKER_VERSION}.tar.gz"
    local remote_image_path="${DEPLOY_DIR}/images"
    local image_name="${DOCKER_IMAGE_NAME}:${DOCKER_VERSION}"

    # 创建远程解压脚本
    local extract_script="/tmp/supertool_extract.sh"
    cat > "$extract_script" << EOF
#!/bin/bash
set -euo pipefail

echo "=================================="
echo "📦 开始解压并加载Docker镜像"
echo "=================================="

# 设置变量
remote_image_path="${remote_image_path}"
remote_archive="${remote_archive}"
image_name="${image_name}"
COMPRESS_PASSWORD="${COMPRESS_PASSWORD:-}"

# 进入镜像目录
cd "\$remote_image_path"

echo "📁 解压目录: \$remote_image_path"
echo "📦 镜像文件: \$remote_archive"

# 解压并加载镜像
if [[ -n "\${COMPRESS_PASSWORD}" ]]; then
    echo "🔐 使用密码解压镜像..."
    echo "\${COMPRESS_PASSWORD}" | gunzip -c "\$remote_archive" | docker load
else
    echo "📂 解压镜像文件..."
    gunzip -c "\$remote_archive" | docker load
fi

# 验证镜像加载
if ! docker images "\$image_name" --format "{{.Repository}}:{{.Tag}}" | grep -q "^\$image_name$"; then
    echo "❌ 镜像加载失败"
    echo "请检查镜像文件是否完整"
    exit 1
fi

echo "✅ 镜像加载成功"

# 显示镜像信息
echo "📊 已加载的镜像信息:"
docker images "\$image_name" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

echo "=================================="
echo "🎉 镜像解压加载完成!"
echo "=================================="
EOF

    # 上传解压脚本
    log "上传解压脚本到服务器..."
    local scp_opts
    scp_opts=$(get_scp_opts "$port" "${SSH_TIMEOUT:-30}" "${SSH_IDENTITY_FILE:-}")

    if ! scp_exec "$extract_script" "$server:/tmp/extract_commands.sh" "$scp_opts"; then
        log_error "解压脚本上传失败"
        exit 1
    fi

    # 执行解压脚本
    log "执行镜像解压加载..."
    if ! ssh_exec "$server" "chmod +x /tmp/extract_commands.sh && /tmp/extract_commands.sh" "$SSH_OPTS"; then
        log_error "镜像解压加载失败"
        exit 1
    fi

    # 清理临时脚本
    rm -f "$extract_script"

    log_success "镜像解压加载完成"
}

# 显示帮助
show_help() {
    cat << EOF
SuperTool Docker 镜像解压加载脚本

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
            echo "Docker镜像解压脚本 v1.0.0"
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
    echo "📦 步骤4.1: 解压并加载Docker镜像"
    echo "=================================="

    load_config "$config_file"
    init_ssh_opts
    check_server_connection
    check_server_docker
    check_image_file
    extract_and_load_image

    log_success "🎉 镜像解压加载完成!"
    echo
    echo "下一步: 运行 ./scripts/04b-deploy-container.sh"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi