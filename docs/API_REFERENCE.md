# ARBIG API 接口参考

## 📋 文档信息

- **文档版本**: v3.1
- **更新日期**: 2025-08-15
- **API版本**: v1
- **Web管理服务**: `http://localhost`
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
  "timestamp": "2025-08-15 15:30:25"
}
```

### 错误响应
```json
{
  "success": false,
  "data": null,
  "message": "错误描述",
  "timestamp": "2025-08-15 15:30:25"
}
```

## 📊 核心交易API (端口8001)

### 1. 持仓管理

#### 获取持仓信息
```http
GET /real_trading/positions
```

**响应**:
```json
{
  "success": true,
  "data": {
    "au2510": {
      "symbol": "au2510",
      "long_position": 3,
      "short_position": 0,
      "long_today": 2,
      "long_yesterday": 1,
      "long_price": 520.50,
      "current_price": 521.20,
      "long_pnl": 210.0,
      "position_detail": {
        "long": {
          "total": 3,
          "today": 2,
          "yesterday": 1
        }
      }
    }
  }
}
```

### 2. 交易操作

#### 手动交易
```http
POST /real_trading/manual_trade
Content-Type: application/json

{
  "symbol": "au2510",
  "direction": "BUY",
  "volume": 1,
  "price": 520.50,
  "order_type": "LIMIT",
  "offset": "OPEN"
}
```

#### 智能平仓
```http
POST /real_trading/simple_close
Content-Type: application/json

{
  "symbol": "au2510",
  "direction": "long",
  "volume": 2,
  "offset_type": "TODAY",
  "order_type": "MARKET"
}
```

### 3. 系统状态

#### 获取CTP状态
```http
GET /real_trading/status
```

**响应**:
```json
{
  "success": true,
  "data": {
    "ctp_status": {
      "trading_connected": true,
      "market_data_connected": true,
      "trading_server": "182.254.243.31:30001",
      "market_server": "182.254.243.31:30011"
    }
  }
}
```

## 🎛️ Web管理API (端口80)

### 1. 持仓查询

#### 获取持仓
```http
GET /api/v1/trading/positions
```

### 2. 交易操作

#### 手动交易
```http
POST /api/v1/trading/manual_trade
Content-Type: application/json

{
  "symbol": "au2510",
  "direction": "BUY",
  "volume": 1,
  "order_type": "MARKET"
}
```

#### 平仓操作
```http
POST /api/v1/trading/simple_close
Content-Type: application/json

{
  "symbol": "au2510",
  "direction": "long",
  "volume": 1,
  "offset_type": "TODAY"
}
```

### 3. 系统监控

#### 获取系统状态
```http
GET /api/v1/system/status
```

## 🎯 策略管理API (端口8002)

### 1. 策略状态

#### 获取策略列表
```http
GET /strategies
```

#### 获取策略状态
```http
GET /strategies/{strategy_id}/status
```

### 2. 策略控制

#### 启动策略
```http
POST /strategies/{strategy_id}/start
```

#### 停止策略
```http
POST /strategies/{strategy_id}/stop
```

## 🔍 API使用示例

### 完整的平仓流程
```javascript
// 1. 获取持仓信息
const positions = await fetch('/api/v1/trading/positions');

// 2. 智能平仓（前端控制）
const closeResult = await fetch('/api/v1/trading/simple_close', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    symbol: 'au2510',
    direction: 'long',
    volume: 2,
    offset_type: 'TODAY'
  })
});
```

### 手动交易流程
```javascript
// 开仓
const openResult = await fetch('/api/v1/trading/manual_trade', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    symbol: 'au2510',
    direction: 'BUY',
    volume: 1,
    order_type: 'MARKET'
  })
});
```

## 📝 注意事项

### 1. 今昨仓处理
- 系统自动识别今昨仓
- 前端控制平仓逻辑
- 优先平今仓（手续费更低）

### 2. 错误处理
- 所有API都返回统一的错误格式
- 检查`success`字段判断操作是否成功
- `message`字段包含详细错误信息

### 3. 交易时间
- CTP连接在非交易时间可能失败
- 建议在交易时间内进行测试

---

**API文档版本**: v3.1  
**最后更新**: 2025-08-15  
**基于**: 当前微服务架构
