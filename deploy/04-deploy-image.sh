#!/usr/bin/env bash
# =============================================================================
# 步骤4: 在服务器上部署镜像 (主控脚本)
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

# 检查脚本依赖
check_script_dependencies() {
    log "检查脚本依赖..."

    local scripts=(
        "04a-extract-image.sh"
        "04b-deploy-container.sh"
        "04c-health-check.sh"
    )

    for script in "${scripts[@]}"; do
        if [[ ! -f "scripts/$script" ]]; then
            log_error "脚本文件不存在: scripts/$script"
            exit 1
        fi
        if [[ ! -x "scripts/$script" ]]; then
            log_info "设置执行权限: scripts/$script"
            chmod +x "scripts/$script"
        fi
    done

    log_success "脚本依赖检查通过"
}

# 执行步骤
execute_step() {
    local step_script="$1"
    local step_name="$2"
    local config_file="$3"

    log "执行步骤: $step_name"

    if ! bash "scripts/$step_script" "$config_file"; then
        log_error "步骤失败: $step_name"
        exit 1
    fi

    log_success "步骤完成: $step_name"
    echo
}

# 显示帮助
show_help() {
    cat << EOF
SuperTool Docker 镜像部署主控脚本

使用方法:
    $0 [选项] [配置文件]

选项:
    --help, -h              显示帮助信息
    --version, -v           显示版本信息
    --skip-health-check     跳过健康检查
    --start-from STEP       从指定步骤开始 (extract, deploy, health)
    --stop-at STEP          在指定步骤停止 (extract, deploy, health)

步骤说明:
    extract  - 解压并加载Docker镜像 (04a-extract-image.sh)
    deploy   - 部署Docker容器 (04b-deploy-container.sh)
    health   - 健康检查和清理 (04c-health-check.sh)

参数:
    配置文件    部署配置文件 (默认: deploy.env)

示例:
    $0                          # 执行完整部署流程
    $0 prod.env                # 使用生产环境配置
    $0 --start-from deploy     # 从容器部署步骤开始
    $0 --stop-at extract       # 只执行镜像解压步骤
    $0 --skip-health-check     # 跳过健康检查

EOF
}

# 主函数
main() {
    local config_file="deploy.env"
    local start_from="extract"
    local stop_at="health"
    local skip_health_check=false

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --version|-v)
                echo "Docker部署主控脚本 v1.0.0"
                exit 0
                ;;
            --skip-health-check)
                skip_health_check=true
                shift
                ;;
            --start-from)
                if [[ -n "${2:-}" ]]; then
                    start_from="$2"
                    shift 2
                else
                    log_error "--start-from 需要指定步骤名称"
                    exit 1
                fi
                ;;
            --stop-at)
                if [[ -n "${2:-}" ]]; then
                    stop_at="$2"
                    shift 2
                else
                    log_error "--stop-at 需要指定步骤名称"
                    exit 1
                fi
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

    # 验证步骤名称
    local valid_steps=("extract" "deploy" "health")
    if [[ ! " ${valid_steps[*]} " =~ " $start_from " ]]; then
        log_error "无效的起始步骤: $start_from"
        log_info "有效步骤: ${valid_steps[*]}"
        exit 1
    fi

    if [[ ! " ${valid_steps[*]} " =~ " $stop_at " ]]; then
        log_error "无效的停止步骤: $stop_at"
        log_info "有效步骤: ${valid_steps[*]}"
        exit 1
    fi

    echo "=================================="
    echo "🚀 步骤4: 在服务器上部署镜像"
    echo "=================================="
    log_info "配置文件: $config_file"
    log_info "起始步骤: $start_from"
    log_info "停止步骤: $stop_at"

    load_config "$config_file"
    check_script_dependencies

    # 定义步骤执行顺序
    local -A step_scripts=(
        ["extract"]="04a-extract-image.sh"
        ["deploy"]="04b-deploy-container.sh"
        ["health"]="04c-health-check.sh"
    )

    local -A step_names=(
        ["extract"]="解压并加载Docker镜像"
        ["deploy"]="部署Docker容器"
        ["health"]="健康检查和清理"
    )

    # 执行步骤
    local executing=false
    for step in "extract" "deploy" "health"; do
        if [[ "$step" == "$start_from" ]]; then
            executing=true
        fi

        if [[ "$executing" == true ]]; then
            if [[ "$step" == "health" && "$skip_health_check" == true ]]; then
                log_info "跳过健康检查步骤"
                break
            fi

            execute_step "${step_scripts[$step]}" "${step_names[$step]}" "$config_file"

            if [[ "$step" == "$stop_at" ]]; then
                log_info "在步骤 '$stop_at' 停止"
                break
            fi
        fi
    done

    log_success "🎉 镜像部署完成!"
    echo
    echo "✅ SuperTool服务已成功部署!"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi