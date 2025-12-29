# 🐳 Docker部署指南

如果你更喜欢使用Docker部署，可以使用以下配置。

## Dockerfile - 后端

创建 `backend/Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建数据目录
RUN mkdir -p data/players

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Dockerfile - 前端

创建 `frontend/Dockerfile`：

```dockerfile
FROM node:18-alpine as build

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm ci

# 构建应用
COPY . .
RUN npm run build

# 使用nginx提供静态文件
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

## docker-compose.yml

创建项目根目录下的 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: badminton-backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/data
    environment:
      - MOONSHOT_API_KEY=${MOONSHOT_API_KEY}
    restart: unless-stopped
    networks:
      - badminton-network

  frontend:
    build: ./frontend
    container_name: badminton-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - badminton-network

networks:
  badminton-network:
    driver: bridge

volumes:
  player-data:
```

## 使用Docker Compose部署

### 1. 安装Docker和Docker Compose

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose -y

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 添加当前用户到docker组
sudo usermod -aG docker $USER
newgrp docker
```

### 2. 创建环境变量文件

创建 `.env` 文件：

```bash
MOONSHOT_API_KEY=sk-r7lK62mQRVGX0Qqh9k6bZsS4KeCTbF7YKonjuDZci9k8vj2r
```

### 3. 构建并启动服务

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps
```

### 4. 停止服务

```bash
# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

## Docker命令速查

```bash
# 查看运行中的容器
docker ps

# 查看所有容器
docker ps -a

# 查看日志
docker logs badminton-backend
docker logs badminton-frontend

# 进入容器
docker exec -it badminton-backend /bin/bash

# 重启容器
docker restart badminton-backend

# 删除容器
docker rm -f badminton-backend badminton-frontend

# 删除镜像
docker rmi bm_backend bm_frontend

# 清理未使用的资源
docker system prune -a
```

## 数据持久化

玩家数据会持久化到主机的 `./backend/data` 目录。即使删除容器，数据也不会丢失。

## 更新应用

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```

## 性能优化

### 使用多阶段构建减小镜像大小

前端Dockerfile已使用多阶段构建，最终镜像只包含nginx和静态文件。

### 后端使用gunicorn

修改后端Dockerfile的CMD：

```dockerfile
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

## 监控和日志

### 查看实时日志

```bash
# 所有服务
docker-compose logs -f

# 特定服务
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 限制日志大小

在 `docker-compose.yml` 中添加：

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 健康检查

在 `docker-compose.yml` 中添加健康检查：

```yaml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/skills"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## 使用Docker Swarm（集群部署）

```bash
# 初始化Swarm
docker swarm init

# 部署服务栈
docker stack deploy -c docker-compose.yml badminton

# 查看服务
docker stack services badminton

# 扩展服务
docker service scale badminton_backend=3

# 删除服务栈
docker stack rm badminton
```

---

**Docker部署让应用更易于管理和扩展！🐳**

