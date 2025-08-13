# 策略架构重新设计方案

## 🎯 设计原则

### 1. 分层解耦
- **信号层**: 纯粹的技术分析和信号生成
- **决策层**: 基于信号的交易决策逻辑
- **执行层**: 订单生成和风控检查
- **管理层**: 策略生命周期和状态管理

### 2. 单一职责
- 每个组件只负责一个明确的功能
- 策略只关注信号生成，不处理执行细节
- 执行引擎只关注订单处理，不关心策略逻辑

### 3. 可测试性
- 每个组件都可以独立测试
- 支持历史数据回测
- 支持模拟环境验证

## 🏗️ 新架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    策略管理层 (Strategy Manager)              │
├─────────────────────────────────────────────────────────────┤
│  - 策略生命周期管理                                          │
│  - 策略配置管理                                              │
│  - 策略状态监控                                              │
│  - 策略性能统计                                              │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    策略执行引擎 (Strategy Engine)             │
├─────────────────────────────────────────────────────────────┤
│  - 接收市场数据                                              │
│  - 调用策略计算                                              │
│  - 处理策略信号                                              │
│  - 风控检查                                                  │
│  - 订单生成                                                  │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    策略实例 (Strategy Instance)              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   信号生成器     │  │   决策引擎       │  │   风控模块       ││
│  │ Signal Generator │  │ Decision Engine │  │ Risk Controller ││
│  │                 │  │                 │  │                 ││
│  │ - 技术指标计算   │  │ - 信号过滤       │  │ - 仓位限制       ││
│  │ - 模式识别       │  │ - 时机选择       │  │ - 止损止盈       ││
│  │ - 信号生成       │  │ - 仓位计算       │  │ - 风险评估       ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    交易执行层 (Trading Executor)             │
├─────────────────────────────────────────────────────────────┤
│  - 订单路由                                                  │
│  - 订单管理                                                  │
│  - 成交回报                                                  │
│  - 持仓更新                                                  │
└─────────────────────────────────────────────────────────────┘
```

## 📋 组件详细设计

### 1. 信号生成器 (Signal Generator)

**职责**: 纯粹的技术分析，生成买卖信号

```python
class SignalGenerator:
    def __init__(self, config):
        self.indicators = self._init_indicators(config)
    
    def generate_signal(self, market_data) -> Signal:
        """生成交易信号"""
        # 只关注技术分析，不考虑仓位、资金等
        pass
    
    def _calculate_ma(self, prices, period):
        """计算移动平均线"""
        pass
    
    def _calculate_rsi(self, prices, period):
        """计算RSI"""
        pass
```

### 2. 决策引擎 (Decision Engine)

**职责**: 基于信号做出交易决策

```python
class DecisionEngine:
    def __init__(self, config):
        self.filters = self._init_filters(config)
        self.position_sizer = PositionSizer(config)
    
    def make_decision(self, signal, market_context, portfolio_context) -> Decision:
        """基于信号和上下文做出决策"""
        # 信号过滤
        if not self._filter_signal(signal, market_context):
            return None
        
        # 计算仓位
        position = self.position_sizer.calculate(signal, portfolio_context)
        
        return Decision(action=signal.action, quantity=position, price=signal.price)
```

### 3. 风控模块 (Risk Controller)

**职责**: 风险检查和控制

```python
class RiskController:
    def __init__(self, config):
        self.max_position = config.get('max_position')
        self.stop_loss = config.get('stop_loss')
        self.max_drawdown = config.get('max_drawdown')
    
    def check_risk(self, decision, portfolio_state) -> bool:
        """检查决策是否符合风控要求"""
        # 仓位检查
        # 止损检查
        # 回撤检查
        pass
```

### 4. 策略实例 (Strategy Instance)

**职责**: 组合各个组件，实现完整策略逻辑

```python
class StrategyInstance:
    def __init__(self, name, config):
        self.name = name
        self.signal_generator = SignalGenerator(config['signals'])
        self.decision_engine = DecisionEngine(config['decisions'])
        self.risk_controller = RiskController(config['risk'])
        
        self.state = StrategyState()
    
    def process_market_data(self, market_data) -> List[Order]:
        """处理市场数据，返回订单列表"""
        # 1. 生成信号
        signal = self.signal_generator.generate_signal(market_data)
        if not signal:
            return []
        
        # 2. 做出决策
        decision = self.decision_engine.make_decision(
            signal, market_data, self.state.portfolio
        )
        if not decision:
            return []
        
        # 3. 风控检查
        if not self.risk_controller.check_risk(decision, self.state):
            return []
        
        # 4. 生成订单
        orders = self._create_orders(decision)
        
        # 5. 更新状态
        self.state.update_pending_orders(orders)
        
        return orders
```

## 🔄 策略执行流程

### 1. 数据流
```
市场数据 → 策略实例 → 信号生成 → 决策制定 → 风控检查 → 订单生成 → 交易执行
```

### 2. 状态管理
```
策略状态 ← 成交回报 ← 订单状态 ← 交易执行
```

### 3. 监控反馈
```
性能统计 ← 策略状态 ← 持仓变化 ← 成交记录
```

## 🎛️ 配置驱动设计

### 策略配置示例
```yaml
strategy:
  name: "SHFE_MA_Strategy"
  type: "trend_following"
  
  signals:
    indicators:
      - type: "MA"
        short_period: 5
        long_period: 20
      - type: "RSI"
        period: 14
        overbought: 70
        oversold: 30
    
    rules:
      - condition: "MA_short > MA_long AND RSI < 70"
        signal: "BUY"
      - condition: "MA_short < MA_long AND RSI > 30"
        signal: "SELL"
  
  decisions:
    filters:
      - type: "time_filter"
        start_time: "09:00"
        end_time: "15:00"
      - type: "volatility_filter"
        min_volatility: 0.01
        max_volatility: 0.05
    
    position_sizing:
      method: "fixed_fraction"
      fraction: 0.02
      max_position: 1000
  
  risk:
    max_position: 1000
    stop_loss: 0.02
    take_profit: 0.05
    max_drawdown: 0.10
    max_daily_loss: 0.05
```

## 🧪 测试策略

### 1. 单元测试
```python
def test_signal_generator():
    generator = SignalGenerator(config)
    signal = generator.generate_signal(mock_data)
    assert signal.action == "BUY"
    assert signal.strength > 0.5

def test_decision_engine():
    engine = DecisionEngine(config)
    decision = engine.make_decision(mock_signal, mock_context, mock_portfolio)
    assert decision.quantity > 0
```

### 2. 集成测试
```python
def test_strategy_instance():
    strategy = StrategyInstance("test", config)
    orders = strategy.process_market_data(mock_market_data)
    assert len(orders) > 0
    assert orders[0].symbol == "au2509"
```

### 3. 回测验证
```python
def test_backtest():
    strategy = StrategyInstance("backtest", config)
    backtest_engine = BacktestEngine(historical_data)
    results = backtest_engine.run(strategy)
    
    assert results.total_return > 0
    assert results.sharpe_ratio > 1.0
    assert results.max_drawdown < 0.1
```

## 🚀 实施优势

### 1. 清晰的职责分离
- 每个组件职责明确，易于理解和维护
- 可以独立开发和测试各个组件
- 便于团队协作开发

### 2. 高度可配置
- 通过配置文件控制策略行为
- 无需修改代码即可调整参数
- 支持A/B测试和参数优化

### 3. 易于扩展
- 新增指标只需实现SignalGenerator接口
- 新增决策逻辑只需扩展DecisionEngine
- 新增风控规则只需扩展RiskController

### 4. 便于监控
- 每个环节都有明确的输入输出
- 可以监控每个组件的性能
- 便于问题定位和调试

## 🎯 下一步实施计划

### 阶段1: 重构现有策略
1. 将SHFE策略按新架构重构
2. 实现基础的信号生成器
3. 实现简单的决策引擎

### 阶段2: 完善执行引擎
1. 实现策略执行引擎
2. 集成风控模块
3. 完善订单管理

### 阶段3: 增强功能
1. 实现回测框架
2. 添加性能监控
3. 支持多策略并行

这个新架构将大大提高策略的可维护性、可测试性和可扩展性。
