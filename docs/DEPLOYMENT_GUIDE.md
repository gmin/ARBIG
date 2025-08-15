# ARBIG 部署指南

## 📋 部署概述

本指南介绍 ARBIG 当前版本的部署方法，基于微服务架构（三服务）。

## 🏗️ 系统架构

```
ARBIG 微服务架构
├── 核心交易服务 (trading_service) - 端口8001
├── 策略管理服务 (strategy_service) - 端口8002  
└── Web管理服务 (web_admin_service) - 端口80
```

## 🚀 快速部署

### 1. 环境准备

```bash
# 1. 确保已安装conda和vnpy环境
conda activate vnpy

# 2. 进入项目目录
cd /root/ARBIG

# 3. 检查环境依赖
python -c "import vnpy; print('vnpy环境正常')"
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

### 3. 启动系统

#### 🎯 推荐方式（一键启动）
```bash
# 一键启动所有服务
python start_with_logs.py
```

#### 🔧 手动启动各服务
```bash
# 1. 启动核心交易服务
conda activate vnpy
python services/trading_service/main.py --port 8001

# 2. 启动策略管理服务  
conda activate vnpy
python services/strategy_service/main.py --port 8002

# 3. 启动Web管理服务
conda activate vnpy
python services/web_admin_service/main.py --port 80
```

### 4. 验证部署

```bash
# 检查服务端口
netstat -tlnp | grep -E "(80|8001|8002)"

# 测试API连接
curl http://localhost:8001/real_trading/positions
curl http://localhost/api/v1/trading/positions

# 访问Web界面
# 浏览器打开: http://localhost
```

## 🔧 生产环境部署

### 1. 系统要求
- **操作系统**: Linux (推荐CentOS/Ubuntu)
- **Python**: 3.8+ 
- **内存**: 最少2GB，推荐4GB+
- **磁盘**: 最少10GB可用空间

### 2. 服务管理

#### 使用systemd管理服务
创建服务文件 `/etc/systemd/system/arbig.service`:
```ini
[Unit]
Description=ARBIG Trading System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/ARBIG
ExecStart=/root/miniconda3/envs/vnpy/bin/python start_with_logs.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl enable arbig
sudo systemctl start arbig
sudo systemctl status arbig
```

### 3. 日志管理

```bash
# 查看系统日志
tail -f logs/*.log

# 查看服务状态
systemctl status arbig

# 重启服务
systemctl restart arbig
```

## 🛡️ 安全配置

### 1. 防火墙设置
```bash
# 开放必要端口
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=8001/tcp  
firewall-cmd --permanent --add-port=8002/tcp
firewall-cmd --reload
```

### 2. 访问控制
- Web界面默认监听所有IP (0.0.0.0:80)
- 生产环境建议配置反向代理或VPN访问

## 🔍 故障排除

### 常见问题

#### 1. 端口占用
```bash
# 查看端口占用
netstat -tlnp | grep -E "(80|8001|8002)"

# 杀死占用进程
kill -9 <PID>
```

#### 2. CTP连接失败
- 检查网络连接
- 确认账户信息正确
- 确认在交易时间内测试

#### 3. 服务启动失败
```bash
# 查看详细错误信息
python start_with_logs.py

# 检查日志文件
tail -f logs/*.log
```

## 📊 监控和维护

### 1. 健康检查
系统每5分钟自动进行健康检查，检查各服务端口状态。

### 2. 日志轮转
建议配置logrotate管理日志文件大小。

### 3. 备份策略
- 定期备份配置文件
- 备份交易日志和数据库

---

**部署指南版本**: v3.1  
**最后更新**: 2025-08-15  
**适用架构**: 微服务架构（三服务）
