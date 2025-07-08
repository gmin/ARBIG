# ARBIG Web监控与风控系统

## 概述

ARBIG Web监控与风控系统是一个独立的Web服务，提供实时交易监控和人工风控干预功能。系统采用前后端分离架构，支持实时数据推送和直观的操作界面。

## 核心功能

### 🔍 实时监控
- **系统状态监控** - 各服务运行状态、连接状态
- **交易数据监控** - 实时订单、成交、持仓信息
- **风险指标监控** - 实时风险级别、盈亏、回撤等
- **行情数据监控** - 实时行情数据展示

### 🛡️ 人工风控干预
- **紧急暂停交易** - 一键暂停所有新订单
- **紧急平仓** - 快速平仓所有持仓（需确认码）
- **策略级控制** - 暂停/恢复特定策略
- **参数调整** - 实时调整风控参数
- **止损设置** - 手动设置止损价格

### 📊 数据分析
- **交易统计** - 详细的交易数据统计
- **风险分析** - 风险指标分析和历史趋势
- **操作日志** - 完整的人工干预操作记录
- **实时预警** - 多级风险预警系统

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend │    │   Web Backend   │    │  Core Trading   │
│   (HTML/JS)     │◄──►│   (FastAPI)     │◄──►│    System       │
│                 │    │                 │    │                 │
│ - 实时仪表板     │    │ - REST API      │    │ - EventEngine   │
│ - 风控操作面板   │    │ - WebSocket     │    │ - Services      │
│ - 数据可视化     │    │ - 数据转换      │    │ - CTP Gateway   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
# 安装Web服务依赖
pip install fastapi uvicorn websockets
```

### 2. 运行方式

#### 方式一：集成模式（推荐）
连接到完整的ARBIG交易系统：

```bash
cd /root/ARBIG
python web_admin/run_web_monitor.py --mode integrated
```

#### 方式二：独立模式
仅运行Web界面（用于开发和测试）：

```bash
cd /root/ARBIG
python web_admin/run_web_monitor.py --mode standalone
```

### 3. 访问界面

打开浏览器访问：http://localhost:8000

## 目录结构

```
web_monitor/
├── __init__.py              # 模块初始化
├── app.py                   # 主应用程序
├── models.py                # 数据模型定义
├── risk_controller.py       # 风控控制器
├── data_provider.py         # 数据提供器
├── run_web_monitor.py       # 启动脚本
├── static/                  # 静态文件
│   └── index.html          # 前端页面
└── README.md               # 使用文档
```

## API接口

### 数据查询接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/status` | GET | 获取系统状态 |
| `/api/positions` | GET | 获取持仓信息 |
| `/api/orders` | GET | 获取订单信息 |
| `/api/trades` | GET | 获取成交信息 |
| `/api/market_data` | GET | 获取行情数据 |
| `/api/risk_metrics` | GET | 获取风险指标 |
| `/api/statistics` | GET | 获取统计信息 |
| `/api/operation_log` | GET | 获取操作日志 |

### 风控操作接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/risk/emergency_halt` | POST | 紧急暂停交易 |
| `/api/risk/emergency_close` | POST | 紧急平仓 |
| `/api/risk/halt_strategy` | POST | 暂停策略 |
| `/api/risk/resume_trading` | POST | 恢复交易 |
| `/api/risk/update_position_limit` | POST | 更新仓位限制 |
| `/api/risk/set_stop_loss` | POST | 设置止损 |

### WebSocket接口

- `/ws` - 实时数据推送

## 使用指南

### 1. 系统监控

#### 查看系统状态
- 各服务运行状态（绿色=正常，红色=异常）
- CTP连接状态
- 当前风险级别
- 交易暂停状态

#### 监控交易数据
- 实时查看活跃订单
- 监控当前持仓
- 查看最新成交记录
- 观察行情数据变化

### 2. 风控操作

#### 紧急操作
```javascript
// 紧急暂停交易
POST /api/risk/emergency_halt
{
    "reason": "市场异常波动",
    "operator": "trader_001"
}

// 紧急平仓（需要确认码）
POST /api/risk/emergency_close
{
    "reason": "系统故障",
    "operator": "trader_001",
    "confirmation_code": "EMERGENCY_CLOSE_123"
}
```

#### 策略控制
```javascript
// 暂停特定策略
POST /api/risk/halt_strategy
{
    "target": "arbitrage_v1",
    "reason": "策略异常",
    "operator": "trader_001"
}
```

#### 参数调整
```javascript
// 调整仓位限制
POST /api/risk/update_position_limit
{
    "symbol": "au2509",
    "new_limit": 50.0,
    "reason": "降低风险敞口",
    "operator": "trader_001"
}
```

### 3. 实时监控

#### WebSocket数据格式
```javascript
{
    "type": "realtime_update",
    "timestamp": "2025-01-04T10:30:00",
    "data": {
        "system_status": {...},
        "risk_metrics": {...},
        "statistics": {...}
    }
}
```

#### 风险预警
```javascript
{
    "type": "risk_alert",
    "timestamp": "2025-01-04T10:30:00",
    "data": {
        "level": "WARNING",
        "message": "日内亏损接近限制",
        "details": {...}
    }
}
```

## 安全特性

### 1. 操作确认
- 危险操作需要确认码
- 所有操作记录操作员信息
- 完整的操作日志追踪

### 2. 权限控制
- 操作员身份验证
- 分级操作权限
- 敏感操作双重确认

### 3. 数据安全
- 实时数据加密传输
- 操作日志持久化存储
- 异常操作自动报警

## 配置说明

### 启动参数

```bash
python run_web_monitor.py [OPTIONS]

Options:
  --mode {standalone,integrated}  运行模式 [default: integrated]
  --host TEXT                     监听地址 [default: 0.0.0.0]
  --port INTEGER                  监听端口 [default: 8000]
```

### 环境变量

```bash
# Web服务配置
export ARBIG_WEB_HOST=0.0.0.0
export ARBIG_WEB_PORT=8000
export ARBIG_WEB_DEBUG=false

# 日志配置
export ARBIG_LOG_LEVEL=INFO
export ARBIG_LOG_FILE=/var/log/arbig_web.log
```

## 故障排除

### 常见问题

#### 1. 无法连接到交易系统
**现象**: Web界面显示"核心服务未连接"

**解决方案**:
- 检查交易系统是否正常运行
- 确认CTP连接状态
- 查看服务启动日志

#### 2. WebSocket连接失败
**现象**: 实时数据不更新

**解决方案**:
- 检查网络连接
- 确认防火墙设置
- 重新刷新页面

#### 3. 风控操作失败
**现象**: 点击风控按钮无响应

**解决方案**:
- 检查操作权限
- 确认确认码正确
- 查看操作日志

### 日志查看

```bash
# 查看Web服务日志
tail -f logs/arbig_web.log

# 查看错误日志
grep ERROR logs/arbig_web.log
```

## 开发指南

### 1. 添加新的API接口

```python
@app.post("/api/custom/action")
async def custom_action(request: CustomRequest):
    # 实现自定义操作
    return {"success": True}
```

### 2. 扩展前端功能

```javascript
// 添加新的数据显示
function updateCustomData(data) {
    document.getElementById('customData').innerHTML = data;
}
```

### 3. 自定义风控规则

```python
class CustomRiskController(WebRiskController):
    async def custom_risk_check(self, params):
        # 实现自定义风控逻辑
        pass
```

## 部署建议

### 1. 生产环境部署

```bash
# 使用Gunicorn部署
pip install gunicorn
gunicorn web_monitor.app:app -w 4 -k uvicorn.workers.UvicornWorker

# 使用Nginx反向代理
# /etc/nginx/sites-available/arbig-web
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 2. 监控和日志

```bash
# 使用systemd管理服务
# /etc/systemd/system/arbig-web.service
[Unit]
Description=ARBIG Web Monitor
After=network.target

[Service]
Type=simple
User=arbig
WorkingDirectory=/opt/arbig
ExecStart=/opt/arbig/venv/bin/python web_monitor/run_web_monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 版本历史

- **v1.0.0** (2025-01-04): 初始版本
  - 基础监控功能
  - 人工风控干预
  - 实时数据推送
  - Web界面

---

**维护者**: ARBIG开发团队  
**最后更新**: 2025-01-04
