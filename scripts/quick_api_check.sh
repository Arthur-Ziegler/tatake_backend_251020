#!/bin/bash

# API参数问题快速检查脚本
# 用于快速检测和修复API参数解析问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."

    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi

    if ! command -v uv &> /dev/null; then
        print_error "uv 未安装，请先安装 uv"
        exit 1
    fi

    if ! python3 -c "import httpx" 2>/dev/null; then
        print_info "安装 httpx..."
        uv add httpx
    fi

    print_success "依赖检查完成"
}

# 检查API服务器状态
check_api_server() {
    print_info "检查API服务器状态..."

    API_URL="http://localhost:8000"

    if curl -s "$API_URL/health" > /dev/null 2>&1; then
        print_success "API服务器正在运行 ($API_URL)"
        return 0
    else
        print_warning "API服务器未运行，尝试启动..."

        # 尝试启动API服务器
        print_info "启动API服务器..."
        uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --app-dir src/api > /dev/null 2>&1 &
        SERVER_PID=$!

        # 等待服务器启动
        for i in {1..30}; do
            if curl -s "$API_URL/health" > /dev/null 2>&1; then
                print_success "API服务器启动成功 (PID: $SERVER_PID)"
                echo $SERVER_PID > .api_server.pid
                return 0
            fi
            sleep 1
        done

        print_error "API服务器启动失败"
        return 1
    fi
}

# 运行OpenAPI验证
run_openapi_validation() {
    print_info "运行OpenAPI参数验证..."

    REPORT_FILE="api_validation_$(date +%Y%m%d_%H%M%S).json"

    if uv run python scripts/validate_openapi.py --output "$REPORT_FILE"; then
        print_success "OpenAPI验证通过"
        return 0
    else
        print_error "OpenAPI验证失败"

        if [ -f "$REPORT_FILE" ]; then
            print_info "详细报告已保存到: $REPORT_FILE"

            # 显示主要错误
            if command -v jq &> /dev/null; then
                echo "主要错误:"
                jq -r '.errors[]' "$REPORT_FILE" 2>/dev/null | head -5 | while read error; do
                    echo "  - $error"
                done
            fi
        fi

        return 1
    fi
}

# 运行API健康检查
run_health_check() {
    print_info "运行API健康检查..."

    HEALTH_DIR="health_reports_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$HEALTH_DIR"

    if uv run python scripts/api_health_monitor.py --once --output "$HEALTH_DIR"; then
        print_success "健康检查完成"
        print_info "健康报告已保存到: $HEALTH_DIR"
        return 0
    else
        print_warning "健康检查发现问题"
        return 1
    fi
}

# 运行pytest测试
run_api_tests() {
    print_info "运行API参数验证测试..."

    if uv run pytest tests/validation/test_api_parameters.py -v --tb=short; then
        print_success "API测试通过"
        return 0
    else
        print_error "API测试失败"
        return 1
    fi
}

# 生成综合报告
generate_summary_report() {
    print_info "生成综合报告..."

    REPORT_FILE="api_check_summary_$(date +%Y%m%d_%H%M%S).md"

    cat > "$REPORT_FILE" << EOF
# API参数检查报告

**检查时间**: $(date)
**检查范围**: OpenAPI规范、API健康状态、参数验证测试

## 检查结果

### OpenAPI验证
- 状态: $([ "$OPENAPI_STATUS" = "0" ] && echo "✅ 通过" || echo "❌ 失败")
- 报告文件: ${OPENAPI_REPORT:-"无"}

### API健康检查
- 状态: $([ "$HEALTH_STATUS" = "0" ] && echo "✅ 正常" || echo "⚠️ 发现问题")
- 报告目录: ${HEALTH_DIR:-"无"}

### 参数验证测试
- 状态: $([ "$TEST_STATUS" = "0" ] && echo "✅ 通过" || echo "❌ 失败")

## 建议

EOF

    if [ "$OPENAPI_STATUS" != "0" ]; then
        echo "### 立即修复项" >> "$REPORT_FILE"
        echo "- 检查并修复OpenAPI验证中发现的问题" >> "$REPORT_FILE"
        echo "- 参考报告文件中的详细错误信息" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi

    if [ "$HEALTH_STATUS" != "0" ]; then
        echo "### 性能优化建议" >> "$REPORT_FILE"
        echo "- 检查响应时间较长的端点" >> "$REPORT_FILE"
        echo "- 优化数据库查询和业务逻辑" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi

    if [ "$TEST_STATUS" != "0" ]; then
        echo "### 测试改进建议" >> "$REPORT_FILE"
        echo "- 修复失败的测试用例" >> "$REPORT_FILE"
        echo "- 增强参数验证逻辑" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi

    echo "## 后续行动" >> "$REPORT_FILE"
    echo "1. 修复所有发现的问题" >> "$REPORT_FILE"
    echo "2. 重新运行验证确保问题解决" >> "$REPORT_FILE"
    echo "3. 设置定期监控防止问题重现" >> "$REPORT_FILE"

    print_success "综合报告已生成: $REPORT_FILE"
}

# 清理函数
cleanup() {
    print_info "清理临时文件..."

    # 停止启动的API服务器
    if [ -f ".api_server.pid" ]; then
        SERVER_PID=$(cat .api_server.pid)
        if kill -0 "$SERVER_PID" 2>/dev/null; then
            kill "$SERVER_PID"
            print_info "已停止API服务器 (PID: $SERVER_PID)"
        fi
        rm -f .api_server.pid
    fi
}

# 设置信号处理
trap cleanup EXIT INT TERM

# 主函数
main() {
    echo "=============================================="
    echo "🔍 API参数问题快速检查工具"
    echo "=============================================="
    echo ""

    # 检查是否在项目根目录
    if [ ! -f "pyproject.toml" ] || [ ! -d "src" ]; then
        print_error "请在项目根目录运行此脚本"
        exit 1
    fi

    # 执行检查步骤
    check_dependencies

    if ! check_api_server; then
        print_error "无法启动API服务器，请手动启动后重试"
        exit 1
    fi

    echo ""
    print_info "开始API参数检查..."
    echo ""

    # 运行各项检查
    run_openapi_validation
    OPENAPI_STATUS=$?
    OPENAPI_REPORT=$(ls -t api_validation_*.json 2>/dev/null | head -1)

    echo ""
    run_health_check
    HEALTH_STATUS=$?
    HEALTH_DIR=$(ls -dt health_reports_* 2>/dev/null | head -1)

    echo ""
    run_api_tests
    TEST_STATUS=$?

    echo ""
    echo "=============================================="

    # 生成综合报告
    generate_summary_report

    # 显示最终结果
    if [ "$OPENAPI_STATUS" = "0" ] && [ "$TEST_STATUS" = "0" ]; then
        print_success "🎉 所有检查通过！API参数状态良好。"
        exit 0
    else
        print_error "❌ 发现问题需要修复。请查看上述报告了解详情。"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "API参数问题快速检查工具"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  --no-server    不启动API服务器（假设已运行）"
    echo "  --validation   仅运行OpenAPI验证"
    echo "  --health       仅运行健康检查"
    echo "  --tests        仅运行测试"
    echo ""
    echo "示例:"
    echo "  $0                    # 运行完整检查"
    echo "  $0 --validation       # 仅验证OpenAPI"
    echo "  $0 --no-server        # 使用已运行的服务器"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --no-server)
            SKIP_SERVER=true
            shift
            ;;
        --validation)
            RUN_VALIDATION=true
            shift
            ;;
        --health)
            RUN_HEALTH=true
            shift
            ;;
        --tests)
            RUN_TESTS=true
            shift
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 根据参数执行特定操作
if [ "$RUN_VALIDATION" = "true" ]; then
    check_dependencies
    if [ "$SKIP_SERVER" != "true" ]; then
        check_api_server || exit 1
    fi
    run_openapi_validation
    exit $?
elif [ "$RUN_HEALTH" = "true" ]; then
    check_dependencies
    if [ "$SKIP_SERVER" != "true" ]; then
        check_api_server || exit 1
    fi
    run_health_check
    exit $?
elif [ "$RUN_TESTS" = "true" ]; then
    check_dependencies
    run_api_tests
    exit $?
else
    # 运行完整检查
    main
fi