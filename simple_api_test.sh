#!/bin/bash

API_BASE="http://localhost:8001"
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

test_api() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local expected_code="$4"
    local description="$5"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    echo "测试 $TOTAL_TESTS: $method $endpoint - $description"

    if [ -n "$data" ]; then
        http_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_BASE$endpoint")
    else
        http_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            "$API_BASE$endpoint")
    fi

    if [ "$http_code" = "$expected_code" ]; then
        echo "✅ 通过 - HTTP $http_code"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "❌ 失败 - 期望 $expected_code, 实际 $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    echo "---"
}

echo "🚀 TaKeKe API 简化测试"
echo "API服务器: $API_BASE"
echo "================================"

# 1. 系统端点
echo "1. 系统端点测试"
test_api "GET" "/health" "" "200" "健康检查"
test_api "GET" "/docs" "" "200" "API文档"

# 2. 认证端点
echo "2. 认证端点测试"
test_api "POST" "/auth/wechat/login" '{"wechat_openid": "test_openid_123"}' "422" "微信登录（格式错误）"
test_api "POST" "/auth/phone/send-code" '{"phone": "13800138000"}' "502" "发送验证码（微服务不可用）"
test_api "POST" "/auth/phone/verify" '{"phone": "13800138000", "code": "123456"}' "502" "验证验证码（微服务不可用）"

# 3. 用户管理端点
echo "3. 用户管理端点测试"
test_api "GET" "/user/profile" "" "401" "获取用户信息（无token）"
test_api "PUT" "/user/profile" '{"nickname": "test"}' "401" "更新用户信息（无token）"

# 4. 任务管理端点
echo "4. 任务管理端点测试"
test_api "GET" "/tasks" "" "405" "获取任务列表（方法不允许）"
test_api "POST" "/tasks" '{"title": "test task"}' "401" "创建任务（无token）"
test_api "POST" "/tasks/query" '{"page": 1}' "401" "查询任务（无token）"

# 5. Top3端点
echo "5. Top3端点测试"
test_api "GET" "/tasks/special/top3/2025-11-12" "" "401" "查询Top3（无token）"
test_api "POST" "/tasks/special/top3" '{"date": "2025-11-12", "task_ids": []}' "401" "设置Top3（无token）"

# 6. 专注系统端点
echo "6. 专注系统端点测试"
test_api "GET" "/focus/sessions" "" "401" "获取专注会话（无token）"
test_api "POST" "/focus/sessions" '{"task_id": "test"}' "401" "开始专注会话（无token）"
test_api "GET" "/focus/pomodoro-count" "" "401" "查看番茄数量（无token）"

# 7. 聊天系统端点
echo "7. 聊天系统端点测试"
test_api "GET" "/chat/sessions" "" "401" "获取聊天会话（无token）"
test_api "GET" "/chat/sessions/test/messages" "" "401" "获取聊天记录（无token）"

# 8. 奖励系统端点
echo "8. 奖励系统端点测试"
test_api "GET" "/rewards/prizes" "" "401" "查看奖品（无token）"
test_api "GET" "/rewards/points" "" "401" "查看积分（无token）"
test_api "POST" "/rewards/redeem" '{"code": "test"}' "401" "兑换奖品（无token）"

# 9. 其他测试
echo "9. 其他测试"
test_api "GET" "/nonexistent" "" "404" "不存在的端点"
test_api "POST" "/auth/wechat/login" '' "422" "空数据请求"

echo "================================"
echo "📊 测试结果汇总"
echo "总测试数: $TOTAL_TESTS"
echo "通过: $PASSED_TESTS"
echo "失败: $FAILED_TESTS"

SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo "成功率: $SUCCESS_RATE%"

if [ $FAILED_TESTS -eq 0 ]; then
    echo "🎉 所有测试都通过了！"
else
    echo "⚠️  有 $FAILED_TESTS 个测试失败"
fi