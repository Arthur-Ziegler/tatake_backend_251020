# TaKeKe Backend - 生产级Dockerfile
# 平台: x86_64 (linux/amd64)
# Python: 3.12-slim
# 包管理: UV

FROM --platform=linux/amd64 python:3.12-slim

# 镜像元数据
LABEL maintainer="takeke-team" \
      description="TaKeKe Backend Service" \
      version="1.0.0"

# 工作目录
WORKDIR /app

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    PORT=8000 \
    ENVIRONMENT=production \
    DEBUG=false \
    AUTH_MICROSERVICE_URL=http://api.aitodo.it:20251 \
    TASK_MICROSERVICE_URL=http://api.aitodo.it:20253 \
    REWARD_MICROSERVICE_URL=http://api.aitodo.it:20254 \
    CHAT_MICROSERVICE_URL=http://api.aitodo.it:20252 \
    FOCUS_MICROSERVICE_URL=http://api.aitodo.it:20255

# 系统依赖（最小化）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        postgresql-client \
        curl && \
    rm -rf /var/lib/apt/lists/*

# 安装UV包管理器
RUN pip install --no-cache-dir uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装Python依赖
RUN uv sync --frozen --no-dev

# 复制应用代码
COPY src ./src

# 创建非root用户
RUN useradd -m -u 1000 app && \
    chown -R app:app /app

USER app

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# 暴露端口
EXPOSE ${PORT}

# 启动命令
CMD ["sh", "-c", "uv run uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}"]
