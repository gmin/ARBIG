# ARBIG 完整系统架构 - Trading Service → Strategy Service → Strategy Instance

## 架构决策摘要

| 决策 | 结论 |
| --- | --- |
| 服务划分 | 三层保持（Trading / Strategy / Web Admin），行情暂不独立拆分 |
| Trading Service 断开 | 立即暂停所有策略，重连后持仓对齐再恢复 |
| 信号传递 | Strategy → Trading，HTTP POST，策略与数据源解耦 |
| 信号分层 | 分析 → 决策 → 生成，策略代码必须遵守 |
| 触发入口 | on_bar() 处理信号生成，on_tick() 处理实时风控 |
| 持仓查询 | 每次下单前 HTTP 查询真实持仓，正确性优先 |

## 架构图

```mermaid
flowchart TB
    subgraph External["外部系统"]
        CTPServer["CTP 服务器<br/>SimNow / 实盘<br/>行情 + 交易"]
    end

    subgraph TradingService["Trading Service (Port 8001)"]
        direction TB

        subgraph CtpIntegration["CTP 接入 (ctp_integration.py)"]
            VnpyEngine["vnpy 引擎<br/>EventEngine + MainEngine + CtpGateway"]
            ConnectMgr["初始化与连接<br/>initialize() / connect()"]
            Subscribe["订阅管理<br/>subscribe() / auto_subscribe()"]
            OrderMgr["订单执行<br/>send_order() / cancel_order()"]
            QueryMgr["账户与持仓查询<br/>get_account_info() / get_position_info()"]
            EventHandlers["事件处理器<br/>_on_tick / _on_order / _on_trade<br/>_on_account / _on_position / _on_contract"]
        end

        subgraph DataCache["数据缓存"]
            Ticks["ticks: dict"]
            Positions["positions: dict"]
            Orders["orders: dict"]
            Trades["trades: dict"]
            Account["account: AccountData"]
        end

        subgraph RestAPI["REST API (real_trading.py)"]
            TickAPI["GET /tick/{symbol}"]
            PositionAPI["GET /positions"]
            AccountAPI["GET /account"]
            SignalAPI["POST /strategy_signal"]
            StatusAPI["GET /status"]
        end

        subgraph WsEndpoint["WebSocket (websocket_api.py)"]
            WsAPI["WS /ws/trading<br/>推送 tick / order / trade"]
        end

        EventHandlers --> DataCache
        Ticks --> TickAPI
        Positions --> PositionAPI
        Account --> AccountAPI
        Ticks --> WsAPI
        Orders --> WsAPI
        Trades --> WsAPI
        SignalAPI --> OrderMgr
    end

    subgraph StrategyService["Strategy Service (Port 8002)"]
        direction TB

        subgraph Engine["StrategyEngine (strategy_engine.py)"]
            EngineInit["初始化 / 加载策略类"]
            WsLoop["_websocket_loop()<br/>接收实时 tick/order/trade 推送"]
            DataLoop["_data_processing_loop()<br/>HTTP 轮询补充行情"]
            FetchData["_fetch_market_data()"]
            TradingTime["_is_trading_time()"]
            DistributeTick["分发 tick 事件"]
            OnBarCallback["_on_bar()<br/>K线回调，分发 bar 事件"]
            ConnMonitor["连接监控<br/>断连 → 暂停所有策略<br/>重连 → 持仓对齐 → 恢复"]
        end

        subgraph DataTools["数据工具 (data_tools.py)"]
            BarGenerator["BarGenerator<br/>Tick → 1分钟 K线"]
            ArrayManager["ArrayManager<br/>K线数组 + 技术指标"]
        end

        subgraph SignalSender["SignalSender (signal_sender.py)"]
            SendSignal["send_signal()<br/>HTTP POST 交易信号"]
            HealthCheck["health_check()"]
            GetPositions["get_positions()<br/>HTTP GET 查询持仓"]
        end

        subgraph Template["ARBIGCtaTemplate (cta_template.py)"]
            Lifecycle["生命周期<br/>start() / stop() / pause()"]
            TradeMethods["交易方法<br/>buy() / sell() / short() / cover()"]
            TickCallback["on_tick() → on_tick_impl()<br/>实时风控入口"]
            BarCallback["on_bar() → on_bar_impl()<br/>主信号生成入口"]
            TradeCallback["on_trade() → on_trade_impl()<br/>成交回调，维护本地持仓（快速参考）"]
            SendOrder["_send_order()<br/>创建 SignalData"]
        end

        WsLoop --> DistributeTick
        FetchData --> BarGenerator
        BarGenerator --> OnBarCallback
        BarGenerator --> ArrayManager
        TradeMethods --> SendOrder
        SendOrder --> GetPositions
        GetPositions -->|"持仓校验通过"| SendSignal
    end

    subgraph Strategy["策略实例 (ARBIGCtaTemplate 子类)"]
        direction TB

        subgraph StrategyCallbacks["生命周期回调"]
            SOnInit["on_init()"]
            SOnStart["on_start()"]
            SOnBar["on_bar_impl(bar)<br/>主信号入口"]
            SOnTick["on_tick_impl(tick)<br/>实时风控"]
            SOnTrade["on_trade_impl(trade)<br/>成交后附加处理"]
        end

        subgraph SignalPipeline["信号生成流水线（必须遵守）"]
            Analyze["阶段1: 市场状态分析"]
            Decision["阶段2: 交易方向决策"]
            Generate["阶段3: 信号参数生成"]
        end

        subgraph RiskControl["实时风控 (on_tick 驱动)"]
            StopLoss["止损检查"]
            TakeProfit["止盈检查"]
            PosLimit["持仓上限检查"]
        end

        subgraph StrategyVars["策略状态"]
            Params["参数: trade_volume, max_position 等"]
            AM["self.am: ArrayManager"]
            LocalPos["本地持仓（快速参考，非权威）"]
        end

        SOnBar --> Analyze
        Analyze --> Decision
        Decision --> Generate

        SOnTick --> StopLoss
        SOnTick --> TakeProfit
        SOnTick --> PosLimit
    end

    %% 主数据流
    CTPServer <-->|"TCP 连接"| VnpyEngine
    VnpyEngine --> EventHandlers

    WsAPI -->|"① WS 推送 tick/order/trade"| WsLoop
    FetchData -->|"② HTTP GET /tick（补充）"| TickAPI
    DistributeTick -->|"③ on_tick()"| SOnTick
    OnBarCallback -->|"④ on_bar()"| SOnBar
    DistributeTick -->|"⑤ on_trade()"| SOnTrade

    %% 下单链路
    Generate -->|"⑥ buy()/sell()"| TradeMethods
    GetPositions -->|"⑦ HTTP GET /positions（必经）"| PositionAPI
    SendSignal -->|"⑧ HTTP POST /strategy_signal"| SignalAPI
    OrderMgr -->|"⑨ send_order()"| VnpyEngine

    %% 异常路径
    ConnMonitor -.->|"断连 → 暂停"| Lifecycle
    ConnMonitor -.->|"重连 → 查持仓 → 恢复"| GetPositions
```

## 关键数据流说明

### 正常路径

1. CTP 服务器通过 TCP 向 vnpy 引擎推送行情和成交
2. Trading Service 的事件处理器更新内部数据缓存
3. Trading Service 通过 WebSocket（①）向 Strategy Service 推送实时数据
4. Strategy Engine 同时通过 HTTP 轮询（②）补充行情，覆盖 WebSocket 断连恢复期
5. tick 事件分发到策略的 `on_tick_impl()`（③），驱动实时风控
6. BarGenerator 合成 K 线后，通过 `on_bar_impl()`（④）触发策略信号生成
7. 成交回报通过 `on_trade_impl()`（⑤）回调策略，父类同时更新本地持仓快速参考
8. 策略信号生成后，调用 `buy()/sell()` 等交易方法（⑥）
9. 下单前，必须通过 HTTP 查询 Trading Service 的真实持仓（⑦），校验通过后才发送信号
10. 信号通过 HTTP POST 发送到 Trading Service（⑧）
11. Trading Service 通过 vnpy 引擎执行订单（⑨）

### 异常路径：Trading Service 断连

1. Strategy Engine 的连接监控检测到 WebSocket 断开
2. 立即暂停所有运行中的策略（冻结信号生成和下单，保留策略状态）
3. 持续尝试 WebSocket 重连
4. 重连成功后，先通过 HTTP 查询 Trading Service 的真实持仓
5. 将远程持仓与本地状态对齐（远程为准）
6. 对齐完成后，恢复策略运行

### 持仓数据的两层设计

- **权威来源**：Trading Service 的 `GET /positions`，反映 CTP 侧真实持仓
- **快速参考**：父类 `on_trade()` 维护的本地 `pos` / `long_pos` / `short_pos`
- **使用规则**：日常风控可参考本地状态；下单前必须查远程；发现不一致时以远程为准并记录告警

---

最后更新：2026-03-13
文档版本：v4.0
