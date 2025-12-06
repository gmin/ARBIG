# MaRsiComboStrategy 设计文档

## 📋 文档信息
- **策略名称**: MA-RSI组合策略
- **策略类名**: `MaRsiComboStrategy`
- **文件名**: `MaRsiComboStrategy.py`
- **适用市场**: 上期所黄金期货（au主力合约）
- **策略类型**: 趋势跟踪 + 动量确认
- **版本**: v2.1.1
- **最后更新**: 2025-12-09

---

## 🎯 策略概述

### 核心思想
基于**双均线交叉**识别趋势转换点，结合**RSI指标**过滤极端市场状态，通过**智能持仓管理**实现盈利最大化和风险控制。

### 策略特点
1. ✅ **金叉死叉检测**：EMA5/EMA20交叉信号，带交叉强度和价格确认
2. ✅ **RSI过滤**：避免在超买超卖极端区域入场
3. ✅ **智能持仓管理**：盈利平仓 + 亏损持有 + 方向限仓
4. ✅ **加仓距离控制**：只在亏损达到阈值时加仓，避免价格太近难以解套
5. ✅ **实时持仓查询**：基于上期所真实持仓数据决策
6. ✅ **完整数据记录**：CSV日志记录所有K线和指标数据

### 适用场景
- ✅ 趋势性行情（金叉死叉信号有效）
- ✅ 日内交易和短线交易
- ⚠️ 震荡市场可能产生假信号
- ⚠️ 需要足够的流动性和波动性

---

## 📊 技术指标

### 1. 双均线系统
```python
EMA5  = EMA(Close, 5)   # 短期均线，捕捉快速趋势变化
EMA20 = EMA(Close, 20)  # 长期均线，确认主要趋势方向
```

**交叉信号**：
- **金叉（GOLDEN_CROSS）**: EMA5从下方上穿EMA20 → 看涨信号
- **死叉（DEATH_CROSS）**: EMA5从上方下穿EMA20 → 看跌信号

**交叉确认条件**：
1. **交叉幅度** ≥ 0.05（过滤微小交叉）
2. **价格确认**：
   - 金叉：收盘价 > EMA5
   - 死叉：收盘价 < EMA5

### 2. RSI指标
```python
RSI = RSI(Close, 14)  # 14周期相对强弱指标
```

**阈值设置**：
- **超买区域**: RSI > 70（谨慎做多）
- **超卖区域**: RSI < 30（谨慎做空）
- **合理区间**: 30 < RSI < 70（可以交易）

**作用**：
- 过滤极端市场状态
- 避免追高杀跌
- 提高信号质量

---

## 🔄 交易逻辑

### 信号生成流程

```
K线更新 → 计算指标 → 检测交叉 → RSI确认 → 生成信号 → 持仓管理 → 执行交易
```

### 详细逻辑

#### 1. 金叉买入信号
```python
条件：
  1. EMA5上穿EMA20（金叉）
  2. 交叉幅度 >= 0.05
  3. 收盘价 > EMA5
  4. 30 < RSI < 70

执行：
  1. 如果有空头持仓且盈利 → 平空
  2. 如果多头持仓 < 2手 → 加仓控制检查
     - 无多头持仓（0手）→ 开多1手
     - 有多头持仓（1手）→ 检查多头亏损
       - 亏损 >= 0.2% → 开多1手（加仓）
       - 亏损 < 0.2% → 不开仓
  3. 如果多头持仓 >= 2手 → 不开仓
```

#### 2. 死叉卖出信号
```python
条件：
  1. EMA5下穿EMA20（死叉）
  2. 交叉幅度 >= 0.05
  3. 收盘价 < EMA5
  4. 30 < RSI < 70

执行：
  1. 如果有多头持仓且盈利 → 平多
  2. 如果空头持仓 < 2手 → 加仓控制检查
     - 无空头持仓（0手）→ 开空1手
     - 有空头持仓（1手）→ 检查空头亏损
       - 亏损 >= 0.2% → 开空1手（加仓）
       - 亏损 < 0.2% → 不开仓
  3. 如果空头持仓 >= 2手 → 不开仓
```

---

## 💼 持仓管理策略

### 核心原则
**"盈利平仓 + 亏损持有 + 加仓控制 + 方向限仓"**

### 详细规则

#### 1. 盈利平仓
- 金叉信号时：如果有空头持仓且盈利 → 平空
- 死叉信号时：如果有多头持仓且盈利 → 平多
- **目的**：锁定利润，避免利润回吐

#### 2. 亏损持有
- 金叉信号时：如果有空头持仓但亏损 → 保留空头
- 死叉信号时：如果有多头持仓但亏损 → 保留多头
- **目的**：等待反转机会，避免频繁止损

#### 3. 加仓距离控制（新增）⭐
- **核心逻辑**：只在亏损达到阈值时才允许加仓
- **金叉信号加仓规则**：
  - 无多头持仓（0手）→ 直接开多1手
  - 有多头持仓（1手）→ 检查多头亏损
    - 亏损 >= 0.2% → 允许加多1手
    - 亏损 < 0.2% → 不加仓（忽略信号）
- **死叉信号加仓规则**：
  - 无空头持仓（0手）→ 直接开空1手
  - 有空头持仓（1手）→ 检查空头亏损
    - 亏损 >= 0.2% → 允许加空1手
    - 亏损 < 0.2% → 不加仓（忽略信号）
- **目的**：
  - ✅ 避免价格太近难以解套
  - ✅ 越跌越买，降低平均成本
  - ✅ 保持足够的加仓空间
- **参数**：`add_loss_pct = 0.002`（0.2%，约1.93元@963）

#### 4. 方向限仓
- 多头方向：最多持有2手
- 空头方向：最多持有2手
- **目的**：控制单向风险敞口

#### 5. 双向持仓
- 允许同时持有多头和空头
- 例如：多头1手（亏损） + 空头1手（新开）
- **目的**：对冲风险，灵活应对市场变化

---

## ⚙️ 策略参数

### 技术指标参数

| 参数名 | 默认值 | 类型 | 说明 |
|--------|--------|------|------|
| `ma_short` | 5 | int | 短期均线周期（EMA5） |
| `ma_long` | 20 | int | 长期均线周期（EMA20） |
| `rsi_period` | 14 | int | RSI计算周期 |
| `rsi_overbought` | 70 | int | RSI超买阈值 |
| `rsi_oversold` | 30 | int | RSI超卖阈值 |

### 风险控制参数

| 参数名 | 默认值 | 类型 | 说明 |
|--------|--------|------|------|
| `stop_loss_pct` | 0.006 | float | 止损百分比（0.6%） |
| `take_profit_pct` | 0.008 | float | 止盈百分比（0.8%） |
| `add_loss_pct` | 0.002 | float | 加仓亏损阈值（0.2%）⭐ |
| `max_position` | 5 | int | 最大总持仓手数 |

### 交易执行参数

| 参数名 | 默认值 | 类型 | 说明 |
|--------|--------|------|------|
| `trade_volume` | 1 | int | 每次交易手数 |
| `min_signal_interval` | 60 | int | 最小信号间隔（秒） |

---

## 🔍 核心算法详解

### 1. 金叉死叉检测算法

```python
def _detect_ma_cross(current_price):
    """
    检测EMA5和EMA20的交叉信号

    输入：
        current_price: 当前收盘价

    输出：
        "GOLDEN_CROSS" - 金叉
        "DEATH_CROSS"  - 死叉
        "NONE"         - 无交叉
    """

    # 需要至少2个历史点
    if len(ma5_history) < 2 or len(ma20_history) < 2:
        return "NONE"

    # 获取前1时刻和当前时刻的均线值
    ma5_prev, ma5_curr = ma5_history[-2:]
    ma20_prev, ma20_curr = ma20_history[-2:]

    # 金叉检测
    if ma5_prev <= ma20_prev and ma5_curr > ma20_curr:
        # 计算交叉幅度
        cross_strength = abs((ma5_curr - ma20_curr) - (ma5_prev - ma20_prev))

        # 价格确认
        price_confirmation = current_price > ma5_curr

        # 交叉幅度和价格都满足
        if cross_strength >= 0.05 and price_confirmation:
            return "GOLDEN_CROSS"

    # 死叉检测
    if ma5_prev >= ma20_prev and ma5_curr < ma20_curr:
        # 计算交叉幅度
        cross_strength = abs((ma5_curr - ma20_curr) - (ma5_prev - ma20_prev))

        # 价格确认
        price_confirmation = current_price < ma5_curr

        # 交叉幅度和价格都满足
        if cross_strength >= 0.05 and price_confirmation:
            return "DEATH_CROSS"

    return "NONE"
```

**关键点**：
1. **确认检测**：使用前1时刻和当前时刻的数据，避免误判
2. **交叉幅度**：≥0.05，过滤微小交叉和噪音
3. **价格确认**：收盘价必须在交叉方向上，增强信号可靠性

### 2. 交易决策算法

```python
def _analyze_trading_opportunity(cross_signal, rsi):
    """
    基于交叉信号和RSI生成交易决策

    输入：
        cross_signal: 交叉信号（GOLDEN_CROSS/DEATH_CROSS/NONE）
        rsi: RSI值

    输出：
        {
            "action": "BUY/SELL/NONE",
            "reason": "决策原因",
            "strength": 信号强度（0-1）
        }
    """

    # 金叉买入
    if cross_signal == "GOLDEN_CROSS":
        if 30 < rsi < 70:  # RSI在合理区间
            return {
                "action": "BUY",
                "reason": f"金叉信号+RSI确认({rsi:.1f})",
                "strength": 1.0
            }
        else:
            return {
                "action": "NONE",
                "reason": f"金叉信号但RSI不合适({rsi:.1f})",
                "strength": 0
            }

    # 死叉卖出
    elif cross_signal == "DEATH_CROSS":
        if 30 < rsi < 70:  # RSI在合理区间
            return {
                "action": "SELL",
                "reason": f"死叉信号+RSI确认({rsi:.1f})",
                "strength": 1.0
            }
        else:
            return {
                "action": "NONE",
                "reason": f"死叉信号但RSI不合适({rsi:.1f})",
                "strength": 0
            }

    # 无交叉信号
    else:
        return {
            "action": "NONE",
            "reason": f"无金叉死叉信号，RSI({rsi:.1f})",
            "strength": 0.0
        }
```

### 3. 持仓管理算法

```python
def _process_trading_signal(action, current_price):
    """
    处理交易信号并执行持仓管理

    核心逻辑：盈利平仓 + 亏损持有 + 加仓控制 + 方向限仓
    """

    # 查询真实持仓
    position_info = query_real_position()
    long_position = position_info["long_position"]
    short_position = position_info["short_position"]
    long_price = position_info["long_price"]
    short_price = position_info["short_price"]

    # 金叉信号处理
    if action == "BUY":
        # 1. 检查空头持仓 - 盈利则平仓
        if short_position > 0:
            short_pnl = (short_price - current_price) * short_position
            if short_pnl > 0:  # 空头盈利
                cover(short_position)  # 平空

        # 2. 检查多头持仓限制（最多2手）
        if long_position >= 2:
            # 已达上限，不开仓
            pass
        else:
            # 🎯 加仓控制：只在没有持仓或亏损达到阈值时开仓
            should_open = False

            if long_position == 0:
                # 没有多头持仓，直接开仓
                should_open = True
            else:
                # 已有多头持仓，检查是否亏损达到阈值
                long_pnl_pct = (current_price - long_price) / long_price
                if long_pnl_pct <= -add_loss_pct:  # 亏损 >= 0.3%
                    should_open = True  # 允许加仓

            if should_open:
                buy(1)  # 开多1手

    # 死叉信号处理
    elif action == "SELL":
        # 1. 检查多头持仓 - 盈利则平仓
        if long_position > 0:
            long_pnl = (current_price - long_price) * long_position
            if long_pnl > 0:  # 多头盈利
                sell(long_position)  # 平多

        # 2. 检查空头持仓限制（最多2手）
        if short_position >= 2:
            # 已达上限，不开仓
            pass
        else:
            # 🎯 加仓控制：只在没有持仓或亏损达到阈值时开仓
            should_open = False

            if short_position == 0:
                # 没有空头持仓，直接开仓
                should_open = True
            else:
                # 已有空头持仓，检查是否亏损达到阈值
                short_pnl_pct = (short_price - current_price) / short_price
                if short_pnl_pct <= -add_loss_pct:  # 亏损 >= 0.3%
                    should_open = True  # 允许加仓

            if should_open:
                short(1)  # 开空1手
```

**关键改进**：
1. ✅ **加仓距离控制**：避免价格太近难以解套
2. ✅ **首次开仓不受限制**：无持仓时直接开仓
3. ✅ **亏损加仓**：只在亏损 >= 0.3% 时才允许加仓
4. ✅ **详细日志**：记录每个决策过程

---

## 📈 数据记录

### CSV日志文件

**文件路径**: `logs/indicators_{strategy_name}_{symbol}_{date}.csv`

**记录内容**：
```csv
DateTime,Open,High,Low,Close,Volume,EMA5,EMA20,RSI,EMA5_EMA20_Diff,Cross_Signal
2025-12-05 21:44:00,962.84,963.08,962.74,963.02,33550,963.08,963.17,47.66,-0.10,DEATH_CROSS
2025-12-05 21:53:00,963.38,963.58,963.38,963.50,37984,963.21,963.07,57.23,0.13,GOLDEN_CROSS
```

**字段说明**：
- `DateTime`: K线时间
- `Open/High/Low/Close`: OHLC价格
- `Volume`: 成交量
- `EMA5/EMA20`: 双均线值
- `RSI`: RSI指标值
- `EMA5_EMA20_Diff`: 均线差值
- `Cross_Signal`: 交叉信号（GOLDEN_CROSS/DEATH_CROSS/NONE）

**用途**：
- 策略回测分析
- 信号质量评估
- 参数优化
- 问题诊断

---

## 🛡️ 风险控制

### 1. 持仓限制
- **单向最大持仓**: 2手
- **总持仓限制**: 5手
- **目的**: 控制风险敞口，避免过度集中

### 2. 信号间隔控制
- **最小信号间隔**: 60秒
- **目的**: 避免频繁交易，减少滑点和手续费

### 3. 加仓距离控制（新增）⭐
- **加仓阈值**: 0.2%（`add_loss_pct = 0.002`，约1.93元@963）
- **控制逻辑**: 只在亏损达到阈值时才允许加仓
- **目的**:
  - ✅ 避免价格太近难以解套
  - ✅ 越跌越买，降低平均成本
  - ✅ 保持足够的加仓空间
- **示例场景**:
  ```
  场景1：首次开仓
  - 金叉信号，价格963.00，无多头持仓
  - 结果：开多1手 ✅

  场景2：价格接近时的金叉
  - 已有多头1手@963.00，金叉信号，价格963.20
  - 盈亏：+0.02%（未达到亏损阈值）
  - 结果：不加仓 ⚠️

  场景3：价格下跌后的金叉
  - 已有多头1手@963.00，金叉信号，价格961.07
  - 盈亏：-0.20%（达到亏损阈值）
  - 结果：加仓1手 ✅
  ```

### 4. 止损止盈（预留接口）
- **止损**: 0.6%（当前未启用）
- **止盈**: 0.8%（当前未启用）
- **说明**: 当前策略依赖信号反转平仓，止损止盈作为备用机制

### 5. 实时持仓查询
- **查询频率**: 每次信号前查询
- **缓存机制**: 30秒缓存，减少服务压力
- **目的**: 基于真实持仓数据决策，避免虚拟持仓误差

---

## 📊 性能优化

### 1. 指标计算优化
```python
# 每个K线只计算一次指标，后续复用
current_ma5 = am.ema(5)
current_ma20 = am.ema(20)
current_rsi = am.rsi(14)
```

### 2. 持仓缓存机制
```python
# 30秒内使用缓存，避免频繁查询
if time.time() - last_position_update < 30:
    return cached_position
else:
    return query_real_position()
```

### 3. 历史数据管理
```python
# 只保留最近10个均线值
ma5_history = ma5_history[-10:]
ma20_history = ma20_history[-10:]
```

---

## 🔧 使用示例

### 策略配置

```python
# strategy_manager.py
strategy_config = {
    "name": "GoldMaRsi",
    "type": "MaRsiComboStrategy",
    "symbol": "au2602",
    "params": {
        "ma_short": 5,
        "ma_long": 20,
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "trade_volume": 1,
        "max_position": 5,
        "min_signal_interval": 60
    }
}
```

### 策略启动

```python
from services.strategy_service.strategies.MaRsiComboStrategy import MaRsiComboStrategy

# 创建策略实例
strategy = MaRsiComboStrategy(
    strategy_name="GoldMaRsi",
    symbol="au2602",
    setting={
        "ma_short": 5,
        "ma_long": 20,
        "rsi_period": 14
    }
)

# 启动策略
strategy.on_start()
```

---

## 📉 回测分析示例

### 12月5日数据分析

**测试数据**: 2025-12-05 21:00 - 2025-12-06 02:30

**信号统计**:
- 总信号: 8个（4金叉 + 4死叉）
- 总盈亏: +2.12元
- 胜率: 62.5%

**金叉信号表现**:
- 数量: 4个
- 盈亏: +1.76元
- 胜率: 75%
- 平均RSI: 56.4

**死叉信号表现**:
- 数量: 4个
- 盈亏: +0.36元
- 胜率: 50%
- 平均RSI: 46.1

**关键发现**:
1. ✅ 金叉信号在RSI > 50时表现优秀（胜率75%）
2. ⚠️ 死叉信号表现一般（胜率50%）
3. ✅ RSI过滤和价格位置过滤效果一致
4. ✅ 当前交叉幅度阈值（0.05）+ RSI确认（30-70）已经很有效

---

## 🔄 策略演进历史

### v1.0 (初始版本)
- 基础双均线交叉策略
- 简单的RSI过滤
- 固定止损止盈

### v2.0 (当前版本)
- ✅ 改进的金叉死叉检测（交叉幅度 + 价格确认）
- ✅ 智能持仓管理（盈利平仓 + 亏损持有）
- ✅ 实时持仓查询（基于上期所真实数据）
- ✅ 完整CSV日志记录
- ✅ 方向限仓（每个方向最多2手）
- ✅ 双向持仓支持

### 未来优化方向
- 🔮 动态参数调整（根据市场波动率）
- 🔮 ATR止损（基于波动率的动态止损）
- 🔮 多时间周期确认
- 🔮 成交量过滤
- 🔮 时间段过滤（避开低流动性时段）

---

## ⚠️ 注意事项

### 1. 市场环境依赖
- ✅ **趋势市场**: 策略表现优秀
- ⚠️ **震荡市场**: 可能产生假信号
- ❌ **极端波动**: 交叉幅度过滤可能失效

### 2. 参数敏感性
- **交叉幅度阈值（0.05）**: 太小会增加假信号，太大会错过机会
- **RSI区间（30-70）**: 太宽会降低过滤效果，太窄会减少交易机会
- **持仓限制（2手）**: 需要根据资金规模调整

### 3. 持仓管理风险
- **亏损持有**: 可能导致亏损扩大，需要配合止损
- **双向持仓**: 增加资金占用，需要充足保证金
- **盈利平仓**: 可能错过更大趋势，需要权衡

### 4. 数据依赖
- **实时持仓查询**: 依赖上期所接口稳定性
- **K线数据**: 需要至少20根K线才能计算EMA20
- **CSV日志**: 需要定期清理，避免文件过大

---

## 🧪 测试建议

### 1. 回测测试
```python
# 使用历史数据回测
python analysis/test_filter_methods.py
```

### 2. 参数优化
- 测试不同的均线周期组合（EMA5/EMA20 vs EMA5/EMA30）
- 测试不同的交叉幅度阈值（0.03, 0.05, 0.08）
- 测试不同的RSI区间（25-75, 30-70, 35-65）
- 测试不同的加仓阈值（0.2%, 0.3%, 0.5%）⭐

### 3. 信号质量分析
```python
# 分析信号盈亏分布
python analysis/detailed_signal_analysis.py
```

### 4. 实盘测试
- 先用小仓位测试（1手）
- 观察至少5-10个交易日
- 记录所有信号和执行情况
- 根据实盘表现调整参数

---

## 📚 相关文档

- **策略代码**: `services/strategy_service/strategies/MaRsiComboStrategy.py`
- **策略模板**: `STRATEGY_TEMPLATE` (代码第907行)
- **分析脚本**: `analysis/test_filter_methods.py`
- **详细分析**: `analysis/detailed_signal_analysis.py`
- **对比分析**: `analysis/compare_ma_combinations.py`
- **加仓逻辑测试**: `analysis/test_add_position_logic.py` ⭐

---

## 📞 联系方式

如有问题或建议，请联系策略开发团队。

---

## 📝 更新日志

### 2025-12-09 (v2.1.1) 🔧
- ✅ **调整加仓阈值**：0.3% → 0.2%（约1.93元@963）
  - 原阈值价差太远，调整为更合理的距离
  - 增加加仓机会，同时保持足够的解套空间

### 2025-12-06 (v2.1) ⭐
- ✅ **新增加仓距离控制机制**
  - 添加 `add_loss_pct` 参数（初始0.3%）
  - 只在亏损达到阈值时才允许加仓
  - 避免价格太近难以解套
  - 实现越跌越买的成本摊薄策略
- ✅ 更新设计文档，添加加仓控制详细说明
- ✅ 创建加仓逻辑测试脚本（7个场景，100%通过）
- ✅ 更新持仓管理算法伪代码

### 2025-12-06 (v2.0)
- ✅ 创建策略设计文档
- ✅ 完成12月5日数据分析
- ✅ 对比EMA5/EMA20 vs EMA5/EMA30
- ✅ 确认当前参数配置有效

### 2025-12-05 (v1.0)
- ✅ 实现智能持仓管理
- ✅ 添加CSV日志记录
- ✅ 优化金叉死叉检测算法

---

**文档结束**

