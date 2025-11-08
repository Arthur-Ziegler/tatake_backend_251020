#!/usr/bin/env bash
# =============================================================================
# 完整部署脚本 - 依次执行所有部署步骤
# =============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_info() {
    echo -e "${CYAN}[ℹ]${NC} $1"
}

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 显示帮助
show_help() {
    cat << 'EOF'
SuperTool Docker 完整部署脚本

使用方法:
    $0 [选项] [配置文件]

选项:
    --help, -h          显示此帮助信息
    --version, -v       显示版本信息
    --dry-run           预演模式，显示将要执行的步骤
    --skip-tests        跳过最后的测试步骤
    --stop-at N         在第N步后停止 (1-5)
    --start-from N      从第N步开始 (1-5)

步骤说明:
    1. 构建Docker镜像
    2. 导出Docker镜像
    3. 上传到服务器
    4. 在服务器部署
    5. 测试部署结果

示例:
    $0                          # 执行所有步骤
    $0 prod.env                 # 使用生产环境配置
    $0 --dry-run                # 预演模式
    $0 --skip-tests             # 跳过测试
    $0 --stop-at 3              # 只执行前3步
    $0 --start-from 3           # 从第3步开始执行

EOF
}

# 显示步骤信息
show_step_info() {
    local step_num="$1"
    local step_name="$2"
    local step_desc="$3"

    echo
    echo "=================================="
    echo -e "${PURPLE}步骤 $step_num: $step_name${NC}"
    echo "=================================="
    echo -e "${CYAN}$step_desc${NC}"
    echo
}

# 执行步骤脚本
execute_step() {
    local step_script="$1"
    local step_name="$2"
    local config_file="$3"

    if [[ ! -f "$step_script" ]]; then
        log_error "步骤脚本不存在: $step_script"
        exit 1
    fi

    log_info "执行脚本: $step_script"

    if ! bash "$step_script" "$config_file"; then
        log_error "步骤执行失败: $step_name"
        log_error "部署过程中断"
        exit 1
    fi

    log_success "步骤完成: $step_name"
}

# 主函数
main() {
    local config_file="deploy.env"
    local dry_run=false
    local skip_tests=false
    local stop_at=5
    local start_from=1

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --version|-v)
                echo "SuperTool Docker 完整部署脚本 v1.0.0"
                exit 0
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --skip-tests)
                skip_tests=true
                stop_at=4
                shift
                ;;
            --stop-at)
                if [[ -n "${2:-}" && "$2" =~ ^[1-5]$ ]]; then
                    stop_at="$2"
                    shift 2
                else
                    log_error "--stop-at 需要一个1-5之间的数字"
                    exit 1
                fi
                ;;
            --start-from)
                if [[ -n "${2:-}" && "$2" =~ ^[1-5]$ ]]; then
                    start_from="$2"
                    shift 2
                else
                    log_error "--start-from 需要一个1-5之间的数字"
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

    # 显示横幅
    echo
    echo "=================================="
    echo "🚀 SuperTool Docker 完整部署脚本 v1.0.0"
    echo "=================================="
    echo
    log_info "配置文件: $config_file"
    log_info "执行模式: $([ "$dry_run" = true ] && echo "预演模式" || echo "正式部署")"
    log_info "执行范围: 步骤 $start_from 到 $stop_at"
    echo

    # 检查配置文件
    if [[ "$dry_run" != true && ! -f "$config_file" ]]; then
        log_error "配置文件不存在: $config_file"
        log_info "请复制 deploy.env.example 为 deploy.env 并配置相应参数"
        exit 1
    fi

    # 定义部署步骤
    declare -a steps=(
        [1]="01-build-image.sh:构建Docker镜像:构建包含SuperTool应用和所有依赖的Docker镜像"
        [2]="02-export-image.sh:导出Docker镜像:将构建好的镜像导出为压缩文件"
        [3]="03-upload-image.sh:上传到服务器:将镜像文件和环境配置上传到目标服务器"
        [4]="04-deploy-image.sh:在服务器部署:在服务器上加载镜像并启动容器"
        [5]="05-test-deployment.sh:测试部署结果:验证服务是否正常运行并提供功能测试"
    )

    # 预演模式
    if [[ "$dry_run" = true ]]; then
        log_info "预演模式 - 以下是将要执行的步骤:"
        for ((i=start_from; i<=stop_at; i++)); do
            if [[ -n "${steps[$i]:-}" ]]; then
                IFS=':' read -r script name desc <<< "${steps[$i]}"
                echo "  步骤 $i: $name"
                echo "    脚本: scripts/$script"
                echo "    描述: $desc"
                echo
            fi
        done
        log_success "预演完成"
        exit 0
    fi

    # 检查脚本目录
    if [[ ! -d "$SCRIPT_DIR" ]]; then
        log_error "脚本目录不存在: $SCRIPT_DIR"
        exit 1
    fi

    # 执行部署步骤
    local start_time=$(date +%s)
    local success=true

    for ((i=start_from; i<=stop_at; i++)); do
        if [[ -n "${steps[$i]:-}" ]]; then
            IFS=':' read -r script name desc <<< "${steps[$i]}"
            show_step_info "$i" "$name" "$desc"

            local step_script="$SCRIPT_DIR/$script"
            execute_step "$step_script" "$name" "$config_file"

            log_success "步骤 $i 完成"
            echo
        fi
    done

    # 计算执行时间
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    # 显示最终结果
    echo
    echo "=================================="
    echo "🎉 部署完成!"
    echo "=================================="
    echo "⏱️  执行时间: ${minutes}分${seconds}秒"
    echo "📁 配置文件: $config_file"
    echo "🖥️  目标服务器: ${SERVER_HOST:-'未配置'}"
    echo "🐳 容器名称: ${CONTAINER_NAME:-'未配置'}"
    echo "🌐 访问地址: http://${SERVER_HOST:-'your-server'}:${HOST_PORT:-20001}"
    echo "📚 API文档: http://${SERVER_HOST:-'your-server'}:${HOST_PORT:-20001}/docs"
    echo "=================================="
    echo

    if [[ "$success" = true ]]; then
        log_success "🎊 SuperTool服务已成功部署并运行!"
        echo
        log_info "下一步:"
        echo "  1. 访问服务地址验证功能"
        echo "  2. 查看API文档了解接口"
        echo "  3. 根据需要调整配置"
        echo "  4. 设置监控和日志"
    else
        log_error "部署过程中遇到错误，请检查日志并修复问题"
        exit 1
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi