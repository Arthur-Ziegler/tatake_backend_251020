#!/bin/bash

# TaKeKe API 全面测试脚本
# 测试所有25+个API端点

API_BASE="http://localhost:8001"
TEST_RESULTS=()
FAILED_TESTS=()
AUTH_TOKEN=""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 测试函数
test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local expected_code="$4"
    local headers="$5"
    local description="$6"

    log_info "测试: $method $endpoint - $description"

    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" \
            -X "$method" \
            -H "Content-Type: application/json" \
            ${headers:+-H "$headers"} \
            -d "$data" \
            "$API_BASE$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" \
            -X "$method" \
            -H "Content-Type: application/json" \
            ${headers:+-H "$headers"} \
            "$API_BASE$endpoint")
    fi

    body=$(echo "$response" | head -n -1)
    http_code=$(echo "$response" | tail -n 1)

    if [ "$http_code" = "$expected_code" ]; then
        log_success "✅ $method $endpoint - HTTP $http_code"
        TEST_RESULTS+=("✅ $method $endpoint - $description (HTTP $http_code)")

        # 检查响应格式
        if echo "$body" | jq . > /dev/null 2>&1; then
            # 验证必要字段
            if echo "$body" | jq -e 'has("code") and has("message")' > /dev/null; then
                log_success "响应格式正确: code, message字段存在"
            else
                log_warning "响应格式不完整: 缺少必要字段"
                TEST_RESULTS+=("⚠️  $method $endpoint - 响应格式不完整")
            fi
        else
            log_warning "响应不是有效的JSON格式"
            TEST_RESULTS+=("⚠️  $method $endpoint - 响应不是JSON格式")
        fi

    else
        log_error "❌ $method $endpoint - 期望 HTTP $expected_code, 实际 $http_code"
        TEST_RESULTS+=("❌ $method $endpoint - $description (期望: $expected_code, 实际: $http_code)")
        FAILED_TESTS+=("$method $endpoint - $description")

        # 显示错误响应
        echo -e "${RED}错误响应:${NC} $body"
    fi

    echo "----------------------------------------"
    sleep 1
}

echo "🚀 开始 TaKeKe API 全面测试"
echo "API服务器: $API_BASE"
echo "========================================"

# 1. 系统端点测试
echo -e "\n${BLUE}1. 系统端点测试${NC}"

test_endpoint "GET" "/health" "" "200" "" "健康检查"
test_endpoint "GET" "/docs" "" "200" "" "API文档"
test_endpoint "GET" "/openapi.json" "" "200" "" "OpenAPI规范"

# 2. 认证系统测试
echo -e "\n${BLUE}2. 认证系统测试${NC}"

# 微信登录测试
wechat_data='{"wechat_openid": "test_openid_' $(date +%s) '"}'
test_endpoint "POST" "/auth/wechat/login" "$wechat_data" "200" "" "微信登录（自动注册）"

# 提取token用于后续测试
response=$(curl -s -X POST -H "Content-Type: application/json" \
    -d "$wechat_data" \
    "$API_BASE/auth/wechat/login")
AUTH_TOKEN=$(echo "$response" | jq -r '.data.access_token // empty')

if [ -n "$AUTH_TOKEN" ] && [ "$AUTH_TOKEN" != "null" ]; then
    log_success "✅ 获取到认证Token: ${AUTH_TOKEN:0:20}..."
    AUTH_HEADER="Authorization: Bearer $AUTH_TOKEN"
else
    log_warning "⚠️  无法获取认证Token，将使用无token方式测试需要认证的端点"
    AUTH_HEADER=""
fi

# Token刷新测试
if [ -n "$AUTH_TOKEN" ]; then
    refresh_data='{"refresh_token": "dummy_refresh_token"}'
    test_endpoint "POST" "/auth/token/refresh" "$refresh_data" "400" "$AUTH_HEADER" "Token刷新（无效token）"
fi

# 手机验证码发送测试
phone_data='{"phone": "13800138000"}'
test_endpoint "POST" "/auth/phone/send-code" "$phone_data" "200" "" "发送手机验证码"

# 手机验证码验证测试
verify_data='{"phone": "13800138000", "code": "123456"}'
test_endpoint "POST" "/auth/phone/verify" "$verify_data" "400" "" "手机验证码登录（错误验证码）"

# 3. 用户管理测试
echo -e "\n${BLUE}3. 用户管理测试${NC}"

test_endpoint "GET" "/user/profile" "" "401" "" "获取用户信息（无token）"

if [ -n "$AUTH_HEADER" ]; then
    test_endpoint "GET" "/user/profile" "" "200" "$AUTH_HEADER" "获取用户信息（有token）"

    # 更新用户信息测试
    update_data='{"nickname": "测试用户", "theme": "dark"}'
    test_endpoint "PUT" "/user/profile" "$update_data" "200" "$AUTH_HEADER" "更新用户信息"
else
    test_endpoint "GET" "/user/profile" "" "401" "" "获取用户信息（无效token）"
fi

# 4. 任务管理测试
echo -e "\n${BLUE}4. 任务管理测试${NC}"

# 创建任务测试
if [ -n "$AUTH_HEADER" ]; then
    task_data='{"title": "测试任务", "description": "这是一个测试任务", "priority": "high"}'
    test_endpoint "POST" "/tasks" "$task_data" "200" "$AUTH_HEADER" "创建任务"

    # 查询任务列表测试
    query_data='{"page": 1, "page_size": 10}'
    test_endpoint "POST" "/tasks/query" "$query_data" "200" "$AUTH_HEADER" "查询任务列表"

    # 测试其他任务相关端点
    test_endpoint "GET" "/tasks/pomodoro-count" "" "200" "$AUTH_HEADER" "查看番茄钟计数"
else
    test_endpoint "POST" "/tasks" '{"title": "测试"}' "401" "" "创建任务（无token）"
    test_endpoint "POST" "/tasks/query" '{"page": 1}' "401" "" "查询任务（无token）"
fi

# 5. Top3管理测试
echo -e "\n${BLUE}5. Top3管理测试${NC}"

if [ -n "$AUTH_HEADER" ]; then
    # 设置Top3测试
    top3_data='{"date": "2025-11-12", "task_ids": ["test-task-id-1", "test-task-id-2"]}'
    test_endpoint "POST" "/tasks/special/top3" "$top3_data" "400" "$AUTH_HEADER" "设置Top3（无效任务ID）"

    # 查询Top3测试
    test_endpoint "GET" "/tasks/special/top3/2025-11-12" "" "200" "$AUTH_HEADER" "查询Top3"
else
    test_endpoint "GET" "/tasks/special/top3/2025-11-12" "" "401" "" "查询Top3（无token）"
fi

# 6. 专注系统测试
echo -e "\n${BLUE}6. 专注系统测试${NC}"

if [ -n "$AUTH_HEADER" ]; then
    # 开始专注会话测试
    focus_data='{"task_id": "test-task-id", "session_type": "focus"}'
    test_endpoint "POST" "/focus/sessions" "$focus_data" "400" "$AUTH_HEADER" "开始专注会话（无效任务ID）"

    # 查询专注会话列表
    test_endpoint "GET" "/focus/sessions" "" "200" "$AUTH_HEADER" "查询专注会话列表"

    # 查看番茄数量
    test_endpoint "GET" "/focus/pomodoro-count" "" "200" "$AUTH_HEADER" "查看我的番茄数量"
else
    test_endpoint "GET" "/focus/sessions" "" "401" "" "查询专注会话（无token）"
fi

# 7. 聊天系统测试
echo -e "\n${BLUE}7. 聊天系统测试${NC}"

if [ -n "$AUTH_HEADER" ]; then
    # 查询会话列表
    test_endpoint "GET" "/chat/sessions" "" "200" "$AUTH_HEADER" "查询聊天会话列表"

    # 查询聊天记录测试（需要session_id）
    test_endpoint "GET" "/chat/sessions/test-session-id/messages" "" "404" "$AUTH_HEADER" "查询聊天记录（不存在的会话）"
else
    test_endpoint "GET" "/chat/sessions" "" "401" "" "查询聊天会话（无token）"
fi

# 8. 奖励系统测试
echo -e "\n${BLUE}8. 奖励系统测试${NC}"

if [ -n "$AUTH_HEADER" ]; then
    # 查看奖品
    test_endpoint "GET" "/rewards/prizes" "" "200" "$AUTH_HEADER" "查看我的奖品"

    # 查看积分
    test_endpoint "GET" "/rewards/points" "" "200" "$AUTH_HEADER" "查看我的积分"

    # 兑换奖品测试
    redeem_data='{"code": "test-redeem-code"}'
    test_endpoint "POST" "/rewards/redeem" "$redeem_data" "400" "$AUTH_HEADER" "兑换奖品（无效兑换码）"
else
    test_endpoint "GET" "/rewards/prizes" "" "401" "" "查看奖品（无token）"
    test_endpoint "GET" "/rewards/points" "" "401" "" "查看积分（无token）"
fi

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}📊 测试结果汇总${NC}"
echo -e "${BLUE}========================================${NC}"

total_tests=${#TEST_RESULTS[@]}
failed_tests=${#FAILED_TESTS[@]}
passed_tests=$((total_tests - failed_tests))

echo -e "总测试数: $total_tests"
echo -e "${GREEN}通过: $passed_tests${NC}"
echo -e "${RED}失败: $failed_tests${NC}"

if [ $failed_tests -eq 0 ]; then
    log_success "🎉 所有测试通过！"
else
    echo -e "\n${RED}失败的测试:${NC}"
    for failed_test in "${FAILED_TESTS[@]}"; do
        echo -e "${RED}❌ $failed_test${NC}"
    done
fi

echo -e "\n${BLUE}详细测试结果:${NC}"
for result in "${TEST_RESULTS[@]}"; do
    echo "$result"
done

# 生成测试报告
report_file="api_test_report_$(date +%Y%m%d_%H%M%S).txt"
{
    echo "TaKeKe API 测试报告"
    echo "生成时间: $(date)"
    echo "API服务器: $API_BASE"
    echo "========================================"
    echo "总测试数: $total_tests"
    echo "通过: $passed_tests"
    echo "失败: $failed_tests"
    echo ""
    echo "详细结果:"
    for result in "${TEST_RESULTS[@]}"; do
        echo "$result"
    done
} > "$report_file"

echo -e "\n${GREEN}✅ 测试完成！报告已保存到: $report_file${NC}"