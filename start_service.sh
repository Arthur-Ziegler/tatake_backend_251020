#!/bin/bash
# 业务服务启动脚本

echo "🚀 启动TaKeKe后端服务..."

# 设置认证微服务配置
export AUTH_MICROSERVICE_URL=http://localhost:8987
export AUTH_PROJECT=tatake_backend
export ENVIRONMENT=development

# 开发环境JWT配置
export JWT_SKIP_SIGNATURE=true
export JWT_FALLBACK_SKIP_SIGNATURE=true

# 输出配置信息
echo "认证微服务配置:"
echo "   AUTH_MICROSERVICE_URL=$AUTH_MICROSERVICE_URL"
echo "   AUTH_PROJECT=$AUTH_PROJECT"
echo "   ENVIRONMENT=$ENVIRONMENT"

# 启动服务
echo "启动FastAPI服务..."
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
