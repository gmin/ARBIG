# 黄金跨市场基差套利项目 (Hong Kong CNH Gold vs Shanghai CNY Gold Arbitrage)

## 1. 项目目标

本项目旨在探索和实现香港离岸人民币黄金（例如，通过香港交易所交易的黄金合约，以CNH计价）与上海黄金交易所的黄金主力合约（例如，AU(T+D) 或相关期货合约，以CNY计价）之间的基差套利机会。

核心策略是利用同一标的（黄金）在不同市场、不同币种计价下产生的临时价格差异，通过同时进行买入低价市场黄金、卖出高价市场黄金的操作来获取无风险或低风险利润。

## 2. 选定技术框架

经过初步调研和比较，本项目选定 **`vnpy`** 作为核心的量化交易开发和执行框架。

选择 `vnpy` 的主要原因包括：
*   **强大的多市场/多接口接入能力 (`Gateway` 机制)**：原生支持同时连接和管理来自不同交易所或经纪商的行情和交易通道，这对于跨市场套利至关重要。
*   **成熟的策略开发环境 (`CtaStrategy` 引擎)**：提供了标准化的事件驱动策略模板，便于开发、测试和管理套利逻辑。
*   **相对完善的生态系统**：拥有活跃的社区、丰富的文档资源以及多种可用的功能模块。
*   **Python 主力语言**：便于快速开发和集成。

## 3. 系统架构设计

### 3.1 事件驱动架构

系统采用**事件驱动架构**，实现组件间的解耦和高效通信：

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据源适配器   │───▶│   事件引擎      │───▶│   策略模块      │
│  (MT5/CTP)      │    │  (EventEngine)  │    │  (Strategies)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   主控制器      │
                       │ (MainController)│
                       └─────────────────┘
```

**核心特点：**
- **单线程事件循环**：简化并发处理，便于调试和维护
- **事件持久化**：支持事件回放和回测
- **策略可插拔**：基于抽象基类，便于扩展新策略
- **数据源统一**：支持多种数据源的无缝切换

### 3.2 事件类型定义

系统定义了完整的事件类型体系：

```python
# 行情事件
TICK_EVENT = "TICK_EVENT"           # Tick行情事件
BAR_EVENT = "BAR_EVENT"             # K线事件

# 交易事件
ORDER_EVENT = "ORDER_EVENT"         # 订单事件
TRADE_EVENT = "TRADE_EVENT"         # 成交事件
ACCOUNT_EVENT = "ACCOUNT_EVENT"     # 账户事件

# 策略事件
SIGNAL_EVENT = "SIGNAL_EVENT"       # 策略信号事件
SPREAD_EVENT = "SPREAD_EVENT"       # 基差事件

# 系统事件
LOG_EVENT = "LOG_EVENT"             # 日志事件
ERROR_EVENT = "ERROR_EVENT"         # 错误事件
```

## 4. 代码结构

```
ARBIG/
├── core/                          # 核心框架
│   ├── event_engine.py           # 事件驱动引擎
│   ├── constants.py              # 事件类型常量
│   ├── strategy_base.py          # 策略基类
│   ├── data.py                   # 数据管理器
│   ├── strategy.py               # 套利策略逻辑
│   ├── trader.py                 # 交易执行
│   ├── risk.py                   # 风控模块
│   └── storage.py                # 数据存储
├── strategies/                    # 策略实现
│   ├── spread_arbitrage.py       # 基差套利策略
│   └── shfe_quant.py             # 上海市场量化策略
├── data/                         # 数据适配器
│   ├── mt5/                      # MT5数据源
│   └── shfe/                     # 上期所数据源
├── config.yaml                   # 系统配置文件
├── main.py                       # 主控制器
└── requirements.txt              # 项目依赖
```

## 5. 策略实现

### 5.1 基差套利策略 (SpreadArbitrageStrategy)

**策略逻辑：**
- 实时监控香港和上海黄金价格
- 计算基差：`基差 = 上海价格 - 香港价格`
- 当基差超过阈值时生成套利信号
- 支持双向套利：买上海卖香港 / 买香港卖上海

**核心参数：**
```yaml
spread_threshold: 0.5      # 基差阈值
max_position: 1000         # 最大持仓
shfe_symbol: "AU9999"      # 上期所合约
mt5_symbol: "XAUUSD"       # MT5合约
```

### 5.2 上海市场量化策略 (SHFEQuantStrategy)

**策略类型：**
1. **趋势跟踪策略**：基于移动平均线交叉
2. **均值回归策略**：基于RSI指标
3. **突破策略**：基于布林带

**技术指标：**
- 移动平均线（MA5/MA20）
- RSI指标（14周期）
- 布林带（20周期，2倍标准差）

#### 5.2.1 趋势跟踪策略 (Trend Following)

**策略原理：**
趋势跟踪策略基于"趋势延续"的市场假设，当短期均线上穿长期均线时，认为上升趋势确立，反之则认为下降趋势确立。

**信号生成逻辑：**
```python
# 计算移动平均线
ma_short = np.mean(prices[-ma_short_period:])  # 短期均线
ma_long = np.mean(prices[-ma_long_period:])    # 长期均线

# 趋势信号
if ma_short > ma_long and position <= 0:
    return 'BUY'    # 金叉，买入信号
elif ma_short < ma_long and position >= 0:
    return 'SELL'   # 死叉，卖出信号
```

**参数配置：**
```yaml
strategy_type: "trend"
ma_short: 5         # 短期均线周期
ma_long: 20         # 长期均线周期
max_position: 1000  # 最大持仓
```

**适用场景：**
- 市场处于明显趋势阶段
- 波动率相对较低
- 适合中长期持仓

**风险提示：**
- 震荡市场中可能产生频繁假信号
- 趋势转折时可能滞后
- 需要合理的止损设置

#### 5.2.2 均值回归策略 (Mean Reversion)

**策略原理：**
均值回归策略基于"价格偏离均值后会回归"的假设，当RSI指标显示超买或超卖时，预期价格会向均值回归。

**信号生成逻辑：**
```python
# 计算RSI指标
rsi = calculate_rsi(prices, rsi_period)

# 均值回归信号
if rsi < rsi_oversold and position <= 0:
    return 'BUY'     # 超卖，买入信号
elif rsi > rsi_overbought and position >= 0:
    return 'SELL'    # 超买，卖出信号
```

**RSI计算公式：**
```python
def calculate_rsi(prices, period):
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
```

**参数配置：**
```yaml
strategy_type: "mean_reversion"
rsi_period: 14           # RSI计算周期
rsi_overbought: 70       # 超买阈值
rsi_oversold: 30         # 超卖阈值
max_position: 1000       # 最大持仓
```

**适用场景：**
- 震荡市场环境
- 价格在一定区间内波动
- 适合短线交易

**风险提示：**
- 强趋势市场中可能过早平仓
- 需要准确判断超买超卖阈值
- 极端行情下可能失效

#### 5.2.3 突破策略 (Breakout)

**策略原理：**
突破策略基于"价格突破关键阻力/支撑位后会延续方向"的假设，当价格突破布林带上轨或下轨时，预期会继续向突破方向运动。

**信号生成逻辑：**
```python
# 计算布林带
upper, lower = calculate_bollinger_bands(prices, period, std_multiplier)
current_price = prices[-1]

# 突破信号
if current_price > upper and position <= 0:
    return 'BUY'     # 突破上轨，买入信号
elif current_price < lower and position >= 0:
    return 'SELL'    # 突破下轨，卖出信号
```

**布林带计算公式：**
```python
def calculate_bollinger_bands(prices, period, std_multiplier):
    sma = np.mean(prices[-period:])           # 简单移动平均
    std = np.std(prices[-period:])            # 标准差
    
    upper = sma + (std_multiplier * std)      # 上轨
    lower = sma - (std_multiplier * std)      # 下轨
    
    return upper, lower
```

**参数配置：**
```yaml
strategy_type: "breakout"
bollinger_period: 20      # 布林带周期
bollinger_std: 2          # 标准差倍数
max_position: 1000        # 最大持仓
```

**适用场景：**
- 市场即将突破关键价位
- 波动率相对较高
- 适合捕捉大行情

**风险提示：**
- 假突破可能导致亏损
- 需要配合成交量确认
- 突破后可能快速回撤

#### 5.2.4 策略选择建议

**根据市场环境选择：**

1. **趋势市场** → 选择趋势跟踪策略
   - 特征：价格持续向一个方向运动
   - 优势：能捕捉大趋势
   - 注意：设置合理的止损

2. **震荡市场** → 选择均值回归策略
   - 特征：价格在一定区间内波动
   - 优势：能捕捉短期机会
   - 注意：避免在趋势中过早平仓

3. **突破市场** → 选择突破策略
   - 特征：价格突破关键阻力/支撑
   - 优势：能捕捉大行情
   - 注意：确认突破的有效性

**参数调优建议：**
- 根据历史数据回测确定最优参数
- 考虑交易成本和滑点
- 定期评估策略表现并调整
- 结合多个时间周期分析

## 6. 数据持久化

### 6.1 事件持久化

系统实现了完整的事件持久化机制：

```python
# 自动持久化所有事件到JSONL文件
event_engine = EventEngine(persist_path="events.jsonl")

# 支持事件回放
event_engine.replay("events.jsonl")
```

**持久化内容：**
- 所有行情数据（Tick、K线）
- 交易事件（订单、成交）
- 策略信号
- 系统日志

**文件格式：**
```json
{"type": "TICK_EVENT", "data": {"symbol": "AU9999", "last_price": 456.7}}
{"type": "SIGNAL_EVENT", "data": {"strategy_name": "spread_arbitrage", "data": {...}}}
```

### 6.2 配置管理

统一的YAML配置文件管理：

```yaml
# 事件引擎配置
event_persist_path: "events.jsonl"

# 数据源配置
data:
  shfe: {...}    # 上期所配置
  mt5: {...}     # MT5配置

# 策略配置
strategies:
  - name: "spread_arbitrage"
    type: "spread_arbitrage"
    config: {...}
```

## 7. 项目核心关注点

### 7.1. 数据源 (Data Sources)

*   **上海黄金市场**:
    *   **行情数据**: 需要接入上海黄金交易所或上海期货交易所的实时黄金合约行情 (Tick级优先)。
    *   **交易接口**: 需要通过支持程序化交易的期货公司账户接入交易，例如通过 `vnpy` 的 `CTP Gateway`。
*   **香港黄金市场**:
    *   **行情数据**: 需要接入香港相关交易所（如HKEX）的离岸人民币黄金合约（或其他适合的黄金标的）的实时行情。
    *   **交易接口**: 需要通过支持程序化交易的香港经纪商账户接入交易。调研重点包括 `vnpy` 是否有现成的 `Gateway` (如 Interactive Brokers - `IB Gateway`) 或是否需要定制开发。
*   **数据质量与同步**:
    *   确保两地行情数据的低延迟和时间戳的准确性。
    *   处理潜在的数据清洗和异常值问题。

### 7.2. 套利策略 (Arbitrage Strategy Logic)

*   **基差计算**:
    *   `基差 = 香港黄金价格(本地货币) * 汇率(如果需要转换为同一货币比较) - 上海黄金价格(本地货币)`
    *   简化版（若两地黄金价格已能直接比较或暂时忽略汇率波动）：`基差 = 香港黄金价格 - 上海黄金价格`
    *   注意合约单位、报价单位的统一。
*   **交易信号生成**:
    *   设定合理的开仓基差阈值（考虑交易成本、滑点、最小期望利润）。
    *   设定合理的平仓基差阈值（基差回归或反向扩大到一定程度）。
*   **仓位管理**:
    *   确定单次套利操作的合约手数。
    *   设置总套利组合的持仓上限。
*   **订单管理**:
    *   确保套利两腿订单的**近乎同时**发出。
    *   处理部分成交和未成交订单的逻辑。
    *   选择合适的订单类型（限价单、市价单、FOK、FAK等）以平衡成交率和滑点。

### 7.3. 执行速度 (Execution Speed)

*   **低延迟行情**: 选用速度快的行情接口，优化网络连接。
*   **快速计算**: 策略逻辑计算要高效，避免成为瓶颈。
*   **快速下单**: 交易指令的生成和发送要迅速，`Gateway` 的执行效率是关键。
*   **系统优化**: 减少 `vnpy` 内部以及自定义代码的潜在延迟。

### 7.4. 风险控制 (Risk Control)

*   **市场风险/价差风险**:
    *   基差可能不会按预期收敛，甚至反向扩大。
    *   设定止损条件（例如，最大基差亏损容忍度、持仓时间限制）。
*   **单边腿风险 (Legging Risk)**:
    *   套利一腿成交，另一腿未成交或以不利价格成交。
    *   需要有机制快速处理未平衡的敞口（如立即尝试补单或对已成交腿进行平仓）。
*   **滑点风险**:
    *   实际成交价格与下单时的价格存在不利偏差。
    *   通过合理的下单方式和流动性判断来控制。
*   **流动性风险**:
    *   某一市场或合约流动性不足，导致无法顺利建仓或平仓。
*   **交易成本**:
    *   精确计算双边手续费、印花税（如有）、资金成本等，确保套利空间能覆盖这些成本。
*   **资金管理**:
    *   设定整体策略的最大资金占用。
    *   最大可承受亏损。
*   **操作和系统风险**:
    *   程序BUG、网络中断、`Gateway` 故障等。
    *   需要有监控和应急预案。

## 8. 快速开始

### 8.1 环境安装

1. **创建虚拟环境**
```bash
python3 -m venv venv
source venv/bin/activate
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **TA-Lib安装**（如需要）
```bash
# 安装C库
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.6.4-src.tar.gz
tar -xzf ta-lib-0.6.4-src.tar.gz
cd ta-lib-0.6.4/
./configure --prefix=/usr
make
make install
ldconfig

# 安装Python包
pip install TA-Lib
```

### 8.2 配置系统

1. **编辑配置文件**
```bash
vim config.yaml
```

2. **配置数据源**
```yaml
data:
  shfe:
    gateway: "CTP"
    host: "your_host"
    port: 10101
    user: "your_username"
    password: "your_password"
    
  mt5:
    server: "MetaQuotes-Demo"
    login: 12345
    password: "your_password"
```

3. **配置策略**
```yaml
strategies:
  - name: "spread_arbitrage"
    type: "spread_arbitrage"
    config:
      spread_threshold: 0.5
      max_position: 1000
```

### 8.3 运行系统

```bash
python main.py
```

## 9. 开发计划

### 第一阶段：框架搭建 ✅
- [x] 事件驱动引擎实现
- [x] 策略基类设计
- [x] 数据管理器集成
- [x] 主控制器实现

### 第二阶段：策略实现 ✅
- [x] 基差套利策略
- [x] 上海市场量化策略
- [x] 事件持久化机制

### 第三阶段：数据源对接
- [ ] MT5数据源实现
- [ ] CTP数据源实现
- [ ] 数据质量验证

### 第四阶段：交易执行
- [ ] 订单管理系统
- [ ] 风控模块集成
- [ ] 实盘交易接口

### 第五阶段：系统优化
- [ ] 性能优化
- [ ] 监控告警
- [ ] 回测系统

## 10. 注意事项

1. **风险提示**：量化交易存在风险，请谨慎使用
2. **实盘测试**：建议先进行充分的模拟测试
3. **参数调优**：策略参数需要根据市场情况调整
4. **监控维护**：系统运行需要持续监控和维护

---

本文档将随着项目的进展持续更新。 