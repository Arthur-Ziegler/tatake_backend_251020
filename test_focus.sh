#!/bin/bash

TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiYmFmYzRhMS04OTNiLTQwYzktOGRkNi00MTU5MzVhMmMyMWYiLCJpc19ndWVzdCI6ZmFsc2UsImp3dF92ZXJzaW9uIjoyLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiaWF0IjoxNzYzMTQ4OTc2LCJleHAiOjE3NjMxNTA3NzYsImp0aSI6ImE3MmNmZTYyLTg1YTItNDhhOS05OTM5LTJmNTVhM2E0MmVlZiJ9.H4jLb2ZqziE0bfw8jy9xneQslGMsJBqxsIGqUyyeHli9OVbjJVobQFQGn3fk_WScx1c2hdMEGHvIKCsxllmf68ft-CUQYQJWqAEVwuhnmgQZcyQiDJqpNLHBjhWB1XS2nq9Hl09TDYSzv0jd0cHKau115lOgRDErwB1XkpnPBLRWGsvpqXnxiAHbi_54R3O4ghTk599njUuvNiV6Jjwe73troEFY0h7nb6P2SdTRz1_0acUQKJ7h_iTKEJdTuk9Ry9yOGdzqWKef0YkLVTbxQ8IyAIy4L1Mh1XSDH6-8TrpECiAZUck0GV-5eR8jQ07OnOE3ubU148YbLuB6JfDrYA"

echo "====== 测试Focus-Status ======"
curl -s -X POST http://localhost:8001/tasks/focus-status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"focus_status":"focused","duration_minutes":25,"task_id":"dde20fd1-df01-40c9-a9a9-e70942fba597"}' | jq .

echo ""
echo "====== 测试Pomodoro-Count ======"
curl -s -X GET "http://localhost:8001/tasks/pomodoro-count?date_filter=today" \
  -H "Authorization: Bearer $TOKEN" | jq .
