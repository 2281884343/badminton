# 🐧 Linux服务器部署指南

## 系统要求

- Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- Python 3.8+
- Node.js 20+ LTS（推荐）
- Nginx（推荐用于生产环境）

## 快速部署

### 1. 准备服务器环境

#### Ubuntu/Debian
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python 3
sudo apt install python3 python3-pip python3-venv -y

# 安装Node.js 20.x LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# 安装Nginx（可选）
sudo apt install nginx -y
```

#### CentOS/RHEL
```bash
# 更新系统
sudo yum update -y

# 安装Python 3
sudo yum install python3 python3-pip -y

# 安装Node.js 20.x LTS
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo yum install nodejs -y

# 安装Nginx（可选）
sudo yum install nginx -y
```

### 2. 上传代码到服务器

```bash
# 方法1: 使用git
git clone https://github.com/2281884343/badminton /opt/badminton-game
cd /opt/badminton-game

# 方法2: 使用scp上传
# 在本地执行
scp -r ./bm user@server:/opt/badminton-game
```

### 3. 自动部署

```bash
# 赋予执行权限
chmod +x deploy.sh start-dev.sh start-prod.sh

# 运行部署脚本
./deploy.sh
```

部署脚本会自动：
- 检查系统环境
- 创建Python虚拟环境
- 安装后端依赖
- 安装前端依赖
- 创建必要的数据目录

### 4. 启动服务

#### 开发模式（用于测试）
```bash
./start-dev.sh
```

开发模式特点：
- 后端单进程运行
- 前端热重载开发服务器
- 适合开发和调试

#### 生产模式（推荐）
```bash
./start-prod.sh
```

生产模式特点：
- 后端多进程运行
- 前端静态文件服务
- 更高性能和稳定性

## 使用systemd管理服务（推荐）

### 1. 修改服务文件

编辑 `badminton-game.service`：

```ini
[Unit]
Description=Badminton Game Backend Service
After=network.target

[Service]
Type=simple
User=www-data  # 修改为你的用户
WorkingDirectory=/opt/badminton-game/backend  # 修改为实际路径
Environment="PATH=/opt/badminton-game/backend/venv/bin"
ExecStart=/opt/badminton-game/backend/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. 安装和启动服务

```bash
# 复制服务文件
sudo cp badminton-game.service /etc/systemd/system/

# 重新加载systemd
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable badminton-game

# 启动服务
sudo systemctl start badminton-game

# 查看状态
sudo systemctl status badminton-game

# 查看日志
sudo journalctl -u badminton-game -f
```

### 3. 管理服务

```bash
# 停止服务
sudo systemctl stop badminton-game

# 重启服务
sudo systemctl restart badminton-game

# 禁用开机自启
sudo systemctl disable badminton-game
```

## Nginx反向代理配置（推荐）

### 1. 修改配置文件

编辑 `nginx.conf` 文件，修改以下内容：

```nginx
server_name your-domain.com;  # 改为你的域名或服务器IP
root /opt/badminton-game/frontend/dist;  # 改为实际路径
```

### 2. 构建前端

```bash
cd frontend
npm run build
```

### 3. 部署Nginx配置

```bash
# 复制配置文件
sudo cp nginx.conf /etc/nginx/sites-available/badminton-game

# 创建软链接
sudo ln -s /etc/nginx/sites-available/badminton-game /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

### 4. 访问应用

浏览器访问：`http://your-server-ip` 或 `http://your-domain.com`

## 防火墙配置

### UFW (Ubuntu/Debian)
```bash
# 允许HTTP
sudo ufw allow 80/tcp

# 允许HTTPS（如果使用SSL）
sudo ufw allow 443/tcp

# 如果不使用Nginx，需要开放应用端口
sudo ufw allow 8080/tcp  # 后端
sudo ufw allow 3000/tcp  # 前端

# 重新加载防火墙
sudo ufw reload
```

### Firewalld (CentOS/RHEL)
```bash
# 允许HTTP
sudo firewall-cmd --permanent --add-service=http

# 允许HTTPS
sudo firewall-cmd --permanent --add-service=https

# 允许自定义端口
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-port=3000/tcp

# 重新加载防火墙
sudo firewall-cmd --reload
```

## SSL/HTTPS配置（推荐）

### 使用Let's Encrypt免费证书

```bash
# 安装certbot
sudo apt install certbot python3-certbot-nginx -y

# 自动配置SSL
sudo certbot --nginx -d your-domain.com

# 自动续期（添加到cron）
sudo crontab -e
# 添加以下行：
0 3 * * * certbot renew --quiet
```

Nginx会自动更新配置，将HTTP重定向到HTTPS。

## 性能优化

### 1. 后端优化

#### 使用Gunicorn（推荐）

```bash
# 安装gunicorn
cd backend
source venv/bin/activate
pip install gunicorn

# 启动（4个worker进程）
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080
```

#### 修改systemd服务文件

```ini
ExecStart=/opt/badminton-game/backend/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080
```

### 2. 前端优化

前端已在构建时自动优化：
- 代码压缩和混淆
- 静态资源CDN
- Gzip压缩
- 浏览器缓存

### 3. Nginx优化

在 `nginx.conf` 中添加：

```nginx
# Gzip压缩
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript application/json;

# 连接优化
keepalive_timeout 65;
client_max_body_size 10M;

# 缓冲优化
client_body_buffer_size 10K;
client_header_buffer_size 1k;
large_client_header_buffers 4 8k;
```

## 监控和日志

### 1. 查看后端日志

```bash
# systemd服务日志
sudo journalctl -u badminton-game -f

# 或者重定向到文件
cd backend
source venv/bin/activate
python main.py >> /var/log/badminton-backend.log 2>&1
```

### 2. 查看Nginx日志

```bash
# 访问日志
sudo tail -f /var/log/nginx/access.log

# 错误日志
sudo tail -f /var/log/nginx/error.log
```

### 3. 安装监控工具（可选）

```bash
# 安装htop查看系统资源
sudo apt install htop -y

# 安装pm2管理Node.js进程
sudo npm install -g pm2

# 使用pm2管理前端（开发模式）
cd frontend
pm2 start "npm run dev" --name badminton-frontend
pm2 save
pm2 startup
```

## 备份和恢复

### 备份玩家数据

```bash
# 创建备份目录
mkdir -p /backup/badminton-game

# 备份玩家配置
cp -r backend/data/players /backup/badminton-game/players-$(date +%Y%m%d)

# 自动备份（添加到cron）
sudo crontab -e
# 每天3点备份
0 3 * * * cp -r /opt/badminton-game/backend/data/players /backup/badminton-game/players-$(date +\%Y\%m\%d)
```

### 恢复数据

```bash
# 恢复玩家配置
cp -r /backup/badminton-game/players-20240101/* backend/data/players/
```

## 更新应用

```bash
# 拉取最新代码
cd /opt/badminton-game
git pull

# 更新后端依赖
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 更新前端依赖并重新构建
cd ../frontend
npm install
npm run build

# 重启服务
sudo systemctl restart badminton-game
sudo systemctl restart nginx
```

## 故障排查

### 后端无法启动

```bash
# 检查Python版本
python3 --version

# 检查依赖是否安装
cd backend
source venv/bin/activate
pip list

# 检查端口是否被占用
sudo netstat -tulnp | grep 8080
sudo lsof -i :8080
```

### 前端无法访问

```bash
# 检查Nginx状态
sudo systemctl status nginx

# 检查Nginx配置
sudo nginx -t

# 检查前端是否构建
ls -la frontend/dist
```

### WebSocket连接失败

```bash
# 检查Nginx WebSocket配置
sudo nginx -T | grep -A 10 "location /ws"

# 检查防火墙
sudo ufw status
sudo iptables -L
```

### AI描述生成失败

```bash
# 检查网络连接
curl -I https://api.moonshot.cn

# 测试API密钥
curl -X POST https://api.moonshot.cn/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "kimi-k2-turbo-preview", "messages": [{"role": "user", "content": "test"}]}'
```

## 安全建议

### 1. 修改默认配置

```bash
# 修改API密钥（不要使用示例中的密钥）
vi backend/main.py
# 修改 api_key 值
```

### 2. 限制访问

```nginx
# 在nginx.conf中添加IP白名单（如果需要）
location / {
    allow 192.168.1.0/24;
    deny all;
}
```

### 3. 定期更新

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 更新Python包
cd backend
source venv/bin/activate
pip list --outdated
pip install --upgrade <package-name>

# 更新Node.js包
cd frontend
npm outdated
npm update
```

## 常用命令速查

```bash
# 服务管理
sudo systemctl start badminton-game    # 启动
sudo systemctl stop badminton-game     # 停止
sudo systemctl restart badminton-game  # 重启
sudo systemctl status badminton-game   # 状态

# 日志查看
sudo journalctl -u badminton-game -f   # 实时日志
sudo journalctl -u badminton-game -n 100  # 最近100行

# Nginx管理
sudo nginx -t                          # 测试配置
sudo systemctl reload nginx            # 重载配置
sudo systemctl restart nginx           # 重启Nginx

# 进程管理
ps aux | grep python                   # 查看Python进程
ps aux | grep node                     # 查看Node进程
kill -9 <PID>                         # 强制结束进程
```

## 联系和支持

如遇到问题，请检查：
1. 系统日志：`sudo journalctl -xe`
2. 应用日志：`sudo journalctl -u badminton-game -f`
3. Nginx日志：`sudo tail -f /var/log/nginx/error.log`

---

**祝部署顺利！🏸**

