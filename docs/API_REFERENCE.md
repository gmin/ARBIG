# ARBIG API 接口参考

## 文档信息

- 文档版本: `v4.0`
- 更新日期: `2026-03-13`
- API版本: `v1`
- Web 管理服务: `http://localhost`
- Trading Service: `http://localhost:8001`
- Strategy Service: `http://localhost:8002`

## 当前服务边界

ARBIG 当前采用三层边界：

1. `Trading Service`
   - 负责 CTP 连接、行情、账户、持仓、订单执行
2. `Strategy Service`
   - 负责策略注册、启动停止、策略状态、触发记录、紧急停止
3. `Web Admin`
   - 负责页面展示与聚合代理，不再提供手动下单和平仓 UI

## 通用约定

- 请求体默认使用 `application/json`
- 时间字段以服务端实际返回为准，当前多数接口使用 `ISO 8601`
- 大多数业务接口返回 `success`、`data`、`message`、`timestamp`

示例响应：

```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2026-03-13T18:30:25"
}
```

## Trading Service API (8001)

### 行情与连接

```http
GET /real_trading/status
GET /real_trading/tick/{symbol}
POST /real_trading/subscribe/{symbol}
POST /real_trading/test_connection
```

用途：

- 查询 CTP 连接状态
- 获取指定合约最新 Tick
- 手动订阅合约行情
- 触发一次连接测试

### 账户与持仓

```http
GET /real_trading/account
GET /real_trading/positions
GET /real_trading/orders
GET /real_trading/trades/{strategy_name}
```

用途：

- 获取账户资金
- 获取实时持仓
- 获取当前订单列表
- 查询某个策略相关成交

### 订单执行

```http
POST /real_trading/order
DELETE /real_trading/order/{order_id}
POST /real_trading/strategy_signal
```

说明：

- `POST /real_trading/order` 是当前通用下单接口
- `POST /real_trading/strategy_signal` 用于 Strategy Service 向 Trading Service 发送策略信号
- 旧的 `manual_trade` 不再作为当前文档推荐接口
- `simple_close` 仍存在于代码中，但不再作为 Web 端公开工作流的一部分

下单请求示例：

```json
{
  "symbol": "au2604",
  "direction": "BUY",
  "volume": 1,
  "price": 0,
  "order_type": "MARKET",
  "offset": "OPEN"
}
```

## Strategy Service API (8002)

### 服务状态

```http
GET /
GET /status
GET /engine/status
GET /strategies
GET /strategies/{strategy_name}
GET /strategies/types
GET /strategies/triggers
```

说明：

- `GET /strategies` 返回当前策略列表与状态
- `GET /strategies/{strategy_name}` 返回单个策略状态
- `GET /strategies/triggers` 返回策略触发/交易记录摘要

### 策略控制

```http
POST /strategies/register
POST /strategies/{strategy_name}/start
POST /strategies/{strategy_name}/stop
POST /strategies/{strategy_name}/params
DELETE /strategies/{strategy_name}
POST /emergency_stop
```

说明：

- `POST /emergency_stop` 当前会停止所有策略
- 紧急停止当前不负责统一撤销所有挂单，撤单仍应通过 Trading Service 处理

### 与交易服务协同

```http
GET /trading/status
GET /trading/positions
POST /strategies/{strategy_name}/trade
POST /strategies/{strategy_name}/position
```

用途：

- 查询 Trading Service 状态
- 查询 Trading Service 持仓
- 更新策略交易统计与持仓统计

## Web Admin 聚合 API (80)

Web 端通过 `services/web_admin_service/api/trading.py` 聚合两类后端服务。

### 配置与基础信息

```http
GET /api/v1/trading/config/main_contract
POST /api/v1/trading/config/main_contract
GET /api/v1/trading/contracts/config
GET /api/v1/trading/market/current
```

### 交易监控

```http
GET /api/v1/trading/ctp_status
GET /api/v1/trading/account
GET /api/v1/trading/positions
GET /api/v1/trading/tick/{symbol}
```

说明：

- 这些接口主要代理到 Trading Service
- Web 总控台当前以监控为主，不再提供手动下单和平仓页面操作

### 策略管理

```http
GET /api/v1/trading/strategy/status
GET /api/v1/trading/strategy/triggers
POST /api/v1/trading/emergency_stop
GET /api/v1/trading/strategies
GET /api/v1/trading/strategies/types
POST /api/v1/trading/strategies/{strategy_name}/start
POST /api/v1/trading/strategies/{strategy_name}/stop
POST /api/v1/trading/strategies/{strategy_name}/params
POST /api/v1/trading/strategies/register
```

说明：

- 这些接口当前统一代理到 Strategy Service
- Web 层保留策略管理与紧急停止，不再承担交易执行职责

## 推荐调用路径

### 页面监控类调用

- Web 页面调用 `Web Admin` 聚合接口
- Web Admin 再分发到 Trading Service 或 Strategy Service

### 策略执行类调用

- 策略引擎直接调用 Strategy Service
- Strategy Service 再通过 `strategy_signal` 调用 Trading Service

## 注意事项

1. 非交易时间 CTP 连接、行情、账户返回异常是正常现象
2. Web 端已裁剪为监控与策略管理界面，不应再依赖手动交易和平仓接口
3. 若文档与代码不一致，应优先以以下文件中的实际路由为准：
   - `services/trading_service/api/real_trading.py`
   - `services/strategy_service/main.py`
   - `services/web_admin_service/api/trading.py`

---

文档版本: `v4.0`  
最后更新: `2026-03-13`
