#!/bin/bash
# 手动部署命令集合
# 当自动脚本无法连接时，可以手动执行这些命令

echo "=================================="
echo "🔧 手动部署命令"
echo "=================================="

# 加载配置
if [[ -f "deploy.env" ]]; then
    source deploy.env
    echo "✓ 配置加载完成"
else
    echo "✗ 配置文件不存在: deploy.env"
    exit 1
fi

echo ""
echo "1. 连接到服务器："
echo "   ssh -i ~/.ssh/YcY_Root root@45.152.65.130"
echo ""

echo "2. 检查Docker镜像："
echo "   docker images | grep tatake-backend"
echo ""

echo "3. 停止并删除旧容器："
echo "   docker stop tatake-backend || true"
echo "   docker rm tatake-backend || true"
echo ""

echo "4. 部署新容器："
echo "   docker run -d \\"
echo "       --name tatake-backend \\"
echo "       --restart unless-stopped \\"
echo "       -p 2025:2025 \\"
echo "       --env-file /root/zale/docker_images/tatake_backend/.env \\"
echo "       -e HOST_PORT=2025 \\"
echo "       -e CONTAINER_PORT=2025 \\"
echo "       --add-host=host.docker.internal:host-gateway \\"
echo "       --log-driver json-file \\"
echo "       --log-opt max-size=10m \\"
echo "       --log-opt max-file=3 \\"
echo "       tatake-backend:1.0.3"
echo ""

echo "5. 检查容器状态："
echo "   docker ps | grep tatake-backend"
echo ""

echo "6. 查看容器日志："
echo "   docker logs tatake-backend"
echo ""

echo "7. 测试访问："
echo "   curl http://localhost:2025/health"
echo "   或在浏览器访问: http://45.152.65.130:2025/docs"
echo ""

echo "=================================="
echo "💡 提示："
echo "1. 如果第一步连接成功，后续步骤可以在服务器上直接执行"
echo "2. 确保镜像文件已加载到服务器"
echo "3. 检查防火墙是否允许端口2025访问"
echo "=================================="