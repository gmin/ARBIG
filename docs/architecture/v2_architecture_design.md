# ARBIG 系统架构 V2 设计

## 1. 架构概述

### 1.1 设计目标

解决 V1 架构的核心问题：
- **信息流不完整**：成交回报、订单状态无法到达策略服务
- **职责不清晰**：交易服务同时负责 CTP 连接、行情、交易
- **轮询模式低效**：策略服务 HTTP 轮询获取 tick，延迟高
- **ML 预留**：为未来 ML 模型预测预留接口

### 1.2 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       Ray Cluster (ML)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Ray Serve   │  │ Ray Train   │  │ Ray Data    │              │
│  │ (模型推理)   │  │ (模型训练)   │  │ (数据处理)   │              │
│  └──────▲──────┘  └─────────────┘  └─────────────┘              │
└─────────┼───────────────────────────────────────────────────────┘
          │ HTTP (预测请求)
┌─────────┼───────────────────────────────────────────────────────┐
│         │              Redis Pub/Sub + Stream                    │
└─────────┼───────────────────────────────────────────────────────┘
       ▲  │  ▲              ▲              ▲              ▲
       │  │  │              │              │              │
┌──────┴──┴──┴──┐ ┌─────────┴───┐ ┌────────┴────┐ ┌──────┴──────┐
│    Strategy   │ │   Gateway   │ │   Market    │ │   Trading   │
│     :8002     │ │    :8000    │ │    :8003    │ │    :8001    │
│               │ │             │ │             │ │             │
│  策略引擎      │ │  CTP连接    │ │  K线生成    │ │  订单执行    │
│  指标计算      │ │  事件分发   │ │  行情缓存   │ │  状态管理    │
│  ML调用       │ │             │ │             │ │             │
└───────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
                                                         ▲
┌────────────────────────────────────────────────────────┼────────┐
│                      Web 服务 :8080 (主控)              │        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │        │
│  │ Web UI      │  │ 服务管理     │  │ WebSocket   │─────┘        │
│  │ REST API    │  │ 启动/停止    │  │ 实时推送    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 服务职责定义

| 服务 | 端口 | 职责 |
|------|------|------|
| **Gateway** | 8000 | CTP 连接管理、事件分发到 Redis |
| **Market** | 8003 | Tick 处理、1分钟K线生成、行情缓存 |
| **Trading** | 8001 | 订单执行、成交管理、持仓管理 |
| **Strategy** | 8002 | 策略引擎、技术指标计算、ML调用、信号生成 |
| **Web** | 8080 | 控制台、服务管理、WebSocket推送 |
| **Ray Serve** | 8100 | ML模型推理服务（未来） |

---

## 2. 信息流设计

### 2.1 数据流向

```
                              ┌─────────────────────────────────┐
                              │           Redis                 │
                              │  ┌─────────┐    ┌───────────┐   │
                              │  │ tick:*  │    │ bar:*     │   │
                              │  │ (Pub)   │    │ (Pub)     │   │
                              │  └────┬────┘    └─────┬─────┘   │
                              │       │               │         │
                              │  ┌────┴───────────────┴────┐    │
                              │  │      stream:trade       │    │
                              │  │      stream:position    │    │
                              │  │      stream:order       │    │
                              │  │      stream:cmd         │    │
                              │  └─────────────────────────┘    │
                              └─────────────────────────────────┘
                                    ▲     │           │
        ┌───────────────────────────┘     │           │
        │                    ┌────────────┘           │
        │                    │         ┌──────────────┘
        │                    ▼         ▼
┌───────┴───────┐    ┌───────────┐  ┌─────────┐  ┌──────────┐
│    Gateway    │    │  Market   │  │ Trading │  │ Strategy │
│    :8000      │    │   :8003   │  │  :8001  │  │  :8002   │
└───────┬───────┘    └───────────┘  └────┬────┘  └──────────┘
        │                                │
        ▼                                ▼
┌───────────────┐                ┌───────────────┐
│  vnpy_ctp     │                │  (订单执行)    │
└───────┬───────┘                └───────────────┘
        │
        ▼
    [ CTP ]
```

### 2.2 详细数据流

**行情数据流**：
```
CTP → Gateway → [tick:symbol] → Market → [bar:symbol] → Strategy
                      │                                    ↑
                      └────────────────────────────────────┘
```
- Gateway 发布 tick 到 `tick:{symbol}`
- Market 订阅 tick，生成 bar，发布到 `bar:{symbol}`
- Strategy 同时订阅 tick 和 bar

**交易数据流**：
```
CTP → Gateway → [stream:trade]    → Trading
                                  → Strategy
              → [stream:position] → Trading
                                  → Strategy
```
- Gateway 直接推送 trade/position 给 Trading 和 Strategy

**订单数据流**：
```
Strategy → [stream:order] → Trading → [stream:cmd] → Gateway → CTP
```
- Strategy 发送订单请求到 Trading
- Trading 转换为报单指令发给 Gateway
- Gateway 发送到 CTP

### 2.2 Redis 通道设计

#### Pub/Sub（实时性优先，允许丢失）

| Channel 模式 | 发布者 | 订阅者 | 说明 |
|-------------|--------|--------|------|
| `tick:{symbol}` | Gateway | Market, Strategy | 行情tick，丢失影响小 |
| `bar:{symbol}` | Market | Strategy | 1分钟K线 |

#### Stream（可靠性优先，不允许丢失）

| Stream 名称 | 发布者 | 消费者 | 说明 |
|-------------|--------|--------|------|
| `stream:trade` | Gateway | Trading, Strategy | 成交回报，关键数据 |
| `stream:position` | Gateway | Trading, Strategy | 持仓变化，关键数据 |
| `stream:order_status` | Gateway | Trading, Strategy | 订单状态（含拒单） |
| `stream:order` | Strategy | Trading | 订单请求 |
| `stream:cmd` | Trading | Gateway | 报单指令 |

**Consumer Group 设计**：
- 每个服务使用**独立的 Consumer Group**
- Trading 和 Strategy 各收一份完整消息
- 例：`stream:trade` 有两个 Group：`group:trading` 和 `group:strategy`

### 2.3 各服务订阅/发布关系

| 服务 | Pub/Sub 订阅 | Stream 消费 | 发布/生产 |
|------|-------------|-------------|-----------|
| Gateway | - | `stream:cmd` | `tick:*`, `stream:trade`, `stream:position`, `stream:order_status` |
| Market | `tick:*` | - | `bar:*` |
| Trading | - | `stream:order`, `stream:order_status` | `stream:cmd` |
| Strategy | `tick:*`, `bar:*` | `stream:trade`, `stream:position`, `stream:order_status` | `stream:order` |

### 2.4 状态同步机制

**策略启动时**：
1. 策略服务启动，通过 HTTP 查询 Trading 服务获取当前持仓
2. 初始化 `self.pos` 和相关状态
3. 订阅 Redis 通道，开始接收实时数据

**HTTP 查询接口**（Trading 服务提供）：
- `GET /positions` - 获取当前持仓
- `GET /orders` - 获取未完成订单
- `GET /trades?since={time}` - 获取历史成交

---

## 3. 服务详细设计

### 3.1 Gateway 服务

**职责**：
- 管理 vnpy_ctp 连接（MD + TD）
- 接收 CTP 事件，发布到 Redis
- 接收报单指令，发送到 CTP

**核心组件**：
- `CtpConnector`: vnpy_ctp 封装
- `EventPublisher`: Redis 发布器
- `CommandSubscriber`: 监听报单指令

### 3.2 Market 服务

**职责**：
- 订阅 tick，生成 1 分钟 K 线
- 维护行情缓存
- 提供历史行情查询 API（可选）

**核心组件**：
- `TickSubscriber`: 订阅 tick 数据
- `BarGenerator`: tick → 1min bar
- `MarketCache`: 行情数据缓存

### 3.3 Trading 服务

**职责**：
- 接收策略订单请求
- 转发报单指令到 Gateway
- 管理订单状态、成交记录、持仓

**核心组件**：
- `OrderSubscriber`: 订阅策略订单
- `OrderManager`: 订单状态管理
- `PositionManager`: 持仓管理

### 3.4 Strategy 服务

**职责**：
- 订阅 tick/bar/成交/持仓
- 运行策略引擎
- 计算技术指标，生成交易信号

**核心组件**：
- `DataSubscriber`: 订阅市场数据和交易数据
- `StrategyEngine`: 策略生命周期管理
- `ArrayManager`: K线存储 + 技术指标计算

---

## 4. 数据格式定义

### 4.1 枚举值定义

**订单状态（status）**
| 值 | 说明 |
|-----|------|
| `SUBMITTING` | 提交中 |
| `NOTTRADED` | 未成交（挂单中） |
| `PARTTRADED` | 部分成交 |
| `ALLTRADED` | 全部成交 |
| `CANCELLED` | 已撤销 |
| `REJECTED` | 拒单 |

**方向（direction）**
| 值 | 说明 |
|-----|------|
| `LONG` | 多头 |
| `SHORT` | 空头 |

**开平（offset）**
| 值 | 说明 |
|-----|------|
| `OPEN` | 开仓 |
| `CLOSE` | 平仓 |
| `CLOSETODAY` | 平今（SHFE） |
| `CLOSEYESTERDAY` | 平昨（SHFE） |

**交易所（exchange）**
| 值 | 说明 |
|-----|------|
| `SHFE` | 上海期货交易所（目前仅支持） |

### 4.2 TickData（行情）

Channel: `tick:{symbol}` (Pub/Sub)

```json
{
  "symbol": "au2512",
  "exchange": "SHFE",
  "datetime": "2025-12-23T21:00:01.500",
  "last_price": 650.50,
  "volume": 123456,
  "open_interest": 98765,
  "last_volume": 10,
  "open_price": 648.00,
  "high_price": 651.20,
  "low_price": 647.50,
  "pre_close": 649.00,
  "limit_up": 680.00,
  "limit_down": 620.00,
  "bid_price_1": 650.40,
  "bid_volume_1": 100,
  "ask_price_1": 650.60,
  "ask_volume_1": 80
}
```

### 4.3 BarData（K线）

Channel: `bar:{symbol}` (Pub/Sub)

```json
{
  "symbol": "au2512",
  "exchange": "SHFE",
  "datetime": "2025-12-23T21:01:00",
  "interval": "1m",
  "open_price": 650.00,
  "high_price": 651.20,
  "low_price": 649.80,
  "close_price": 650.50,
  "volume": 1234,
  "open_interest": 98765
}
```

### 4.4 OrderRequest（订单请求）

Stream: `stream:order` (Strategy → Trading)

```json
{
  "request_id": "uuid-xxxx",
  "strategy_name": "MaRsiStrategy",
  "symbol": "au2512",
  "exchange": "SHFE",
  "direction": "LONG",
  "offset": "OPEN",
  "order_type": "LIMIT",
  "price": 650.50,
  "volume": 1,
  "timestamp": "2025-12-23T21:00:01.500"
}
```

### 4.5 TradeData（成交回报）

Stream: `stream:trade` (Gateway → Trading/Strategy)

```json
{
  "trade_id": "12345",
  "order_id": "67890",
  "symbol": "au2512",
  "exchange": "SHFE",
  "direction": "LONG",
  "offset": "OPEN",
  "price": 650.50,
  "volume": 1,
  "datetime": "2025-12-23T21:00:01.500",
  "strategy_name": "MaRsiStrategy"
}
```

### 4.6 PositionData（持仓）

Stream: `stream:position` (Gateway → Trading/Strategy)

```json
{
  "symbol": "au2512",
  "exchange": "SHFE",
  "direction": "LONG",
  "volume": 2,
  "frozen": 0,
  "price": 650.25,
  "pnl": 500.0,
  "yd_volume": 1,
  "datetime": "2025-12-23T21:00:01.500"
}
```

### 4.7 OrderData（订单状态）

Stream: `stream:order_status` (Gateway → Trading)

```json
{
  "order_id": "67890",
  "symbol": "au2512",
  "exchange": "SHFE",
  "direction": "LONG",
  "offset": "OPEN",
  "order_type": "LIMIT",
  "price": 650.50,
  "volume": 1,
  "traded": 1,
  "status": "ALLTRADED",
  "datetime": "2025-12-23T21:00:01.500",
  "strategy_name": "MaRsiStrategy"
}
```

### 4.8 CommandData（报单指令）

Stream: `stream:cmd` (Trading → Gateway)

```json
{
  "cmd_type": "SEND_ORDER",
  "request_id": "uuid-xxxx",
  "symbol": "au2512",
  "exchange": "SHFE",
  "direction": "LONG",
  "offset": "OPEN",
  "order_type": "LIMIT",
  "price": 650.50,
  "volume": 1,
  "timestamp": "2025-12-23T21:00:01.500"
}
```

cmd_type 可选值：`SEND_ORDER`, `CANCEL_ORDER`

---

## 5. 异常处理设计

### 5.1 Redis 断连处理

- **连接方式**：使用 redis-py 连接池，自动重连
- **Pub/Sub 消息**：断连期间丢失，重连后继续（tick/bar 影响小）
- **Stream 消息**：使用 Consumer Group，断连后从断点继续消费

**Stream 配置**：
- 保留策略：最多 10000 条 或 最近 1 天
- Consumer Group：每个服务一个 Consumer

### 5.2 CTP 断连处理（Gateway）

**重连策略**：
```
断连 → 5s → 10s → 30s → 60s（循环）
```

**重连流程**：
1. 记录断连状态
2. 发布断连事件到 Redis（通知其他服务）
3. 启动重连循环
4. 重连成功后：
   - 重新订阅行情
   - 查询持仓/订单
   - 发布重连事件

**断连期间其他服务行为**：
| 服务 | 行为 |
|------|------|
| Market | 暂停 K 线生成 |
| Trading | 拒绝新订单 |
| Strategy | **暂停交易**（不发新信号） |

### 5.3 服务重启恢复

| 服务 | 重启恢复动作 |
|------|-------------|
| **Gateway** | 连接 CTP → 订阅行情 → 查询持仓/订单 → 发布到 Redis |
| **Market** | 订阅 tick → 等待新 tick 重新生成 bar |
| **Trading** | 查询 Gateway 获取持仓/订单 → 订阅 Stream |
| **Strategy** | 查询 Trading 获取持仓 → 从 Stream 断点继续消费 → 订阅 Pub/Sub |

**启动顺序**：Gateway → Market → Trading → Strategy

---

## 6. 配置管理

### 6.1 配置文件结构

```
config/
├── ctp_config.yaml        # CTP 账户配置（已有）
├── redis_config.yaml      # Redis 连接配置
└── strategies/            # 策略配置目录
    ├── ma_rsi.yaml        # MA+RSI 策略参数
    └── xxx.yaml           # 其他策略
```

### 6.2 配置文件示例

**redis_config.yaml**
```yaml
host: localhost
port: 6379
password: ""
db: 0
```

**strategies/ma_rsi.yaml**
```yaml
strategy_name: MaRsiStrategy
symbol: au2512
exchange: SHFE
params:
  fast_window: 10
  slow_window: 30
  rsi_window: 14
  rsi_long: 40
  rsi_short: 60
```

---

## 7. 数据存储

### 7.1 存储方案

| 数据类型 | 存储位置 | 说明 |
|---------|---------|------|
| **tick** | 不持久化 | 实时消费，不存储 |
| **bar** | CSV 文件 | `data/bars/{symbol}/{date}.csv` |
| **订单记录** | 数据库 | SQLite / PostgreSQL |
| **成交记录** | 数据库 | SQLite / PostgreSQL |
| **持仓快照** | 数据库 | 每日收盘记录 |

### 7.2 数据库选择

| 选项 | 优点 | 缺点 |
|------|------|------|
| **SQLite** | 零配置，单文件，简单 | 并发写入受限 |
| **PostgreSQL** | 高性能，功能强大 | 需要额外部署 |

**建议**：先用 SQLite（开发简单），后续需要再迁移 PostgreSQL

### 7.3 数据库表设计（初步）

```sql
-- 订单表
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    order_id TEXT UNIQUE,
    request_id TEXT,
    symbol TEXT,
    exchange TEXT,
    direction TEXT,
    offset TEXT,
    price REAL,
    volume INTEGER,
    traded INTEGER,
    status TEXT,
    strategy_name TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 成交表
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    trade_id TEXT UNIQUE,
    order_id TEXT,
    symbol TEXT,
    exchange TEXT,
    direction TEXT,
    offset TEXT,
    price REAL,
    volume INTEGER,
    strategy_name TEXT,
    traded_at TIMESTAMP
);
```

---

## 8. 风控设计

### 8.1 当前方案：策略级风控

风控逻辑放在 **Strategy 服务**，每个策略自己管理：

| 风控项 | 说明 | 配置位置 |
|--------|------|---------|
| 止损 | 亏损达到阈值平仓 | 策略配置文件 |
| 止盈 | 盈利达到阈值平仓 | 策略配置文件 |
| 最大持仓 | 策略最大持仓手数 | 策略配置文件 |

**策略配置示例**：
```yaml
# strategies/ma_rsi.yaml
risk:
  stop_loss_pct: 2.0     # 止损 2%
  take_profit_pct: 5.0   # 止盈 5%
  max_position: 2        # 最大持仓 2 手
```

### 8.2 未来扩展

如需账户级风控（总仓位限制、下单频率限制等），后续在 Trading 服务添加。

---

## 9. 待讨论细节

### 9.1 性能考虑
- [ ] tick 高频场景下 Redis 性能是否足够？

### 9.2 监控运维
- [ ] 各服务健康检查
- [ ] 日志统一收集

---

## 10. 已确认决策汇总

| 类别 | 决策 |
|------|------|
| **服务划分** | 5 个服务：Gateway, Market, Trading, Strategy, Web |
| **服务通信** | Redis Pub/Sub + Stream |
| **Consumer Group** | 每个服务独立 Group，各收一份消息 |
| **K 线生成** | Market 服务生成 1 分钟 K 线 |
| **指标计算** | Strategy 服务计算 |
| **实时数据** | Pub/Sub（tick, bar） |
| **关键数据** | Stream（trade, position, order, order_status） |
| **订单状态** | Gateway 推送给 Trading 和 Strategy |
| **状态同步** | 启动时 HTTP 查询 + Stream 断点消费 |
| **CTP 重连** | 间隔递增：5s → 10s → 30s → 60s |
| **断连行为** | 暂停交易 |
| **Stream 保留** | 最多 10000 条或 1 天 |
| **配置管理** | CTP、Redis、策略各独立配置文件 |
| **数据存储** | tick 不存，bar 存 CSV，订单/成交存 SQLite |
| **风控** | 策略级风控，每个策略自己管理 |
| **ML 集成** | Ray Serve 独立部署，HTTP 调用 |
| **前端框架** | Vue 3 |
| **UI 组件库** | Element Plus |
| **K 线图表** | TradingView Lightweight Charts |
| **交易所** | 目前仅支持 SHFE |

