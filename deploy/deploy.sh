#!/bin/bash
# TaKeKe Backend 一键部署脚本
# 特性: 蓝绿部署 + 零停机 + 自动回滚 + 健康检查

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 加载配置
load_config() {
    local config_file="$SCRIPT_DIR/deploy.env"

    if [ ! -f "$config_file" ]; then
        log_error "配置文件不存在: $config_file"
        log_info "请复制 deploy.env.example 为 deploy.env 并配置"
        exit 1
    fi

    source "$config_file"
    log_info "配置加载完成"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi

    if ! command -v ssh &> /dev/null; then
        log_error "SSH未安装"
        exit 1
    fi

    log_success "依赖检查通过"
}

# 构建镜像
build_image() {
    log_info "开始构建镜像: ${IMAGE_NAME}:${VERSION}"

    cd "$PROJECT_ROOT"

    docker build \
        --platform "${DOCKER_PLATFORM}" \
        --file "$SCRIPT_DIR/Dockerfile" \
        --tag "${IMAGE_NAME}:${VERSION}" \
        --tag "${IMAGE_NAME}:latest" \
        --build-arg VERSION="${VERSION}" \
        .

    log_success "镜像构建完成"
}

# SSH管道传输镜像（压缩传输）
push_image() {
    log_info "推送镜像到服务器（压缩传输）..."

    # 优先使用SSH别名，否则使用用户名@主机
    local ssh_target="${SSH_ALIAS}"
    if [ -z "${SSH_ALIAS}" ]; then
        ssh_target="${DEPLOY_USER}@${SERVER_HOST}"
    fi

    # SSH连接参数：超时控制 + 心跳保活
    local ssh_opts="-o ConnectTimeout=10 -o ServerAliveInterval=30 -o ServerAliveCountMax=3"

    # 压缩传输（gzip -1 快速压缩，降低CPU占用）
    # docker load 会自动识别gzip格式并解压
    if docker save "${IMAGE_NAME}:${VERSION}" | \
        gzip -1 | \
        ssh ${ssh_opts} "${ssh_target}" "docker load"; then
        log_success "镜像推送完成"
    else
        log_error "镜像推送失败，请检查网络连接或磁盘空间"
        exit 1
    fi
}

# 健康检查
health_check() {
    local container_name=$1
    local max_attempts=${HEALTH_CHECK_RETRIES:-12}
    local interval=${HEALTH_CHECK_INTERVAL:-5}

    # 优先使用SSH别名
    local ssh_target="${SSH_ALIAS:-${DEPLOY_USER}@${SERVER_HOST}}"

    log_info "等待服务就绪..."

    for ((i=1; i<=max_attempts; i++)); do
        if ssh "${ssh_target}" \
            "docker exec ${container_name} curl -f http://localhost:${CONTAINER_PORT}/health > /dev/null 2>&1"; then
            log_success "健康检查通过 (${i}/${max_attempts})"
            return 0
        fi

        log_info "健康检查中... (${i}/${max_attempts})"
        sleep $interval
    done

    log_error "健康检查失败"
    return 1
}

# 蓝绿部署
blue_green_deploy() {
    log_info "开始蓝绿部署..."

    # 优先使用SSH别名
    local ssh_target="${SSH_ALIAS:-${DEPLOY_USER}@${SERVER_HOST}}"
    local container_blue="${CONTAINER_NAME}-blue"
    local container_green="${CONTAINER_NAME}-green"

    # 1. 启动新容器（蓝色）
    log_info "启动新容器: ${container_blue}"

    ssh "${ssh_target}" << EOF
set -e

# 停止并删除旧的蓝色容器
docker stop ${container_blue} 2>/dev/null || true
docker rm ${container_blue} 2>/dev/null || true

# 启动新容器
docker run -d \
    --name ${container_blue} \
    --restart unless-stopped \
    -p ${HOST_PORT}:${CONTAINER_PORT} \
    -e PORT=${CONTAINER_PORT} \
    --memory ${MEMORY_LIMIT:-2g} \
    --cpus ${CPU_LIMIT:-2} \
    --log-driver ${LOG_DRIVER:-json-file} \
    --log-opt max-size=${LOG_MAX_SIZE:-10m} \
    --log-opt max-file=${LOG_MAX_FILE:-3} \
    ${IMAGE_NAME}:${VERSION}

echo "容器已启动"
EOF

    # 2. 健康检查
    if ! health_check "${container_blue}"; then
        log_error "新容器健康检查失败"

        # 自动回滚
        if [ "${ENABLE_ROLLBACK}" == "true" ]; then
            log_warn "执行自动回滚..."
            ssh "${ssh_target}" "docker stop ${container_blue}; docker rm ${container_blue}"
        fi

        exit 1
    fi

    # 3. 切换流量（重命名容器）
    log_info "切换流量到新版本..."

    ssh "${ssh_target}" << EOF
set -e

# 重命名当前主容器为绿色（备份）
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker rename ${CONTAINER_NAME} ${container_green} || true
fi

# 重命名蓝色容器为主容器
docker rename ${container_blue} ${CONTAINER_NAME}

echo "流量切换完成"
EOF

    log_success "流量已切换到新版本"

    # 4. 停止旧容器
    log_info "停止旧版本容器..."

    ssh "${ssh_target}" << EOF
set -e

# 优雅停止旧容器
if docker ps --format '{{.Names}}' | grep -q "^${container_green}$"; then
    docker stop -t 30 ${container_green} 2>/dev/null || true
    docker rm ${container_green} 2>/dev/null || true
    echo "旧容器已停止"
fi
EOF

    log_success "蓝绿部署完成"
}

# 简单部署（无蓝绿）
simple_deploy() {
    log_info "开始简单部署..."

    # 优先使用SSH别名
    local ssh_target="${SSH_ALIAS:-${DEPLOY_USER}@${SERVER_HOST}}"

    ssh "${ssh_target}" << EOF
set -e

# 1. 停止并删除旧容器
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "停止旧容器..."
    docker stop -t 30 ${CONTAINER_NAME} 2>/dev/null || true
    echo "删除旧容器..."
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
fi

# 2. 删除同名的旧镜像（保留tag以外的）
echo "清理旧镜像..."
docker images ${IMAGE_NAME} --format "{{.ID}} {{.Tag}}" | while read id tag; do
    if [ "\$tag" != "${VERSION}" ] && [ "\$tag" != "latest" ]; then
        docker rmi -f \$id 2>/dev/null || true
    fi
done

# 3. 启动新容器
echo "启动新容器..."
docker run -d \
    --name ${CONTAINER_NAME} \
    --restart unless-stopped \
    -p ${HOST_PORT}:${CONTAINER_PORT} \
    -e PORT=${CONTAINER_PORT} \
    --memory ${MEMORY_LIMIT:-2g} \
    --cpus ${CPU_LIMIT:-2} \
    --log-driver ${LOG_DRIVER:-json-file} \
    --log-opt max-size=${LOG_MAX_SIZE:-10m} \
    --log-opt max-file=${LOG_MAX_FILE:-3} \
    ${IMAGE_NAME}:${VERSION}

echo "容器已启动"
EOF

    # 健康检查
    if ! health_check "${CONTAINER_NAME}"; then
        log_error "健康检查失败"
        exit 1
    fi

    log_success "简单部署完成"
}

# 清理旧版本
cleanup_old_versions() {
    if [ "${AUTO_CLEANUP}" != "true" ]; then
        return 0
    fi

    log_info "清理旧版本镜像..."

    # 优先使用SSH别名
    local ssh_target="${SSH_ALIAS:-${DEPLOY_USER}@${SERVER_HOST}}"

    ssh "${ssh_target}" << EOF
# 保留最近N个版本
docker images ${IMAGE_NAME} --format "{{.Tag}}" | \
    grep -v "latest" | \
    tail -n +$((KEEP_VERSIONS + 1)) | \
    xargs -r -I {} docker rmi ${IMAGE_NAME}:{} 2>/dev/null || true

echo "清理完成"
EOF

    log_success "旧版本清理完成"
}

# 保存回滚信息
save_rollback_info() {
    local rollback_file="$SCRIPT_DIR/.last_deploy"

    cat > "$rollback_file" << EOF
VERSION=${VERSION}
IMAGE=${IMAGE_NAME}:${VERSION}
DEPLOY_TIME=$(date '+%Y-%m-%d %H:%M:%S')
CONTAINER_NAME=${CONTAINER_NAME}
EOF

    log_info "回滚信息已保存"
}

# 显示部署信息
show_deploy_info() {
    log_success "========================="
    log_success "部署成功！"
    log_success "========================="
    log_info "版本: ${VERSION}"
    log_info "镜像: ${IMAGE_NAME}:${VERSION}"
    log_info "容器: ${CONTAINER_NAME}"
    log_info "端口: ${HOST_PORT} -> ${CONTAINER_PORT}"
    log_info "服务器: ${SERVER_HOST}"
    log_success "========================="
}

# 主函数
main() {
    log_info "TaKeKe Backend 部署开始"
    log_info "========================="

    # 1. 检查依赖
    check_dependencies

    # 2. 加载配置
    load_config

    # 3. 构建镜像
    build_image

    # 4. 推送镜像
    push_image

    # 5. 部署
    if [ "${ENABLE_BLUE_GREEN}" == "true" ]; then
        blue_green_deploy
    else
        simple_deploy
    fi

    # 6. 清理旧版本
    cleanup_old_versions

    # 7. 保存回滚信息
    save_rollback_info

    # 8. 显示信息
    show_deploy_info
}

# 执行主函数
main "$@"
