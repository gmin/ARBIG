# ARBIG 交易API接口规范

## 📋 文档信息

- **文档版本**: v2.2
- **更新日期**: 2025-08-15
- **API版本**: v1
- **Web管理系统**: `http://localhost`
- **统一API服务**: `http://localhost/api/v1`
- **核心交易服务**: `http://localhost:8001`
- **策略管理服务**: `http://localhost:8002`

## 🔧 通用规范

### 请求格式
- **Content-Type**: `application/json`
- **字符编码**: `UTF-8`
- **时间格式**: `YYYY-MM-DD HH:mm:ss`

### 响应格式
```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2025-01-04 15:30:25",
  "request_id": "req_123456789"
}
```

### 错误响应
```json
{
  "success": false,
  "error": {
    "code": "SERVICE_ERROR",
    "message": "服务启动失败",
    "details": "CTP连接超时"
  },
  "timestamp": "2025-01-04 15:30:25",
  "request_id": "req_123456789"
}
```

## 🎮 系统控制API

### 1. 服务管理

#### 启动服务
```http
POST /api/v1/services/start
Content-Type: application/json

{
  "service_name": "MarketDataService",
  "config": {
    "symbols": ["au2509", "au2512"],
    "cache_size": 1000
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "service_name": "MarketDataService",
    "status": "running",
    "start_time": "2025-01-04 15:30:25",
    "pid": 12345
  },
  "message": "MarketDataService启动成功"
}
```

#### 停止服务
```http
POST /api/v1/services/stop
Content-Type: application/json

{
  "service_name": "MarketDataService",
  "force": false
}
```

#### 重启服务
```http
POST /api/v1/services/restart
Content-Type: application/json

{
  "service_name": "MarketDataService"
}
```

#### 获取服务状态
```http
GET /api/v1/services/status?service_name=MarketDataService
```

**响应**:
```json
{
  "success": true,
  "data": {
    "service_name": "MarketDataService",
    "status": "running",
    "start_time": "2025-01-04 15:30:25",
    "uptime": "2h 30m 15s",
    "cpu_usage": "5.2%",
    "memory_usage": "120MB",
    "last_heartbeat": "2025-01-04 18:00:40"
  }
}
```

#### 获取所有服务列表
```http
GET /api/v1/services/list
```

**响应**:
```json
{
  "success": true,
  "data": {
    "services": [
      {
        "name": "MarketDataService",
        "display_name": "行情服务",
        "status": "running",
        "required": true,
        "dependencies": ["CTP Gateway"]
      },
      {
        "name": "AccountService", 
        "display_name": "账户服务",
        "status": "stopped",
        "required": false,
        "dependencies": ["CTP Gateway"]
      }
    ]
  }
}
```

### 2. 系统管理

#### 获取系统状态
```http
GET /api/v1/system/status
```

**响应**:
```json
{
  "success": true,
  "data": {
    "system_status": "running",
    "running_mode": "FULL_TRADING",
    "start_time": "2025-01-04 09:30:00",
    "uptime": "8h 30m 40s",
    "ctp_status": {
      "market_data": {
        "connected": true,
        "server": "180.168.146.187:10131",
        "latency": "15ms"
      },
      "trading": {
        "connected": true,
        "server": "180.168.146.187:10130", 
        "latency": "18ms"
      }
    },
    "services_summary": {
      "total": 4,
      "running": 4,
      "stopped": 0,
      "error": 0
    }
  }
}
```

#### 切换运行模式
```http
POST /api/v1/system/mode
Content-Type: application/json

{
  "mode": "MONITOR_ONLY",
  "reason": "用户手动切换"
}
```

#### 系统紧急停止
```http
POST /api/v1/system/emergency/stop
Content-Type: application/json

{
  "reason": "市场异常波动",
  "operator": "admin"
}
```

## 🎯 策略管理API

### 1. 策略控制

#### 获取可用策略列表
```http
GET /api/v1/strategies/list
```

**响应**:
```json
{
  "success": true,
  "data": {
    "strategies": [
      {
        "name": "spread_arbitrage",
        "display_name": "套利策略",
        "description": "黄金期货跨期套利策略",
        "version": "1.0.0",
        "risk_level": "medium",
        "status": "available",
        "author": "ARBIG Team"
      },
      {
        "name": "trend_following",
        "display_name": "趋势跟踪策略", 
        "description": "基于技术指标的趋势跟踪",
        "version": "1.2.0",
        "risk_level": "high",
        "status": "available",
        "author": "ARBIG Team"
      }
    ]
  }
}
```

#### 获取当前运行策略
```http
GET /api/v1/strategies/current
```

**响应**:
```json
{
  "success": true,
  "data": {
    "strategy_name": "spread_arbitrage",
    "display_name": "套利策略",
    "status": "running",
    "start_time": "2025-01-04 09:30:00",
    "runtime": "8h 30m 40s",
    "statistics": {
      "signals_generated": 45,
      "orders_executed": 28,
      "successful_trades": 18,
      "failed_trades": 2,
      "current_profit": 12500.00,
      "today_profit": 8500.00,
      "win_rate": 0.685,
      "sharpe_ratio": 1.85
    }
  }
}
```

#### 切换策略
```http
POST /api/v1/strategies/switch
Content-Type: application/json

{
  "from_strategy": "spread_arbitrage",
  "to_strategy": "trend_following",
  "config": {
    "ma_period": 20,
    "signal_threshold": 0.01,
    "max_position": 5
  },
  "switch_mode": "safe"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "switch_id": "switch_123456",
    "from_strategy": "spread_arbitrage",
    "to_strategy": "trend_following",
    "switch_time": "2025-01-04 18:00:00",
    "status": "completed"
  },
  "message": "策略切换成功"
}
```

#### 暂停/恢复策略
```http
POST /api/v1/strategies/pause
POST /api/v1/strategies/resume
```

### 2. 策略配置

#### 获取策略配置
```http
GET /api/v1/strategies/spread_arbitrage/config
```

**响应**:
```json
{
  "success": true,
  "data": {
    "strategy_name": "spread_arbitrage",
    "config": {
      "spread_threshold": 0.5,
      "max_position": 10,
      "stop_loss": 0.02,
      "take_profit": 0.05,
      "symbols": ["au2509", "au2512"]
    },
    "config_schema": {
      "spread_threshold": {
        "type": "float",
        "min": 0.1,
        "max": 2.0,
        "description": "价差阈值"
      }
    }
  }
}
```

#### 更新策略配置
```http
POST /api/v1/strategies/spread_arbitrage/config
Content-Type: application/json

{
  "config": {
    "spread_threshold": 0.6,
    "max_position": 8
  }
}
```

## 📊 数据查询API

### 1. 行情数据

#### 获取实时行情
```http
GET /api/v1/market/ticks?symbols=au2509,au2512&limit=100
```

**响应**:
```json
{
  "success": true,
  "data": {
    "ticks": [
      {
        "symbol": "au2509",
        "datetime": "2025-01-04 18:00:00",
        "last_price": 485.50,
        "bid_price": 485.40,
        "ask_price": 485.60,
        "volume": 12580,
        "open_interest": 45230,
        "change": 2.30,
        "change_percent": 0.48
      }
    ]
  }
}
```

#### 获取K线数据
```http
GET /api/v1/market/klines?symbol=au2509&interval=1m&limit=100
```

### 2. 账户数据

#### 获取账户信息
```http
GET /api/v1/account/info
```

**响应**:
```json
{
  "success": true,
  "data": {
    "account_id": "123456789",
    "total_assets": 1000000.00,
    "available": 850000.00,
    "margin": 150000.00,
    "frozen": 0.00,
    "profit": 25000.00,
    "today_profit": 5000.00,
    "commission": 120.50,
    "currency": "CNY",
    "update_time": "2025-01-04 18:00:00"
  }
}
```

#### 获取持仓信息
```http
GET /api/v1/account/positions
```

**响应**:
```json
{
  "success": true,
  "data": {
    "positions": [
      {
        "symbol": "au2509",
        "direction": "long",
        "volume": 5,
        "avg_price": 483.20,
        "current_price": 485.50,
        "profit": 11500.00,
        "margin": 120000.00,
        "open_time": "2025-01-04 10:30:00"
      }
    ]
  }
}
```

### 3. 风控数据

#### 获取风险指标
```http
GET /api/v1/risk/metrics
```

**响应**:
```json
{
  "success": true,
  "data": {
    "risk_level": "medium",
    "position_ratio": 0.65,
    "daily_loss": -2500.00,
    "max_drawdown": -8500.00,
    "var_95": -15000.00,
    "leverage": 3.2,
    "concentration": {
      "au2509": 0.8,
      "au2512": 0.2
    }
  }
}
```

## 🔄 实时通信API (WebSocket)

### 连接地址
```
ws://localhost:8000/ws/v1/{channel}
```

### 频道列表
- `/ws/v1/market` - 实时行情推送
- `/ws/v1/account` - 账户变动推送  
- `/ws/v1/orders` - 订单状态推送
- `/ws/v1/system` - 系统状态推送

### 消息格式
```json
{
  "channel": "market",
  "type": "tick",
  "data": {
    "symbol": "au2509",
    "last_price": 485.50,
    "timestamp": "2025-01-04 18:00:00"
  },
  "timestamp": "2025-01-04 18:00:00"
}
```

### 订阅消息
```json
{
  "action": "subscribe",
  "channel": "market",
  "params": {
    "symbols": ["au2509", "au2512"]
  }
}
```

## 🔒 认证和授权

### API密钥认证
```http
Authorization: Bearer your_api_key_here
```

### 权限级别
- **READ**: 只读权限，可查询数据
- **CONTROL**: 控制权限，可操作服务
- **ADMIN**: 管理员权限，可修改配置

## 📝 错误代码

| 错误代码 | 描述 | HTTP状态码 |
|---------|------|-----------|
| SUCCESS | 操作成功 | 200 |
| INVALID_PARAMS | 参数错误 | 400 |
| UNAUTHORIZED | 未授权 | 401 |
| FORBIDDEN | 权限不足 | 403 |
| NOT_FOUND | 资源不存在 | 404 |
| SERVICE_ERROR | 服务错误 | 500 |
| CTP_ERROR | CTP连接错误 | 502 |
| STRATEGY_ERROR | 策略错误 | 503 |

## 🧪 API测试

### 使用curl测试
```bash
# 获取系统状态
curl -X GET "http://localhost:8000/api/v1/system/status" \
  -H "Authorization: Bearer your_api_key"

# 启动服务
curl -X POST "http://localhost:8000/api/v1/services/start" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{"service_name": "MarketDataService"}'
```

### 使用Postman
导入API集合文件: `docs/ARBIG_API_Collection.postman_collection.json`

---

**下一步**: 基于此API规范，开始实现Web指挥中轴的后端API接口。
