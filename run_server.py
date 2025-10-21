#!/usr/bin/env python3
"""
TaKeKe API 服务器启动脚本

使用方法：
    python run_server.py
或
    uv run python run_server.py
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    import uvicorn
    from src.api.config import config

    print(f"🚀 启动 {config.app_name} v{config.app_version}")
    print(f"🌐 服务地址: http://{config.api_host}:{config.api_port}{config.api_prefix}")
    print(f"📖 API文档: http://{config.api_host}:{config.api_port}/docs")
    print("")

    uvicorn.run(
        "src.api.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )