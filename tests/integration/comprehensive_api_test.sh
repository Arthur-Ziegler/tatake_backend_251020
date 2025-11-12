#!/bin/bash

# TaKeKe Backend 全面API测试脚本
# 覆盖docs/文档中的所有API端点

BASE_URL="http://api.aitodo.it"
TOKEN=""
TEST_PHONE="13800138000"
TEST_CODE="123456"
USER_ID=""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
ISSUES=()

# 测试函数
test_api() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local require_auth=${5:-true}

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "\n${YELLOW}[TEST $TOTAL_TESTS] $name${NC}"
    echo "  $method $endpoint"

    # 构建curl命令
    local curl_cmd="curl -s -X '$method' '$BASE_URL$endpoint' -H 'Content-Type: application/json'"

    if [ "$require_auth" = "true" ] && [ -n "$TOKEN" ]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $TOKEN'"
    fi

    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -d '$data'"
    fi

    # 执行请求
    response=$(eval $curl_cmd 2>&1)
    http_code=$(echo "$response" | jq -r '.code' 2>/dev/null)
    message=$(echo "$response" | jq -r '.message' 2>/dev/null)

    # 判断结果
    if [[ "$http_code" =~ ^2[0-9][0-9]$ ]]; then
        echo -e "  ${GREEN}✓ PASS${NC} - Code: $http_code, Message: $message"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo "$response"
    else
        echo -e "  ${RED}✗ FAIL${NC} - Code: $http_code, Message: $message"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        ISSUES+=("$name: HTTP $http_code - $message")
        echo "$response"
    fi
}

echo "=========================================="
echo "TaKeKe Backend 全面API测试"
echo "=========================================="

# ==================== 1. 认证系统API (4个) ====================
echo -e "\n${YELLOW}========== 认证系统API ==========${NC}"

# 1.1 发送手机验证码
test_api "1.1 发送手机验证码" "POST" "/auth/phone/send-code" \
    "{\"phone\": \"$TEST_PHONE\"}" false

# 1.2 手机验证码登录（使用固定测试码）
response=$(curl -s -X 'POST' "$BASE_URL/auth/phone/verify" \
    -H 'Content-Type: application/json' \
    -d "{\"phone\": \"$TEST_PHONE\", \"code\": \"$TEST_CODE\"}")

http_code=$(echo "$response" | jq -r '.code' 2>/dev/null)
if [[ "$http_code" =~ ^2[0-9][0-9]$ ]]; then
    TOKEN=$(echo "$response" | jq -r '.data.access_token' 2>/dev/null)
    USER_ID=$(echo "$response" | jq -r '.data.user_id' 2>/dev/null)
    echo -e "${GREEN}✓ 登录成功，已获取Token${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗ 登录失败，将尝试微信登录${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    ISSUES+=("手机验证码登录失败: HTTP $http_code")
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# 1.3 微信登录（备用）
if [ -z "$TOKEN" ]; then
    test_api "1.3 微信登录(备用)" "POST" "/auth/wechat/login" \
        "{\"wechat_openid\": \"test_openid_$(date +%s)\"}" false
    # 提取token...
fi

# 1.4 刷新令牌
if [ -n "$TOKEN" ]; then
    refresh_token=$(echo "$response" | jq -r '.data.refresh_token' 2>/dev/null)
    if [ -n "$refresh_token" ] && [ "$refresh_token" != "null" ]; then
        test_api "1.4 刷新访问令牌" "POST" "/auth/token/refresh" \
            "{\"refresh_token\": \"$refresh_token\"}" false
    else
        echo -e "${YELLOW}跳过刷新令牌测试（无refresh_token）${NC}"
    fi
fi

# ==================== 2. 用户管理API (2个) ====================
echo -e "\n${YELLOW}========== 用户管理API ==========${NC}"

# 2.1 获取用户信息
test_api "2.1 获取用户信息" "GET" "/user/profile" "" true

# 2.2 更新用户信息
test_api "2.2 更新用户信息" "PUT" "/user/profile" \
    "{\"nickname\": \"测试用户_$(date +%s)\", \"bio\": \"全面API测试\"}" true

# ==================== 3. 任务管理API (9个) ====================
echo -e "\n${YELLOW}========== 任务管理API ==========${NC}"

# 3.1 创建任务
task_response=$(curl -s -X 'POST' "$BASE_URL/tasks/" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -d '{
        "title": "测试任务_'$(date +%s)'",
        "description": "全面API测试创建的任务",
        "priority": "high",
        "due_date": "2025-12-31T23:59:59Z",
        "tags": ["测试", "API"]
    }')

task_code=$(echo "$task_response" | jq -r '.code' 2>/dev/null)
TOTAL_TESTS=$((TOTAL_TESTS + 1))

if [[ "$task_code" =~ ^2[0-9][0-9]$ ]]; then
    echo -e "${GREEN}✓ 3.1 创建任务成功${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    TASK_ID=$(echo "$task_response" | jq -r '.data.id' 2>/dev/null)
    echo "  Task ID: $TASK_ID"
else
    echo -e "${RED}✗ 3.1 创建任务失败${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    ISSUES+=("创建任务失败: HTTP $task_code")
    echo "$task_response"
fi

# 3.2 查询任务列表
test_api "3.2 查询任务列表" "POST" "/tasks/query" \
    "{\"page\": 1, \"page_size\": 10}" true

# 3.3 获取所有标签
test_api "3.3 获取所有标签" "GET" "/tasks/tags" "" true

# 3.4 更新任务
if [ -n "$TASK_ID" ]; then
    test_api "3.4 更新任务" "PUT" "/tasks/$TASK_ID" \
        "{\"description\": \"已更新的任务描述\", \"priority\": \"low\"}" true
fi

# 3.5 删除任务
if [ -n "$TASK_ID" ]; then
    test_api "3.5 删除任务" "DELETE" "/tasks/$TASK_ID" "" true
fi

# 创建新任务用于完成测试
task2_response=$(curl -s -X 'POST' "$BASE_URL/tasks/" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -d '{
        "title": "待完成任务_'$(date +%s)'",
        "description": "用于测试完成功能",
        "priority": "medium"
    }')
TASK_ID2=$(echo "$task2_response" | jq -r '.data.id' 2>/dev/null)

# 3.6 完成任务
if [ -n "$TASK_ID2" ]; then
    test_api "3.6 完成任务" "POST" "/tasks/$TASK_ID2/complete" "" true
fi

# 3.7 记录专注状态
test_api "3.7 记录专注状态" "POST" "/tasks/focus-status" \
    "{\"focus_status\": \"focused\", \"duration_minutes\": 25}" true

# 3.8 获取番茄钟计数
test_api "3.8 获取番茄钟计数" "GET" "/tasks/pomodoro-count?date_filter=today" "" true

# 3.9 微服务健康检查
test_api "3.9 任务微服务健康检查" "GET" "/tasks/health" "" false

# ==================== 4. Top3管理API (3个) ====================
echo -e "\n${YELLOW}========== Top3管理API ==========${NC}"

# 创建3个任务用于Top3测试
TOP3_TASKS=()
for i in 1 2 3; do
    task_resp=$(curl -s -X 'POST' "$BASE_URL/tasks/" \
        -H 'Content-Type: application/json' \
        -H "Authorization: Bearer $TOKEN" \
        -d "{\"title\": \"Top3任务$i\", \"priority\": \"high\"}")
    task_id=$(echo "$task_resp" | jq -r '.data.id' 2>/dev/null)
    if [ -n "$task_id" ] && [ "$task_id" != "null" ]; then
        TOP3_TASKS+=("$task_id")
    fi
done

# 4.1 设置Top3任务
if [ ${#TOP3_TASKS[@]} -eq 3 ]; then
    today=$(date +%Y-%m-%d)
    test_api "4.1 设置Top3任务" "POST" "/tasks/special/top3" \
        "{\"date\": \"$today\", \"task_ids\": [\"${TOP3_TASKS[0]}\", \"${TOP3_TASKS[1]}\", \"${TOP3_TASKS[2]}\"]}" true

    # 4.2 获取Top3任务
    test_api "4.2 获取Top3任务" "GET" "/tasks/special/top3/$today" "" true
fi

# ==================== 5. 奖励系统API (3个) ====================
echo -e "\n${YELLOW}========== 奖励系统API ==========${NC}"

# 5.1 查看我的奖品
test_api "5.1 查看我的奖品" "GET" "/rewards/prizes" "" true

# 5.2 查看我的积分
test_api "5.2 查看我的积分" "GET" "/rewards/points" "" true

# 5.3 兑换奖品（使用无效兑换码测试错误处理）
test_api "5.3 兑换奖品(测试错误)" "POST" "/rewards/redeem" \
    "{\"code\": \"INVALID_TEST_CODE\"}" true

# ==================== 6. 聊天系统API (4个) ====================
echo -e "\n${YELLOW}========== 聊天系统API ==========${NC}"

# 6.1 查询所有会话列表
test_api "6.1 查询所有会话列表" "GET" "/chat/sessions" "" true

# 6.2 创建会话并发送消息
session_id="test_session_$(date +%s)"
echo -e "\n${YELLOW}[TEST $((TOTAL_TESTS + 1))] 6.2 聊天接口(流式)${NC}"
echo "  POST /chat/sessions/$session_id/chat"
chat_response=$(curl -s -X 'POST' "$BASE_URL/chat/sessions/$session_id/chat" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"message": "你好，这是API测试"}' 2>&1)

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ -n "$chat_response" ]; then
    echo -e "  ${GREEN}✓ PASS${NC} - 收到流式响应"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo "  响应: ${chat_response:0:100}..."
else
    echo -e "  ${RED}✗ FAIL${NC} - 未收到响应"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    ISSUES+=("聊天接口无响应")
fi

# 6.3 查询聊天记录
test_api "6.3 查询聊天记录" "GET" "/chat/sessions/$session_id/messages" "" true

# 6.4 删除会话
test_api "6.4 删除会话" "DELETE" "/chat/sessions/$session_id" "" true

# ==================== 测试结果汇总 ====================
echo -e "\n=========================================="
echo -e "${YELLOW}测试结果汇总${NC}"
echo "=========================================="
echo "总测试数: $TOTAL_TESTS"
echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
echo -e "${RED}失败: $FAILED_TESTS${NC}"
echo -e "通过率: $(awk "BEGIN {printf \"%.2f\", ($PASSED_TESTS/$TOTAL_TESTS)*100}")%"

if [ ${#ISSUES[@]} -gt 0 ]; then
    echo -e "\n${RED}发现的问题:${NC}"
    for issue in "${ISSUES[@]}"; do
        echo "  ❌ $issue"
    done
fi

echo -e "\n=========================================="
echo "测试完成时间: $(date)"
echo "=========================================="
