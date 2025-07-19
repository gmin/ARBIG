# ARBIG v2.0 部署指南

## 📋 部署概述

本指南介绍 ARBIG v2.0 的部署方法，包括开发环境和生产环境的部署配置。

## 🏗️ 系统架构

```
部署架构
├── web_admin (端口8000)     # Web管理系统
├── trading_api (端口8001)   # 交易API服务
└── core                     # 核心系统 (内部服务)
```

## 🚀 快速部署

### 1. 环境准备

```bash
# 1. 激活vnpy环境
conda activate vnpy

# 2. 安装依赖
pip install -r requirements.txt

# 3. 检查环境
python check_dependencies.py
```

### 2. 配置文件

**CTP配置** (`config/ctp_sim.json`):
```json
{
    "用户名": "your_username",
    "密码": "your_password",
    "经纪商代码": "9999", 
    "交易服务器": "182.254.243.31:30001",
    "行情服务器": "182.254.243.31:30011"
}
```

**系统配置** (`config.yaml`):
```yaml
# Web管理系统配置
web_admin:
  host: "0.0.0.0"
  port: 8000
  debug: false

# 交易API配置  
trading_api:
  host: "0.0.0.0"
  port: 8001
  debug: false

# 核心系统配置
core:
  event_persist_path: "events.jsonl"
  log_level: "INFO"
```

### 3. 启动服务

**方式一: 统一启动脚本**
```bash
python start_arbig.py
# 选择: 3. 启动完整系统
```

**方式二: 启动Web管理系统**
```bash
# 启动Web管理系统（包含所有功能）
python -m web_admin.app
```

**方式三: 后台启动**
```bash
# 后台启动Web管理系统
nohup python -m web_admin.app > logs/web_admin.log 2>&1 &
```

### 4. 验证部署

```bash
# 检查服务状态
curl http://localhost:8000/health    # Web管理系统

# 检查Web界面
# 浏览器访问: http://localhost:8000
```

## 🐳 Docker部署

### 1. 构建镜像

**Dockerfile**:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# 暴露端口
EXPOSE 8000 8001

# 启动脚本
CMD ["python", "start_arbig.py"]
```

### 2. Docker Compose

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  arbig-web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SERVICE_TYPE=web_admin
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped

  arbig-api:
    build: .
    ports:
      - "8001:8001"
    environment:
      - SERVICE_TYPE=trading_api
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/nginx.conf:/etc/nginx/nginx.conf
      - ./deploy/ssl:/etc/nginx/ssl
    depends_on:
      - arbig-web
      - arbig-api
    restart: unless-stopped
```

### 3. 启动容器

```bash
# 构建并启动
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f arbig-web
docker-compose logs -f arbig-api
```

## 🔧 生产环境部署

### 1. 使用Supervisor管理进程

**supervisor.conf**:
```ini
[supervisord]
nodaemon=false

[program:arbig-trading-api]
command=/opt/arbig/venv/bin/python -m trading_api.app
directory=/opt/arbig
user=arbig
autostart=true
autorestart=true
stdout_logfile=/opt/arbig/logs/trading_api.log
stderr_logfile=/opt/arbig/logs/trading_api_error.log

[program:arbig-web-admin]
command=/opt/arbig/venv/bin/python -m web_admin.app
directory=/opt/arbig
user=arbig
autostart=true
autorestart=true
stdout_logfile=/opt/arbig/logs/web_admin.log
stderr_logfile=/opt/arbig/logs/web_admin_error.log
```

### 2. 使用Nginx反向代理

**nginx.conf**:
```nginx
upstream arbig_web {
    server 127.0.0.1:8000;
}

upstream arbig_api {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name your-domain.com;

    # Web管理系统
    location / {
        proxy_pass http://arbig_web;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 交易API
    location /api/ {
        proxy_pass http://arbig_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 3. 系统服务配置

**systemd服务** (`/etc/systemd/system/arbig.service`):
```ini
[Unit]
Description=ARBIG Trading System
After=network.target

[Service]
Type=forking
User=arbig
Group=arbig
WorkingDirectory=/opt/arbig
ExecStart=/usr/bin/supervisord -c /opt/arbig/deploy/supervisor.conf
ExecReload=/usr/bin/supervisorctl reload
ExecStop=/usr/bin/supervisorctl shutdown
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl enable arbig
sudo systemctl start arbig
sudo systemctl status arbig
```

## 📊 监控和日志

### 1. 日志配置

**日志目录结构**:
```
logs/
├── web_admin.log          # Web管理系统日志
├── trading_api.log        # 交易API日志
├── core_system.log        # 核心系统日志
├── ctp_gateway.log        # CTP网关日志
└── error.log             # 错误日志
```

### 2. 监控指标

**系统监控**:
- CPU使用率
- 内存使用率
- 磁盘空间
- 网络连接状态

**业务监控**:
- CTP连接状态
- 订单处理延时
- 交易信号数量
- 风控触发次数

### 3. 告警配置

**告警规则**:
```yaml
alerts:
  - name: "CTP连接断开"
    condition: "ctp_connected == false"
    duration: "30s"
    action: "email,sms"
    
  - name: "系统内存不足"
    condition: "memory_usage > 90%"
    duration: "60s"
    action: "email"
    
  - name: "订单处理延时过高"
    condition: "order_latency > 1000ms"
    duration: "30s"
    action: "email"
```

## 🔒 安全配置

### 1. 防火墙设置

```bash
# 只开放必要端口
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### 2. SSL证书配置

```bash
# 使用Let's Encrypt
sudo certbot --nginx -d your-domain.com
```

### 3. 访问控制

**IP白名单** (nginx):
```nginx
location / {
    allow 192.168.1.0/24;
    allow 10.0.0.0/8;
    deny all;
    
    proxy_pass http://arbig_web;
}
```

## 🚨 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tlnp | grep :8000
   netstat -tlnp | grep :8001
   ```

2. **CTP连接失败**
   ```bash
   # 检查配置文件
   cat config/ctp_sim.json
   
   # 检查网络连接
   telnet 182.254.243.31 30001
   ```

3. **服务启动失败**
   ```bash
   # 查看详细错误
   python -m web_admin.app --debug
   python -m trading_api.app --debug
   ```

### 日志分析

```bash
# 查看实时日志
tail -f logs/web_admin.log
tail -f logs/trading_api.log

# 搜索错误
grep ERROR logs/*.log
grep CRITICAL logs/*.log
```

## 📈 性能优化

### 1. 系统优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 优化网络参数
echo "net.core.somaxconn = 65536" >> /etc/sysctl.conf
sysctl -p
```

### 2. 应用优化

**配置调优**:
```yaml
# 增加工作进程数
web_admin:
  workers: 4
  
trading_api:
  workers: 2
  
# 调整连接池大小
database:
  pool_size: 20
  max_overflow: 30
```

---

**注意**: 生产环境部署前请仔细测试所有功能，确保系统稳定性和安全性。
