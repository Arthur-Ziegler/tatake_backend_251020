#!/bin/bash

# API测试脚本
TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiYmFmYzRhMS04OTNiLTQwYzktOGRkNi00MTU5MzVhMmMyMWYiLCJpc19ndWVzdCI6ZmFsc2UsImp3dF92ZXJzaW9uIjoyLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiaWF0IjoxNzYzMTQ4OTc2LCJleHAiOjE3NjMxNTA3NzYsImp0aSI6ImE3MmNmZTYyLTg1YTItNDhhOS05OTM5LTJmNTVhM2E0MmVlZiJ9.H4jLb2ZqziE0bfw8jy9xneQslGMsJBqxsIGqUyyeHli9OVbjJVobQFQGn3fk_WScx1c2hdMEGHvIKCsxllmf68ft-CUQYQJWqAEVwuhnmgQZcyQiDJqpNLHBjhWB1XS2nq9Hl09TDYSzv0jd0cHKau115lOgRDErwB1XkpnPBLRWGsvpqXnxiAHbi_54R3O4ghTk599njUuvNiV6Jjwe73troEFY0h7nb6P2SdTRz1_0acUQKJ7h_iTKEJdTuk9Ry9yOGdzqWKef0YkLVTbxQ8IyAIy4L1Mh1XSDH6-8TrpECiAZUck0GV-5eR8jQ07OnOE3ubU148YbLuB6JfDrYA"
BASE_URL="http://localhost:8001"

# 测试1: 创建任务
echo "====== 测试1: 创建任务 POST /tasks/ ======"
TASK_RESPONSE=$(curl -s -X POST "$BASE_URL/tasks/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"测试任务1","description":"这是一个测试任务","status":"pending","priority":"high","tags":["测试","API"],"due_date":"2025-12-31","planned_start_time":"2025-12-01T09:00:00Z","planned_end_time":"2025-12-20T18:00:00Z"}')
echo "$TASK_RESPONSE" | jq .
TASK_ID=$(echo "$TASK_RESPONSE" | jq -r '.data.id')
echo "创建的任务ID: $TASK_ID"
echo ""

# 测试2: 查询任务列表
echo "====== 测试2: 查询任务列表 GET /tasks/ ======"
curl -s -X GET "$BASE_URL/tasks/?page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo ""

# 测试3: 获取标签
echo "====== 测试3: 获取标签 GET /tasks/tags ======"
curl -s -X GET "$BASE_URL/tasks/tags" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo ""

# 测试4: 更新任务
echo "====== 测试4: 更新任务 PUT /tasks/{id} ======"
curl -s -X PUT "$BASE_URL/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"更新后的任务","description":"更新后的描述","status":"in_progress","priority":"medium","tags":["已更新"]}' | jq .
echo ""

# 测试5: 完成任务
echo "====== 测试5: 完成任务 POST /tasks/{id}/complete ======"
COMPLETE_RESPONSE=$(curl -s -X POST "$BASE_URL/tasks/$TASK_ID/complete" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}')
echo "$COMPLETE_RESPONSE" | jq .
echo ""

# 测试6: 删除任务
echo "====== 测试6: 删除任务 DELETE /tasks/{id} ======"
curl -s -X DELETE "$BASE_URL/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo ""

# 测试7: 创建三个任务用于Top3
echo "====== 测试7: 创建3个任务用于Top3测试 ======"
for i in 1 2 3; do
  RESPONSE=$(curl -s -X POST "$BASE_URL/tasks/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"Top3任务$i\",\"description\":\"这是Top3测试任务$i\",\"status\":\"pending\",\"priority\":\"high\"}")
  TASK_ID_$i=$(echo "$RESPONSE" | jq -r '.data.id')
  eval "TASK_ID_$i=\$(echo \$RESPONSE | jq -r '.data.id')"
  echo "创建任务$i: $(eval echo \$TASK_ID_$i)"
done
echo ""

# 测试8: 设置Top3
echo "====== 测试8: 设置Top3 POST /tasks/special/top3 ======"
curl -s -X POST "$BASE_URL/tasks/special/top3" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"date\":\"2025-12-01\",\"task_ids\":[\"$TASK_ID_1\",\"$TASK_ID_2\",\"$TASK_ID_3\"]}" | jq .
echo ""

# 测试9: 查看Top3
echo "====== 测试9: 查看Top3 GET /tasks/special/top3/{date} ======"
curl -s -X GET "$BASE_URL/tasks/special/top3/2025-12-01" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo ""

# 测试10: 记录专注状态
echo "====== 测试10: 记录专注状态 POST /tasks/focus-status ======"
curl -s -X POST "$BASE_URL/tasks/focus-status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"focus_status\":\"focused\",\"duration_minutes\":25,\"task_id\":\"$TASK_ID_1\"}" | jq .
echo ""

# 测试11: 获取番茄钟计数
echo "====== 测试11: 获取番茄钟计数 GET /tasks/pomodoro-count ======"
curl -s -X GET "$BASE_URL/tasks/pomodoro-count?date_filter=today" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo ""

echo "====== 所有测试完成 ======"
