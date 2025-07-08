# ARBIG 策略文档

## 📋 策略概述

本目录包含ARBIG系统支持的各种量化交易策略的详细文档，包括策略原理、参数配置、使用指南等。

## 📚 策略文档列表

### 🔄 套利策略

#### 1. [基差套利策略](SPREAD_THRESHOLD_GUIDE.md)
- **策略类型**: 跨市场套利
- **适用市场**: 香港离岸人民币黄金 vs 上海黄金交易所
- **核心原理**: 利用两地黄金价格差异进行套利
- **风险等级**: 中等
- **预期收益**: 年化8-15%

**主要内容**:
- 阈值设置原理和计算方法
- 保守/平衡/激进三种策略配置
- 动态阈值调整机制
- 实际应用场景和案例
- 风险控制和优化建议

### 📈 趋势策略

#### 2. 上海市场量化策略 (开发中)
- **策略类型**: 趋势跟踪
- **适用市场**: 上期所黄金期货
- **核心原理**: 基于技术指标的趋势识别
- **风险等级**: 中高
- **预期收益**: 年化12-20%

### 📊 均值回归策略

#### 3. 价格回归策略 (规划中)
- **策略类型**: 均值回归
- **适用市场**: 多市场
- **核心原理**: 价格偏离均值后的回归特性
- **风险等级**: 中等
- **预期收益**: 年化6-12%

## 🎯 策略选择指南

### 风险偏好分类

**保守型投资者**:
- ✅ 基差套利策略 (保守配置)
- 📊 建议配置: 低杠杆、严格止损
- 🎯 预期收益: 8-12%

**平衡型投资者**:
- ✅ 基差套利策略 (平衡配置)
- ✅ 趋势跟踪策略 (中等参数)
- 📊 建议配置: 适中杠杆、动态调整
- 🎯 预期收益: 12-18%

**激进型投资者**:
- ✅ 基差套利策略 (激进配置)
- ✅ 趋势跟踪策略 (敏感参数)
- ✅ 多策略组合
- 📊 建议配置: 高杠杆、快速响应
- 🎯 预期收益: 18-25%

## 🔧 策略配置

### 配置文件结构

```yaml
# config.yaml
strategies:
  # 基差套利策略
  - name: "spread_arbitrage"
    type: "spread_arbitrage"
    enabled: true
    config:
      # 阈值设置
      entry_threshold: 0.8      # 开仓阈值
      exit_threshold: 0.2       # 平仓阈值
      stop_loss_threshold: 1.5  # 止损阈值
      
      # 交易参数
      max_position: 1000        # 最大持仓
      shfe_symbol: "AU2508"     # 上期所合约
      mt5_symbol: "XAUUSD"      # MT5合约
      
      # 风控参数
      max_hold_time: 3600       # 最大持仓时间(秒)
      transaction_cost: 0.1     # 交易成本
      min_profit: 0.3           # 最小利润要求

  # 趋势跟踪策略
  - name: "shfe_trend"
    type: "shfe_quant"
    enabled: false
    config:
      strategy_type: "trend"
      symbol: "AU2508"
      max_position: 500
      ma_short: 5
      ma_long: 20
      rsi_period: 14
      rsi_overbought: 70
      rsi_oversold: 30
```

### 策略切换

```bash
# 启动特定策略
python main.py --strategy spread_arbitrage

# 查看可用策略
python main.py --list

# 交互式选择策略
python main.py
```

## 📊 策略监控

### Web管理界面

通过 `http://localhost:8000` 访问Web管理系统：

1. **📈 信号监控**
   - 实时查看策略信号
   - 信号触发原因分析
   - 信号执行状态跟踪

2. **📋 订单管理**
   - 策略订单状态监控
   - 订单与信号关联查看
   - 手动干预和调整

3. **🛡️ 风控管理**
   - 策略级别的暂停/恢复
   - 紧急平仓功能
   - 风险指标监控

### 策略表现分析

```python
# 获取策略信号分析
analysis = trading_monitor.get_signal_analysis()

print(f"总信号数: {analysis['total_signals']}")
print(f"执行率: {analysis['execution_rate']:.1%}")
print(f"平均信号强度: {analysis['avg_strength']:.2f}")

# 按策略分组统计
for strategy, count in analysis['signal_by_strategy'].items():
    print(f"{strategy}: {count} 个信号")
```

## 🧪 策略测试

### 回测测试

```bash
# 基差套利策略回测
python tests/backtest_spread_arbitrage.py

# 指定时间范围回测
python tests/backtest_spread_arbitrage.py --start 2024-01-01 --end 2024-12-31
```

### 实盘测试

```bash
# 信号监控测试
python test_signal_monitoring.py

# 策略执行测试
python tests/test_strategy_execution.py
```

## 📈 策略优化

### 参数优化流程

1. **历史数据分析**
   - 收集足够的历史数据
   - 分析市场特征和规律
   - 识别最佳参数范围

2. **回测验证**
   - 使用历史数据回测
   - 计算关键指标 (收益率、夏普比率、最大回撤)
   - 选择最优参数组合

3. **实盘验证**
   - 小资金实盘测试
   - 监控实际表现
   - 根据结果调整参数

4. **持续优化**
   - 定期评估策略表现
   - 根据市场变化调整
   - 引入新的优化技术

### 优化工具

```python
# 参数优化示例
from strategies.optimizer import ParameterOptimizer

optimizer = ParameterOptimizer('spread_arbitrage')
best_params = optimizer.optimize(
    param_ranges={
        'entry_threshold': (0.5, 1.2),
        'exit_threshold': (0.1, 0.5),
        'stop_loss_threshold': (1.0, 2.0)
    },
    objective='sharpe_ratio',
    data_period='2024-01-01:2024-12-31'
)
```

## 🔍 策略开发

### 开发新策略

1. **策略设计**
   - 明确策略逻辑和原理
   - 定义信号生成规则
   - 设计风控机制

2. **代码实现**
   - 继承策略基类
   - 实现核心逻辑方法
   - 添加参数配置

3. **测试验证**
   - 单元测试
   - 回测验证
   - 实盘测试

4. **文档编写**
   - 策略说明文档
   - 参数配置指南
   - 使用示例

### 策略模板

```python
# strategies/custom_strategy.py
from core.strategy_base import StrategyBase

class CustomStrategy(StrategyBase):
    def __init__(self, config):
        super().__init__(config)
        self.param1 = config.get('param1', default_value)
        
    def on_tick(self, tick):
        # 处理tick数据
        signal = self.generate_signal(tick)
        if signal:
            self.send_order(signal)
    
    def generate_signal(self, tick):
        # 信号生成逻辑
        pass
    
    def on_order(self, order):
        # 订单状态处理
        pass
```

## 📞 支持和反馈

- **文档问题**: 请在项目Issues中反馈
- **策略建议**: 欢迎提交策略改进建议
- **技术支持**: 查看主文档或联系开发团队

---

**注意**: 所有策略都包含市场风险，请根据自身风险承受能力选择合适的策略配置。
