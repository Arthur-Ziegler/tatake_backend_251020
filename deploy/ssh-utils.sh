#!/usr/bin/env bash
# =============================================================================
# SSH 工具函数
# =============================================================================

# 获取SSH连接选项
get_ssh_opts() {
    local port="${1:-22}"
    local timeout="${2:-30}"
    local identity_file="${3:-}"

    local ssh_opts="-p $port -o StrictHostKeyChecking=no -o ConnectTimeout=$timeout -o ServerAliveInterval=30 -o ServerAliveCountMax=3"

    if [[ -n "$identity_file" ]]; then
        # 直接使用路径，避免在配置文件加载时解析
        ssh_opts="$ssh_opts -i $identity_file"
    fi

    echo "$ssh_opts"
}

# 获取SCP连接选项
get_scp_opts() {
    local port="${1:-22}"
    local timeout="${2:-30}"
    local identity_file="${3:-}"

    local scp_opts="-P $port -o StrictHostKeyChecking=no -o ConnectTimeout=$timeout -o ServerAliveInterval=30 -o ServerAliveCountMax=3"

    if [[ -n "$identity_file" ]]; then
        # 直接使用路径，避免在配置文件加载时解析
        scp_opts="$scp_opts -i $identity_file"
    fi

    echo "$scp_opts"
}

# 执行SSH命令
ssh_exec() {
    local server="$1"
    local command="$2"
    local ssh_opts="$3"

    ssh $ssh_opts "$server" "$command"
}

# 执行SCP命令
scp_exec() {
    local source="$1"
    local destination="$2"
    local scp_opts="$3"

    # 展开路径中的波浪号
    source=$(eval echo "$source")
    destination=$(eval echo "$destination")
    scp_opts=$(eval echo "$scp_opts")

    scp $scp_opts "$source" "$destination"
}