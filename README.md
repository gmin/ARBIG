# ARBIG - 香港离岸人民币黄金与上海黄金交易所黄金跨市场基差套利系统

## 项目简介

ARBIG是一个基于vnpy框架的量化交易系统，专门用于香港离岸人民币黄金与上海黄金交易所黄金合约的跨市场基差套利。系统支持多种量化策略，包括基差套利、趋势跟踪、均值回归等。

## 系统特点

- **单策略运行模式**：一次只运行一个策略，避免策略间干扰
- **多策略支持**：支持基差套利、趋势跟踪、均值回归等多种策略
- **实时数据处理**：支持实时Tick数据和K线数据处理
- **事件驱动架构**：基于事件引擎的松耦合架构设计
- **配置化管理**：通过YAML配置文件灵活配置策略参数

## 安装依赖

### 系统依赖

```bash
# 安装Python虚拟环境支持
sudo apt-get install python3.10-venv

# 安装TA-Lib依赖库
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr/local
make
sudo make install
sudo ldconfig
```

### Python依赖

```bash
# 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate

# 安装依赖包
pip install -r requirements.txt
```

## 配置说明

### 配置文件结构

系统使用 `config.yaml` 作为主配置文件：

```yaml
# 事件引擎配置
event_persist_path: "events.jsonl"

# 数据源配置
data:
  shfe:
    gateway: "CTP"
    host: "180.168.146.187"
    port: 10101
    user: "your_username"
    password: "your_password"
    broker_id: "9999"
    
  mt5:
    server: "MetaQuotes-Demo"
    login: 12345
    password: "your_password"
    symbol: "XAUUSD"

# 策略配置
strategies:
  - name: "spread_arbitrage"
    type: "spread_arbitrage"
    config:
      spread_threshold: 0.5
      max_position: 1000
      shfe_symbol: "AU9999"
      mt5_symbol: "XAUUSD"
      
  - name: "shfe_quant"
    type: "shfe_quant"
    config:
      strategy_type: "trend"
      symbol: "AU9999"
      max_position: 1000
      ma_short: 5
      ma_long: 20
      rsi_period: 14
      rsi_overbought: 70
      rsi_oversold: 30
```

## 使用方法

### 1. 列出可用策略

```bash
python main.py --list
```

### 2. 指定策略运行

```bash
# 运行基差套利策略
python main.py --strategy spread_arbitrage

# 运行上海市场量化策略
python main.py --strategy shfe_quant
```

### 3. 交互式选择策略

```bash
python main.py
```

系统会显示策略选择菜单，您可以选择要运行的策略。

### 4. 使用自定义配置文件

```bash
python main.py --config my_config.yaml --strategy spread_arbitrage
```

## 策略说明

### 基差套利策略 (spread_arbitrage)

监控香港和上海黄金价格，在基差达到阈值时进行套利交易。

**参数说明：**
- `spread_threshold`: 基差阈值，触发套利的价差
- `max_position`: 最大持仓量
- `shfe_symbol`: 上期所合约代码
- `mt5_symbol`: MT5合约代码

### 上海市场量化策略 (shfe_quant)

实现上期所黄金期货的量化交易策略，支持多种策略类型。

**策略类型：**
- `trend`: 趋势跟踪策略
- `mean_reversion`: 均值回归策略
- `breakout`: 突破策略

**参数说明：**
- `strategy_type`: 策略类型
- `symbol`: 交易合约
- `max_position`: 最大持仓
- `ma_short/ma_long`: 短期/长期均线周期
- `rsi_period`: RSI周期
- `rsi_overbought/rsi_oversold`: RSI超买/超卖阈值

## 策略详细说明

### 1. 基差套利策略（spread_arbitrage）

#### 策略原理
基差套利策略利用同一标的（黄金）在不同市场（如香港离岸人民币黄金与上海黄金交易所黄金）之间的价格差异。当基差（两地价格之差）达到一定阈值时，系统自动进行买入低价市场、卖出高价市场的操作，期望基差回归时获利。

#### 核心交易逻辑
**基差套利的核心原则：在低价市场买入，高价市场卖出**

```python
# 基差计算：spread = SHFE价格 - MT5价格
spread = shfe_price - mt5_price

# 开仓条件：基差超过开仓阈值
if abs(spread) > entry_threshold:
    if spread > 0:
        # 买入MT5(低价)，卖出SHFE(高价)
        signal = 'BUY_MT5_SELL_SHFE'
    else:
        # 买入SHFE(低价)，卖出MT5(高价)
        signal = 'BUY_SHFE_SELL_MT5'

# 平仓条件：基差回归到平仓阈值
if abs(spread) <= exit_threshold:
    signal = 'CLOSE_POSITION'
```

#### 阈值设置策略
**采用简单有效的固定阈值策略，避免过度复杂化**

- **开仓阈值**：0.8元/克 - 确保覆盖交易成本并获得合理利润
- **平仓阈值**：0.2元/克 - 及时锁定利润，避免基差反转
- **策略优势**：逻辑清晰，易于理解和维护，减少过拟合风险

#### 适用场景
- 两地黄金市场流动性较好，价差波动明显
- 具备同时接入两地行情与交易通道的条件
- 适合套利型、低风险偏好的量化交易者

#### 信号生成机制
- 实时监控两地黄金价格（如shfe_price、mt5_price）
- 计算基差：`spread = shfe_price - mt5_price`
- 当|spread|大于`spread_threshold`时，产生套利信号：
  - spread > threshold：买入MT5黄金，卖出SHFE黄金
  - spread < -threshold：买入SHFE黄金，卖出MT5黄金
- 信号只在基差首次突破阈值时触发，避免频繁交易

#### 参数说明
| 参数名           | 说明                 | 典型取值 | 调优建议           |
|------------------|----------------------|----------|--------------------|
| spread_threshold | 触发套利的基差阈值   | 0.5      | 结合手续费、滑点设定|
| max_position     | 最大持仓量           | 1000     | 视资金规模调整     |
| shfe_symbol      | 上期所合约代码       | AU9999   | 需与行情一致       |
| mt5_symbol       | MT5合约代码          | XAUUSD   | 需与行情一致       |

#### 风险提示
- **基差风险**：基差可能不会回归，甚至进一步扩大
- **腿差风险**：一腿成交，另一腿未成交或滑点大
- **流动性风险**：某一市场流动性不足，导致无法及时平仓
- **汇率风险**：如涉及不同币种，需关注汇率波动
- **技术风险**：行情延迟、下单失败、系统故障等

#### 示例流程（伪代码）
```python
while True:
    shfe_price = get_shfe_price()
    mt5_price = get_mt5_price()
    spread = shfe_price - mt5_price
    
    if spread > spread_threshold:
        # 买入MT5(低价)，卖出SHFE(高价)
        send_signal('BUY_MT5_SELL_SHFE')
    elif spread < -spread_threshold:
        # 买入SHFE(低价)，卖出MT5(高价)
        send_signal('BUY_SHFE_SELL_MT5')
    
    sleep(1)
```

---

### 2. 上海量化策略（shfe_quant）

#### 策略架构
上海量化策略采用**分层设计**，包含三个子策略：
- **突破策略（breakout）**：**方向判断器**，识别市场方向（做多/做空）
- **趋势跟踪（trend）**：基于均线交叉的趋势策略
- **均值回归（mean_reversion）**：基于RSI的震荡策略

#### 策略原理

##### 突破策略（方向判断器）
- **核心功能**：判断市场方向，指导其他策略的做多做空决策
- **判断逻辑**：价格突破布林带上轨→做多方向，跌破下轨→做空方向
- **置信度计算**：基于突破强度和趋势一致性
- **信号输出**：方向信号（LONG/SHORT/NEUTRAL）+ 置信度

##### 趋势跟踪策略
- **核心功能**：基于均线交叉的趋势跟踪
- **信号逻辑**：短期均线上穿长期均线→买入，下穿→卖出
- **方向约束**：根据突破策略的方向判断调整操作
- **仓位管理**：根据方向置信度调整仓位大小

##### 均值回归策略
- **核心功能**：基于RSI的震荡交易
- **信号逻辑**：RSI超卖→买入，超买→卖出
- **方向约束**：根据突破策略的方向判断调整操作
- **仓位管理**：根据方向置信度调整仓位大小

#### 适用场景
- **趋势市场**：突破策略识别趋势方向，趋势策略顺势操作
- **震荡市场**：突破策略识别区间突破，均值回归策略在区间内操作
- **转折市场**：突破策略提前识别方向变化，其他策略及时调整

#### 信号生成机制

##### 突破策略（方向判断）
```python
# 计算布林带
upper, lower = calculate_bollinger_bands(price_history)
current_price = price_history[-1]
strength = calculate_breakout_strength(current_price, upper, lower)

# 方向判断
if current_price > upper and strength > 0.5:
    direction = 'LONG'
    confidence = calculate_confidence(direction, strength)
    send_direction_signal(direction, confidence)
elif current_price < lower and strength > 0.5:
    direction = 'SHORT'
    confidence = calculate_confidence(direction, strength)
    send_direction_signal(direction, confidence)
```

##### 趋势策略（结合方向判断）
```python
# 计算均线
ma_short = mean(price_history[-ma_short_period:])
ma_long = mean(price_history[-ma_long_period:])

# 原始信号
if ma_short > ma_long and position <= 0:
    original_signal = 'BUY'
elif ma_short < ma_long and position >= 0:
    original_signal = 'SELL'

# 根据方向调整信号
if direction == 'LONG' and confidence > 0.5:
    if original_signal == 'BUY':
        final_signal = 'BUY'
    elif original_signal == 'SELL':
        final_signal = 'CLOSE_LONG'  # 平多而不是做空
elif direction == 'SHORT' and confidence > 0.5:
    if original_signal == 'BUY':
        final_signal = 'CLOSE_SHORT'  # 平空而不是做多
    elif original_signal == 'SELL':
        final_signal = 'SELL'
```

##### 均值回归策略（结合方向判断）
```python
# 计算RSI
rsi = calculate_rsi(price_history, rsi_period)

# 原始信号
if rsi < rsi_oversold and position <= 0:
    original_signal = 'BUY'
elif rsi > rsi_overbought and position >= 0:
    original_signal = 'SELL'

# 根据方向调整信号（类似趋势策略）
```

#### 参数说明
| 参数名           | 说明                 | 典型取值 | 调优建议           |
|------------------|----------------------|----------|--------------------|
| strategy_type    | 策略类型             | trend/mean_reversion/breakout | 根据市场选择 |
| symbol           | 交易合约代码         | AU9999   | 与行情一致         |
| max_position     | 最大持仓量           | 1000     | 视资金规模调整     |
| ma_short         | 短期均线周期         | 5        | 趋势策略用         |
| ma_long          | 长期均线周期         | 20       | 趋势策略用         |
| rsi_period       | RSI周期              | 14       | 均值回归用         |
| rsi_overbought   | RSI超买阈值          | 70       | 均值回归用         |
| rsi_oversold     | RSI超卖阈值          | 30       | 均值回归用         |

#### 风险提示
- **突破策略**：假突破可能导致方向判断错误，影响其他策略
- **趋势策略**：震荡市易频繁止损，趋势反转时可能滞后
- **均值回归**：强趋势市易逆势亏损，阈值设置不当易频繁交易
- **方向依赖**：其他策略过度依赖突破策略的方向判断
- **参数过拟合**：历史最优参数未必适合未来行情
- **技术风险**：行情延迟、数据异常、系统故障等

#### 策略协同示例

##### 完整流程示例
```python
# 1. 突破策略判断方向
def breakout_direction():
    upper, lower = calc_bollinger_bands(price_history)
    price = price_history[-1]
    strength = calc_breakout_strength(price, upper, lower)
    
    if price > upper and strength > 0.5:
        return 'LONG', calculate_confidence('LONG', strength)
    elif price < lower and strength > 0.5:
        return 'SHORT', calculate_confidence('SHORT', strength)
    return 'NEUTRAL', 0.0

# 2. 趋势策略根据方向调整
def trend_strategy_with_direction():
    direction, confidence = breakout_direction()
    
    # 计算均线信号
    ma_signal = calculate_ma_signal()
    
    # 根据方向调整
    if direction == 'LONG' and confidence > 0.5:
        if ma_signal == 'BUY':
            return 'BUY', calculate_position(confidence)
        elif ma_signal == 'SELL':
            return 'CLOSE_LONG', -current_position
    elif direction == 'SHORT' and confidence > 0.5:
        if ma_signal == 'BUY':
            return 'CLOSE_SHORT', -current_position
        elif ma_signal == 'SELL':
            return 'SELL', calculate_position(confidence)
    
    return None, 0

# 3. 均值回归策略类似处理
```

##### 仓位管理示例
```python
def calculate_position(confidence):
    base_position = 100
    
    if confidence > 0.7:
        return base_position  # 高置信度，正常仓位
    elif confidence > 0.5:
        return int(base_position * 0.8)  # 中等置信度，减少仓位
    else:
        return int(base_position * 0.5)  # 低置信度，大幅减少仓位
```

---

### 3. 策略组合与方向判断

#### 突破策略方向化
突破策略已重新设计为**方向判断器**，主要作用：

1. **市场方向识别**：
   - 检测价格突破布林带上下轨
   - 判断市场方向（做多/做空/中性）
   - 提供方向置信度

2. **主策略指导**：
   - 为趋势策略提供方向指导
   - 为均值回归策略提供方向指导
   - 避免逆势操作

3. **仓位管理**：
   - 根据方向置信度调整仓位
   - 高置信度时正常仓位
   - 低置信度时减少仓位

#### 策略协同示例
```python
# 突破策略判断方向
if breakout_direction == 'LONG' and confidence > 0.7:
    # 高置信度做多方向
    if trend_signal == 'BUY':
        execute_buy(full_position)
    elif trend_signal == 'SELL':
        execute_close_long()  # 平多而不是做空
elif breakout_direction == 'SHORT' and confidence > 0.7:
    # 高置信度做空方向
    if trend_signal == 'BUY':
        execute_close_short()  # 平空而不是做多
    elif trend_signal == 'SELL':
        execute_sell(full_position)
else:
    # 中性方向，减少仓位
    execute_with_reduced_position()
```

## 系统架构

```
ARBIG/
├── main.py              # 主控制器
├── config.yaml          # 配置文件
├── core/                # 核心模块
│   ├── event_engine.py  # 事件引擎
│   ├── data.py          # 数据管理
│   ├── strategy_base.py # 策略基类
│   └── constants.py     # 常量定义
├── strategies/          # 策略模块
│   ├── spread_arbitrage.py  # 基差套利策略
│   └── shfe_quant.py        # 上海市场量化策略
├── config/              # 配置模块
├── utils/               # 工具模块
└── tests/               # 测试模块
```

## 事件系统

系统采用事件驱动架构，主要事件类型包括：

- `TICK_EVENT`: Tick数据事件
- `BAR_EVENT`: K线数据事件
- `SIGNAL_EVENT`: 策略信号事件
- `ORDER_EVENT`: 订单事件
- `TRADE_EVENT`: 成交事件
- `ACCOUNT_EVENT`: 账户事件

## 单策略运行模式

为了避免多个策略同时运行造成的干扰，系统采用单策略运行模式：

1. **策略隔离**：一次只运行一个策略
2. **事件分发**：主控制器统一管理事件分发
3. **资源独占**：当前策略独占数据源和计算资源
4. **状态管理**：清晰的策略启动/停止状态管理

## 开发指南

### 添加新策略

1. 继承 `StrategyBase` 类
2. 实现所有抽象方法
3. 在 `main.py` 中添加策略创建逻辑
4. 在配置文件中添加策略配置

### 示例

```python
from core.strategy_base import StrategyBase

class MyStrategy(StrategyBase):
    def on_start(self):
        print("策略启动")
        
    def on_stop(self):
        print("策略停止")
        
    def on_tick(self, event):
        # 处理Tick数据
        pass
        
    # 实现其他抽象方法...
```

## 注意事项

1. **数据源配置**：请根据实际情况配置数据源连接参数
2. **风控设置**：建议在生产环境中启用风控模块
3. **日志监控**：定期检查系统日志，确保策略正常运行
4. **策略测试**：新策略建议先在模拟环境中充分测试

## 许可证

本项目采用 MIT 许可证。 