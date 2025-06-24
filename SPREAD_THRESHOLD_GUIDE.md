# 基差套利阈值设置指南

## 核心问题
基差套利需要回答两个关键问题：
1. **什么时候开仓？** - 基差达到多少时开始套利
2. **什么时候平仓？** - 基差回归到多少时结束套利

## 阈值设置原理

### 第一性原理分析

#### 1. 开仓阈值（Entry Threshold）
**目标**：确保开仓后能够盈利

```python
# 开仓阈值 = 交易成本 + 预期利润 + 安全边际
entry_threshold = transaction_cost + expected_profit + safety_margin

# 具体计算
transaction_cost = 手续费 + 滑点 + 资金成本  # 约0.1-0.2元/克
expected_profit = 历史基差回归平均收益      # 约0.3-0.5元/克  
safety_margin = 防止假突破的缓冲          # 约0.2-0.3元/克

# 建议开仓阈值：0.8元/克
```

#### 2. 平仓阈值（Exit Threshold）
**目标**：及时锁定利润，避免基差反转

```python
# 平仓阈值 = 交易成本 + 最小利润
exit_threshold = transaction_cost + min_profit

# 具体计算
transaction_cost = 平仓手续费 + 滑点     # 约0.1-0.2元/克
min_profit = 最小利润要求               # 约0.1-0.2元/克

# 建议平仓阈值：0.2元/克
```

#### 3. 止损阈值（Stop Loss Threshold）
**目标**：控制最大亏损

```python
# 止损阈值 = 开仓阈值 + 最大容忍亏损
stop_loss_threshold = entry_threshold + max_loss_tolerance

# 建议止损阈值：1.5元/克
```

## 具体阈值建议

### 保守策略（低风险）
```python
entry_threshold = 1.0    # 开仓阈值：1.0元/克
exit_threshold = 0.3     # 平仓阈值：0.3元/克
stop_loss_threshold = 2.0 # 止损阈值：2.0元/克
```

### 平衡策略（中等风险）
```python
entry_threshold = 0.8    # 开仓阈值：0.8元/克
exit_threshold = 0.2     # 平仓阈值：0.2元/克
stop_loss_threshold = 1.5 # 止损阈值：1.5元/克
```

### 激进策略（高风险）
```python
entry_threshold = 0.5    # 开仓阈值：0.5元/克
exit_threshold = 0.1     # 平仓阈值：0.1元/克
stop_loss_threshold = 1.0 # 止损阈值：1.0元/克
```

## 动态阈值调整

### 1. 基于波动率调整
```python
# 高波动率时提高阈值
if volatility > historical_volatility * 1.5:
    adjusted_entry = entry_threshold * 1.2
    adjusted_exit = exit_threshold * 1.2
```

### 2. 基于市场状态调整
```python
# 突破市场时调整阈值
if market_condition == 'BULLISH_BREAKOUT':
    entry_threshold *= 0.8  # 降低开仓阈值
    exit_threshold *= 1.2   # 提高平仓阈值
```

### 3. 基于持仓时间调整
```python
# 持仓时间越长，平仓阈值越低
time_factor = 1 - (hold_time / max_hold_time) * time_decay_factor
adjusted_exit = exit_threshold * time_factor
```

## 实际应用示例

### 场景1：正常市场
- SHFE价格：500元/克
- MT5价格：499元/克
- 基差：+1.0元/克
- **决策**：开仓（基差 > 0.8）
- **操作**：买入MT5，卖出SHFE

### 场景2：基差回归
- SHFE价格：500.5元/克
- MT5价格：500.3元/克
- 基差：+0.2元/克
- **决策**：平仓（基差 < 0.2）
- **操作**：卖出MT5，买入SHFE

### 场景3：基差扩大
- SHFE价格：501元/克
- MT5价格：497元/克
- 基差：+4.0元/克
- **决策**：止损（基差 > 1.5）
- **操作**：强制平仓

## 阈值优化建议

### 1. 历史数据分析
- 分析历史基差的分布特征
- 计算基差回归的平均时间和幅度
- 确定最优的阈值组合

### 2. 回测验证
- 使用历史数据回测不同阈值组合
- 计算夏普比率、最大回撤等指标
- 选择风险收益比最优的阈值

### 3. 实时监控
- 监控基差的实际表现
- 根据市场变化动态调整阈值
- 定期评估和优化阈值设置

## 风险提示

1. **阈值过低**：频繁交易，成本过高
2. **阈值过高**：错过套利机会
3. **平仓过晚**：基差反转导致亏损
4. **止损过严**：过早止损，错失盈利

## 配置示例

```python
# config.yaml
spread_arbitrage:
  entry_threshold: 0.8      # 开仓阈值
  exit_threshold: 0.2       # 平仓阈值
  stop_loss_threshold: 1.5  # 止损阈值
  max_hold_time: 3600       # 最大持仓时间
  transaction_cost: 0.1     # 交易成本
  min_profit: 0.3           # 最小利润
``` 