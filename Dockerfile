# =============================================================================
# TaKeKe Backend Docker 镜像
# =============================================================================
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY .env* ./

# 安装 uv
RUN pip install uv

# 安装项目依赖
RUN uv sync --frozen --no-dev

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 健康检查（端口号将通过环境变量配置）
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${CONTAINER_PORT}/api/v1/health || exit 1

# 启动命令 - 使用uv运行，但设置环境变量避免重复安装依赖
ENV UV_NO_SYNC=1
# 使用shell形式解析环境变量
CMD ["sh", "-c", "uv run --no-sync python -m uvicorn src.api.main:app --host 0.0.0.0 --port ${CONTAINER_PORT}"]