# MultiModeAdaptiveStrategy 设计文档

## 1. 策略概述

**多模式自适应策略** 是一个综合量化交易策略，能够根据配置切换不同的交易模式（趋势跟踪、均值回归、突破交易）。

### 1.1 当前定位
- 📌 **当前状态**：独立简化版，内置三种模式的基本逻辑
- 📌 **未来规划**：整合为调度器，委托给 MaRsiComboStrategy / BreakoutStrategy / MeanReversionStrategy 执行

### 1.2 适用市场
- ✅ 上期所黄金期货（au主力合约）
- ✅ 全天候交易（通过模式切换适应不同行情）
- ✅ 中长线持仓（持仓周期：小时级到日级）
- ⚠️ 当前简化版逻辑较为基础，不建议直接用于实盘

### 1.3 风险特征
- 📊 **风险等级**：中等
- 💰 **资金要求**：适中
- ⏱️ **持仓周期**：随模式变化
- 📈 **预期收益**：取决于所选模式

---

## 2. 三种交易模式

### 2.1 趋势跟踪模式 (TREND)

| 特性 | 说明 |
|------|------|
| **信号来源** | MA5/MA20 金叉死叉 |
| **买入条件** | MA5 > MA20 且无多仓 |
| **卖出条件** | MA5 < MA20 且无空仓 |
| **适用场景** | 单边趋势行情 |
| **对应独立策略** | MaRsiComboStrategy（更完善） |

### 2.2 均值回归模式 (MEAN_REVERSION)

| 特性 | 说明 |
|------|------|
| **信号来源** | RSI 超买超卖 |
| **买入条件** | RSI < 30 且无多仓 |
| **卖出条件** | RSI > 70 且无空仓 |
| **适用场景** | 震荡整理行情 |
| **对应独立策略** | MeanReversionStrategy（更完善） |

### 2.3 突破模式 (BREAKOUT)

| 特性 | 说明 |
|------|------|
| **信号来源** | 价格突破布林带上下轨 |
| **买入条件** | 收盘价 > 上轨 且突破强度 > 0.5% |
| **卖出条件** | 收盘价 < 下轨 且突破强度 > 0.5% |
| **适用场景** | 趋势启动阶段 |
| **对应独立策略** | BreakoutStrategy（更完善） |

### 2.4 简化版 vs 独立版对比

| 特性 | MultiMode（简化版） | 独立策略 |
|------|-------------------|---------|
| 信号确认 | ❌ 无 | ✅ N根K线确认 |
| RSI过滤 | ❌ 无 | ✅ 有 |
| 带宽过滤 | ❌ 无 | ✅ 有（均值回归） |
| 中轨止盈 | ❌ 无 | ✅ 有（均值回归） |
| 多空独立风控 | ❌ 统一 | ✅ 独立参数 |
| 假突破过滤 | ❌ 无 | ✅ 回踩容忍度 |
| 持仓持久化 | ❌ 无 | ✅ 有 |

---

## 3. 市场方向判断

### 3.1 方向判断逻辑

```python
# 布林带突破强度判断方向
if price > upper_band:
    direction = LONG, confidence = breakout_strength / 2.0
elif price < lower_band:
    direction = SHORT, confidence = breakout_strength / 2.0
else:
    direction = NEUTRAL, confidence = 0.0

# 均线确认增强
if MA5 > MA20 and direction == LONG:  confidence *= 1.2
if MA5 < MA20 and direction == SHORT: confidence *= 1.2
else: confidence *= 0.8  # 方向不一致，降低置信度
```

### 3.2 信号调整规则

| 方向置信度 | 处理 |
|-----------|------|
| < 0.3 | 使用原始信号 |
| LONG + BUY | 允许 |
| LONG + SELL | 只平多，不开空 |
| SHORT + SELL | 允许 |
| SHORT + BUY | 只平空，不开多 |
| NEUTRAL | 使用原始信号 |

---

## 4. 风险控制

### 4.1 风控参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `stop_loss_pct` | 5% | 统一止损比例 |
| `take_profit_pct` | 8% | 统一止盈比例 |
| `max_position` | 10手 | 最大持仓限制 |
| `min_signal_interval` | 300秒 | 最小信号间隔 |

### 4.2 仓位计算

```python
if direction_confidence > 0.7:  multiplier = 1.0
elif direction_confidence > 0.5: multiplier = 0.8
else: multiplier = 0.5

volume = base_volume × multiplier
volume = min(volume, max_position - abs(pos))
```

---

## 5. 系统架构

### 5.1 框架集成

继承 `ARBIGCtaTemplate`，遵循以下规范：
- 使用 `on_bar_impl` / `on_tick_impl` / `on_trade_impl` / `on_order_impl`
- **不覆盖**父类的 `on_bar` / `on_tick` / `on_trade` / `on_order`
- 持仓变量由父类统一更新

### 5.2 处理流程

```
on_bar_impl
├── 更新 ArrayManager
├── 检查信号间隔
├── 更新市场方向判断
└── 根据 strategy_type 生成信号
    ├── TREND → _trend_strategy()
    ├── MEAN_REVERSION → _mean_reversion_strategy()
    └── BREAKOUT → _breakout_strategy()
        └── 方向调整 → 执行信号

on_tick_impl
└── 实时风控检查（止损/止盈）
```

---

## 6. 参数配置

### 6.1 完整参数列表

```python
{
    'strategy_type': 'trend',        # trend | mean_reversion | breakout
    'ma_short': 5,
    'ma_long': 20,
    'rsi_period': 14,
    'rsi_overbought': 70,
    'rsi_oversold': 30,
    'bollinger_period': 20,
    'bollinger_std': 2.0,
    'stop_loss_pct': 0.05,           # 5%
    'take_profit_pct': 0.08,         # 8%
    'trade_volume': 1,
    'max_position': 10,
    'min_signal_interval': 300,      # 5分钟
}
```

---

## 7. 未来规划

### 7.1 改造为调度器架构

```
MultiModeAdaptiveStrategy（调度器）
├── 市场环境识别
│   ├── 波动率分析（布林带带宽）
│   ├── 趋势强度分析（ADX/均线斜率）
│   └── 判定当前行情类型
│
├── 模式选择
│   ├── 趋势市 → 委托 MaRsiComboStrategy
│   ├── 突破市 → 委托 BreakoutStrategy
│   └── 震荡市 → 委托 MeanReversionStrategy
│
└── 统一风控
    └── 总仓位控制、总亏损限制
```

### 7.2 改造步骤
1. ✅ 三个独立策略已完成并修复 bug
2. ⬜ 独立策略回测验证
3. ⬜ 实现市场环境自动识别算法
4. ⬜ 改造 MultiMode 为调度器，委托执行
5. ⬜ 集成测试 + 参数优化

---

## 8. 日志输出说明

### 8.1 关键日志标识

| 标识 | 含义 |
|------|------|
| 📊 信号 | 交易信号生成 |
| 🛑 止损/止盈 | 风控触发 |
| ✅ 成交 | 成交回报 |

---

**文档版本**：v1.0
**最后更新**：2026-03-07
**维护者**：ARBIG量化团队

**更新记录**：
- v1.0 (2026-03-07)：初始版本，记录当前简化版逻辑和未来改造规划

