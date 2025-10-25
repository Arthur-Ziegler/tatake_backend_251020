#!/bin/bash

# Streamlit 测试面板启动脚本
#
# 使用方法：
#   ./run_streamlit.sh [port]
#
# 示例：
#   ./run_streamlit.sh 8503

# 设置默认端口
PORT=${1:-8503}

echo "🚀 启动 TaKeKe Streamlit 测试面板..."
echo "📍 本地访问: http://localhost:$PORT"
echo "🌐 网络访问: http://localhost:$PORT"
echo ""
echo "💡 提示: 按 Ctrl+C 停止应用"
echo ""

# 确保当前目录在PYTHONPATH中
export PYTHONPATH=.

# 启动Streamlit应用
uv run streamlit run streamlit_app/main.py --server.port $PORT