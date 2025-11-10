#!/bin/bash
# TaKeKe Backend 一键回滚脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
        exit 1
    fi

    source "$config_file"
}

# 加载回滚信息
load_rollback_info() {
    local rollback_file="$SCRIPT_DIR/.last_deploy"

    if [ ! -f "$rollback_file" ]; then
        log_error "回滚信息不存在，无法回滚"
        log_info "请检查 $rollback_file 文件"
        exit 1
    fi

    source "$rollback_file"

    log_info "上次部署信息："
    log_info "  版本: ${VERSION}"
    log_info "  镜像: ${IMAGE}"
    log_info "  时间: ${DEPLOY_TIME}"
}

# 确认回滚
confirm_rollback() {
    log_warn "============================="
    log_warn "即将回滚到上一版本"
    log_warn "============================="
    log_info "当前版本将被停止"
    log_info "上一版本将被恢复"
    echo

    read -p "确认回滚？(yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "取消回滚"
        exit 0
    fi
}

# 执行回滚
do_rollback() {
    log_info "开始回滚..."

    # 优先使用SSH别名
    local ssh_target="${SSH_ALIAS:-${DEPLOY_USER}@${SERVER_HOST}}"
    local container_current="${CONTAINER_NAME}"
    local container_old="${CONTAINER_NAME}-old"

    ssh "${ssh_target}" << EOF
set -e

# 检查是否有绿色容器（上一版本）
if docker ps -a --format '{{.Names}}' | grep -q "${CONTAINER_NAME}-green"; then
    echo "发现绿色容器，使用蓝绿回滚..."

    # 停止当前容器并重命名为old
    docker stop ${container_current}
    docker rename ${container_current} ${container_old}

    # 恢复绿色容器为主容器
    docker start ${CONTAINER_NAME}-green
    docker rename ${CONTAINER_NAME}-green ${container_current}

    # 删除旧容器
    docker rm ${container_old}

    echo "蓝绿回滚完成"
else
    echo "使用镜像回滚..."

    # 停止并删除当前容器
    docker stop ${container_current}
    docker rm ${container_current}

    # 使用上一版本镜像启动容器
    docker run -d \
        --name ${container_current} \
        --restart unless-stopped \
        -p ${HOST_PORT}:${CONTAINER_PORT} \
        -e PORT=${CONTAINER_PORT} \
        --memory ${MEMORY_LIMIT:-2g} \
        --cpus ${CPU_LIMIT:-2} \
        ${IMAGE}

    echo "镜像回滚完成"
fi
EOF

    log_success "回滚完成"
}

# 验证回滚
verify_rollback() {
    log_info "验证回滚结果..."

    # 优先使用SSH别名
    local ssh_target="${SSH_ALIAS:-${DEPLOY_USER}@${SERVER_HOST}}"

    # 检查容器状态
    if ssh "${ssh_target}" "docker ps | grep -q ${CONTAINER_NAME}"; then
        log_success "容器运行正常"
    else
        log_error "容器未运行"
        exit 1
    fi

    # 健康检查
    sleep 5

    if ssh "${ssh_target}" "docker exec ${CONTAINER_NAME} curl -f ${HEALTH_CHECK_URL} > /dev/null 2>&1"; then
        log_success "健康检查通过"
    else
        log_warn "健康检查失败，请手动检查"
    fi
}

# 显示回滚信息
show_rollback_info() {
    log_success "============================="
    log_success "回滚成功！"
    log_success "============================="
    log_info "已恢复到上一版本"
    log_info "版本: ${VERSION}"
    log_info "容器: ${CONTAINER_NAME}"
    log_success "============================="
}

# 主函数
main() {
    log_info "TaKeKe Backend 回滚开始"
    log_info "============================="

    # 1. 加载配置
    load_config

    # 2. 加载回滚信息
    load_rollback_info

    # 3. 确认回滚
    confirm_rollback

    # 4. 执行回滚
    do_rollback

    # 5. 验证回滚
    verify_rollback

    # 6. 显示信息
    show_rollback_info
}

# 执行主函数
main "$@"
