# 手动部署命令

## 配置变量
```bash
DOCKER_VERSION=1.0.0
DOCKER_IMAGE_NAME=supertool
SERVER_HOST=192.168.40.41
SERVER_USER=zale
SERVER_PORT=22
SSH_IDENTITY_FILE=~/.ssh/wx_1_zale
DEPLOY_DIR=/data/home/zale/docker_images/base_project/supertool
CONTAINER_NAME=supertool
HOST_PORT=20001
CONTAINER_PORT=20001
```

## 1. 构建Docker镜像
```bash
# 构建镜像
docker build --platform linux/x86_64 -t ${DOCKER_IMAGE_NAME}:${DOCKER_VERSION} .

# 验证镜像
docker images | grep ${DOCKER_IMAGE_NAME}
```

## 2. 导出镜像
```bash
# 创建输出目录
mkdir -p ./docker_images_output

# 导出镜像
docker save ${DOCKER_IMAGE_NAME}:${DOCKER_VERSION} | gzip > ./docker_images_output/supertool_deploy_${DOCKER_VERSION}.tar.gz

# 验证文件
ls -lh ./docker_images_output/supertool_deploy_${DOCKER_VERSION}.tar.gz
```

## 3. 上传到服务器
```bash
# 创建服务器目录
ssh -i ${SSH_IDENTITY_FILE} -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_HOST} "mkdir -p ${DEPLOY_DIR}/images"

# 上传镜像文件
scp -i ${SSH_IDENTITY_FILE} -P ${SERVER_PORT} ./docker_images_output/supertool_deploy_${DOCKER_VERSION}.tar.gz ${SERVER_USER}@${SERVER_HOST}:${DEPLOY_DIR}/images/

# 上传环境文件
scp -i ${SSH_IDENTITY_FILE} -P ${SERVER_PORT} .env ${SERVER_USER}@${SERVER_HOST}:${DEPLOY_DIR}/.env
```

## 4. 服务器端操作
```bash
# 登录服务器
ssh -i ${SSH_IDENTITY_FILE} -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_HOST}

# 加载镜像
cd ${DEPLOY_DIR}/images
gunzip -c supertool_deploy_${DOCKER_VERSION}.tar.gz | docker load

# 验证镜像
docker images | grep ${DOCKER_IMAGE_NAME}

# 停止旧容器
docker stop ${CONTAINER_NAME} || true
docker rm ${CONTAINER_NAME} || true

# 启动新容器
docker run -d \
    --name ${CONTAINER_NAME} \
    --restart unless-stopped \
    -p ${HOST_PORT}:${CONTAINER_PORT} \
    --env-file ${DEPLOY_DIR}/.env \
    --add-host=host.docker.internal:host-gateway \
    --log-driver json-file \
    --log-opt max-size=10m \
    --log-opt max-file=3 \
    ${DOCKER_IMAGE_NAME}:${DOCKER_VERSION}
```

## 5. 验证部署
```bash
# 检查容器状态
docker ps | grep ${CONTAINER_NAME}

# 查看容器日志
docker logs ${CONTAINER_NAME}

# 健康检查
curl -f http://localhost:${HOST_PORT}/health

# 测试API
curl http://localhost:${HOST_PORT}/docs
```

## 常用管理命令
```bash
# 重启容器
docker restart ${CONTAINER_NAME}

# 停止容器
docker stop ${CONTAINER_NAME}

# 删除容器
docker rm ${CONTAINER_NAME}

# 查看容器资源
docker stats ${CONTAINER_NAME}

# 进入容器
docker exec -it ${CONTAINER_NAME} bash

# 清理旧镜像
docker image prune -f
```