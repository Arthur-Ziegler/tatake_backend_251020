#!/usr/bin/env bash
# =============================================================================
# 步骤3: 上传镜像到服务器
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
    local required_vars=("DOCKER_VERSION" "SERVER_HOST" "SERVER_USER")
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
    log "检查上传依赖..."

    if ! command -v scp &> /dev/null; then
        log_error "scp未安装或不在PATH中"
        exit 1
    fi

    if ! command -v ssh &> /dev/null; then
        log_error "ssh未安装或不在PATH中"
        exit 1
    fi

    log_success "依赖检查通过"
}

# 检查导出文件
check_export_file() {
    # 设置默认输出目录
    local output_dir="${DOCKER_IMAGES_OUTPUT:-./docker-images}"

    # 转换相对路径为绝对路径
    if [[ "$output_dir" == ./* ]]; then
        output_dir="$(pwd)/${output_dir#./}"
    fi

    local export_file="${output_dir}/${DOCKER_IMAGE_NAME}_deploy_${DOCKER_VERSION}.tar.gz"

    # 先尝试读取临时文件中的路径
    if [[ -f "/tmp/${DOCKER_IMAGE_NAME}_last_export.txt" ]]; then
        export_file=$(cat "/tmp/${DOCKER_IMAGE_NAME}_last_export.txt")
    fi

    if [[ ! -f "$export_file" ]]; then
        echo "$export_file"
        return 1
    fi

    echo "$export_file"
}

# 测试服务器连接
test_server_connection() {
    log "测试服务器连接..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"

    if ! ssh_exec "$server" "echo 'Connection test successful'" "$SSH_OPTS" &>/dev/null; then
        log_error "无法连接到服务器: $server"
        log_info "请检查:"
        log_info "  - 服务器地址和端口是否正确"
        log_info "  - SSH服务是否运行"
        log_info "  - 用户名和密码是否正确"
        log_info "  - 防火墙设置"
        exit 1
    fi

    log_success "服务器连接测试通过"
}

# 检查服务器Docker环境
check_server_docker() {
    log "检查服务器Docker环境..."

    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"

    if ! ssh_exec "$server" "docker --version" "$SSH_OPTS" &>/dev/null; then
        log_error "服务器上未安装Docker或权限不足"
        log_info "请在服务器上安装Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! ssh_exec "$server" "docker info" "$SSH_OPTS" &>/dev/null; then
        log_error "服务器上Docker服务未运行或权限不足"
        log_info "请启动Docker服务: sudo systemctl start docker"
        exit 1
    fi

    log_success "服务器Docker环境检查通过"
}

# 上传镜像文件
upload_image() {
    local local_file="$1"
    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"
    local remote_dir="${DEPLOY_DIR}/images"
    local remote_file="${remote_dir}/${DOCKER_IMAGE_NAME}_deploy_${DOCKER_VERSION}.tar.gz"

    log "上传镜像文件到服务器..."
    log_info "本地文件: $local_file"
    log_info "目标服务器: $server"
    log_info "远程路径: $remote_file"

    # 先创建远程目录
    if ! ssh_exec "$server" "mkdir -p '$remote_dir'" "$SSH_OPTS"; then
        log_error "无法创建远程目录: $remote_dir"
        exit 1
    fi

    # 使用scp上传文件
    local scp_opts
    scp_opts=$(get_scp_opts "$port" "${SSH_TIMEOUT:-30}" "${SSH_IDENTITY_FILE:-}")

    if ! scp_exec "$local_file" "$server:$remote_file" "$scp_opts"; then
        log_error "文件上传失败"
        exit 1
    fi

    log_success "文件上传完成"
}

# 上传环境文件（如果需要）
upload_env_file() {
    local server="${SERVER_USER}@${SERVER_HOST}"
    local port="${SERVER_PORT:-22}"
    local remote_env_dir="${DEPLOY_DIR}"

    log "检查环境文件..."

    # 检查服务器上是否已有环境文件
    if ssh_exec "$server" "[ ! -f '${remote_env_dir}/.env' ]" "$SSH_OPTS"; then
        if [[ -f ".env" ]]; then
            log "上传环境文件..."
            # 创建部署目录
            ssh_exec "$server" "mkdir -p '$remote_env_dir'" "$SSH_OPTS"

            # 上传环境文件
            local scp_opts
            scp_opts=$(get_scp_opts "$port" "${SSH_TIMEOUT:-30}" "${SSH_IDENTITY_FILE:-}")

            if ! scp_exec ".env" "$server:${remote_env_dir}/.env" "$scp_opts"; then
                log_error "环境文件上传失败"
                exit 1
            fi
            log_success "环境文件上传完成"
        else
            log_error "本地.env文件不存在，且服务器上也没有.env文件"
            exit 1
        fi
    else
        log_info "服务器上已存在环境文件，跳过上传"
    fi
}

# 显示帮助
show_help() {
    cat << EOF
SuperTool Docker 镜像上传脚本

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
            echo "Docker上传脚本 v1.0.0"
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
    echo "⬆️  步骤3: 上传镜像到服务器"
    echo "=================================="

    load_config "$config_file"
    check_dependencies

    log "检查导出文件..."
    local export_file
    export_file=$(check_export_file)

    if [[ ! -f "$export_file" ]]; then
        log_error "导出文件不存在: $export_file"
        log_info "请先运行: ./scripts/02-export-image.sh"
        exit 1
    fi

    local file_size
    file_size=$(du -h "$export_file" | cut -f1)

    # 检查是否从临时文件读取了路径
    if [[ -f "/tmp/${DOCKER_IMAGE_NAME}_last_export.txt" ]]; then
        local temp_file_path
        temp_file_path=$(cat "/tmp/${DOCKER_IMAGE_NAME}_last_export.txt")
        if [[ "$export_file" == "$temp_file_path" ]]; then
            log_info "从临时文件读取路径: $export_file"
        fi
    fi

    log_info "找到导出文件: $export_file"
    log_info "文件大小: $file_size"

    init_ssh_opts
    test_server_connection
    check_server_docker
    upload_image "$export_file"
    upload_env_file

    log_success "🎉 镜像上传完成!"
    echo
    echo "下一步: 运行 ./scripts/04-deploy-image.sh"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi