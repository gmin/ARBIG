# 交易执行服务使用指南

## 概述

ARBIG交易执行服务 (`TradingService`) 是系统的核心执行模块，负责将策略信号转换为实际的交易订单，提供完整的订单生命周期管理和风控集成功能。

## 核心特性

- ✅ **完整订单管理** - 订单发送、撤销、状态跟踪
- ✅ **策略信号处理** - 自动将策略信号转换为订单
- ✅ **风控集成** - 交易前风控检查和限制
- ✅ **订单路由** - 智能订单路由和执行
- ✅ **实时状态跟踪** - 订单和成交状态实时监控
- ✅ **策略级管理** - 按策略分组管理订单
- ✅ **完善的统计** - 详细的交易统计和分析

## 系统架构

```
策略信号 → TradingService → 风控检查 → CTP网关 → 交易所
    ↓           ↓              ↓          ↓         ↓
  信号处理   订单管理      风控验证    订单路由    订单执行
    ↓           ↓              ↓          ↓         ↓
  订单生成   状态跟踪      风险控制    状态反馈    成交回报
```

## 快速开始

### 1. 基本使用

```python
from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from core.services.trading_service import TradingService
from core.services.account_service import AccountService
from core.services.risk_service import RiskService
from core.types import ServiceConfig, OrderRequest, Direction, OrderType
from gateways.ctp_gateway import CtpGatewayWrapper

# 创建组件
event_engine = EventEngine()
config_manager = ConfigManager()
ctp_gateway = CtpGatewayWrapper(config_manager)

# 连接CTP
ctp_gateway.connect()

# 创建依赖服务
account_service = AccountService(event_engine, account_config, ctp_gateway)
risk_service = RiskService(event_engine, risk_config, account_service)

# 创建交易服务
trading_config = ServiceConfig(
    name="trading",
    enabled=True,
    config={
        'order_timeout': 30,
        'max_orders_per_second': 5
    }
)

trading_service = TradingService(
    event_engine, trading_config, ctp_gateway,
    account_service, risk_service
)

# 启动服务
trading_service.start()
```

### 2. 发送订单

```python
# 创建订单请求
order_req = OrderRequest(
    symbol="au2509",
    exchange="SHFE",
    direction=Direction.LONG,
    type=OrderType.LIMIT,
    volume=1.0,
    price=500.0,
    reference="my_strategy_buy"
)

# 发送订单
order_id = trading_service.send_order(order_req)
if order_id:
    print(f"订单发送成功: {order_id}")
```

### 3. 处理策略信号

```python
from core.types import SignalData
from core.constants import SIGNAL_EVENT

# 创建策略信号
signal = SignalData(
    strategy_name="my_strategy",
    symbol="au2509",
    direction=Direction.LONG,
    action="OPEN",
    volume=1.0,
    price=500.0,
    signal_type="TRADE",
    confidence=0.8
)

# 发送信号事件
signal_event = Event(SIGNAL_EVENT, signal)
trading_service.process_signal(signal_event)
```

### 4. 订单管理

```python
# 获取所有订单
orders = trading_service.get_orders()

# 获取活跃订单
active_orders = trading_service.get_active_orders()

# 获取策略订单
strategy_orders = trading_service.get_orders_by_strategy("my_strategy")

# 撤销订单
success = trading_service.cancel_order(order_id)

# 批量撤销策略订单
cancelled_count = trading_service.cancel_strategy_orders("my_strategy")
```

### 5. 添加回调函数

```python
def on_order_update(order):
    print(f"订单更新: {order.orderid} {order.status.value}")

def on_trade(trade):
    print(f"成交通知: {trade.symbol} {trade.volume}@{trade.price}")

# 添加回调
trading_service.add_order_callback(on_order_update)
trading_service.add_trade_callback(on_trade)
```

## 配置说明

### 服务配置

```yaml
services:
  trading:
    enabled: true
    order_timeout: 30              # 订单超时时间（秒）
    max_orders_per_second: 5       # 每秒最大订单数
    enable_risk_check: true        # 是否启用风控检查
    auto_cancel_timeout: true      # 是否自动撤销超时订单
```

### 高级配置

```python
trading_config = ServiceConfig(
    name="trading",
    enabled=True,
    config={
        'order_timeout': 30,           # 订单超时时间
        'max_orders_per_second': 5,    # 订单频率限制
        'enable_risk_check': True,     # 风控检查开关
        'auto_cancel_timeout': True,   # 自动撤销超时订单
        'retry_failed_orders': False,  # 是否重试失败订单
        'max_retry_count': 3           # 最大重试次数
    }
)
```

## API参考

### TradingService

#### 服务生命周期

```python
def start() -> bool                    # 启动服务
def stop() -> None                     # 停止服务
def get_status() -> ServiceStatus      # 获取服务状态
```

#### 订单管理

```python
# 订单操作
def send_order(order_req: OrderRequest) -> Optional[str]     # 发送订单
def cancel_order(order_id: str) -> bool                     # 撤销订单
def cancel_strategy_orders(strategy_name: str, symbol: str = None) -> int  # 批量撤销

# 订单查询
def get_order(order_id: str) -> Optional[OrderData]         # 获取单个订单
def get_orders(symbol: str = None, active_only: bool = False) -> List[OrderData]  # 获取订单列表
def get_active_orders() -> List[OrderData]                  # 获取活跃订单
def get_orders_by_strategy(strategy_name: str) -> List[OrderData]  # 获取策略订单
```

#### 成交查询

```python
def get_trades(symbol: str = None) -> List[TradeData]       # 获取成交记录
```

#### 策略信号处理

```python
def process_signal(signal_event: Event) -> None             # 处理策略信号
```

#### 回调管理

```python
def add_order_callback(callback: Callable[[OrderData], None])    # 添加订单回调
def add_trade_callback(callback: Callable[[TradeData], None])    # 添加成交回调
```

#### 统计和监控

```python
def get_statistics() -> Dict[str, any]                      # 获取服务统计
def get_strategy_statistics(strategy_name: str) -> Dict[str, any]  # 获取策略统计
```

### 数据结构

#### OrderRequest
```python
@dataclass
class OrderRequest:
    symbol: str         # 合约代码
    exchange: str       # 交易所
    direction: Direction # 买卖方向
    type: OrderType     # 订单类型
    volume: float       # 数量
    price: float        # 价格
    offset: Offset      # 开平标志
    reference: str      # 订单引用
```

#### SignalData
```python
@dataclass
class SignalData:
    strategy_name: str  # 策略名称
    symbol: str         # 合约代码
    direction: Direction # 方向
    action: str         # 动作（OPEN/CLOSE）
    volume: float       # 数量
    price: float        # 价格
    signal_type: str    # 信号类型
    confidence: float   # 信号置信度
```

## 策略信号处理

### 信号类型

1. **TRADE信号** - 直接交易信号
2. **POSITION信号** - 仓位调整信号
3. **RISK信号** - 风险控制信号

### 信号处理流程

```python
def process_signal(self, signal_event: Event) -> None:
    signal = signal_event.data
    
    # 1. 信号验证
    if not self._validate_signal(signal):
        return
    
    # 2. 转换为订单请求
    order_req = self._signal_to_order(signal)
    
    # 3. 风控检查
    risk_result = self.risk_service.check_pre_trade_risk(order_req)
    if not risk_result.passed:
        return
    
    # 4. 发送订单
    self.send_order(order_req)
```

## 示例程序

### 1. 基础演示

运行交易执行服务演示：

```bash
cd /root/ARBIG
python examples/trading_demo.py
```

### 2. 完整测试

运行完整的功能测试：

```bash
cd /root/ARBIG
python tests/test_trading_service.py
```

## 监控和调试

### 1. 实时监控

```python
# 监控订单状态
def monitor_orders():
    while True:
        active_orders = trading_service.get_active_orders()
        print(f"活跃订单数: {len(active_orders)}")
        time.sleep(10)

# 监控交易统计
stats = trading_service.get_statistics()
print(f"总订单数: {stats['total_orders']}")
print(f"总成交数: {stats['total_trades']}")
print(f"成交金额: {stats['total_turnover']:,.2f}")
```

### 2. 策略监控

```python
# 监控策略表现
strategy_stats = trading_service.get_strategy_statistics("my_strategy")
print(f"策略订单数: {strategy_stats['total_orders']}")
print(f"策略成交量: {strategy_stats['total_volume']}")
print(f"平均成交价: {strategy_stats['avg_price']:.2f}")
```

### 3. 风险监控

```python
# 监控风险状态
def monitor_risk():
    risk_metrics = risk_service.get_risk_metrics()
    if risk_metrics.risk_level == "HIGH":
        # 暂停新订单
        trading_service.pause_new_orders()
```

## 故障排除

### 常见问题

#### 1. 订单发送失败

**问题**: 订单无法发送或被拒绝

**解决方案**:
- 检查CTP交易服务器连接
- 验证合约代码和参数
- 检查账户权限和资金
- 查看风控检查结果

#### 2. 订单状态不更新

**问题**: 订单状态长时间不变

**解决方案**:
- 检查CTP连接稳定性
- 验证订单ID正确性
- 检查交易时间段
- 查看CTP错误日志

#### 3. 策略信号不执行

**问题**: 策略信号无法转换为订单

**解决方案**:
- 检查信号格式和内容
- 验证风控检查设置
- 检查服务运行状态
- 查看信号处理日志

### 调试技巧

1. **启用详细日志**:
   ```python
   import logging
   logging.getLogger('core.services.trading_service').setLevel(logging.DEBUG)
   ```

2. **监控订单流程**:
   ```python
   def debug_order_flow(order):
       print(f"订单状态变化: {order.orderid} -> {order.status.value}")
   
   trading_service.add_order_callback(debug_order_flow)
   ```

3. **检查风控结果**:
   ```python
   # 在发送订单前检查风控
   risk_result = risk_service.check_pre_trade_risk(order_req)
   if not risk_result.passed:
       print(f"风控拒绝: {risk_result.reason}")
   ```

## 最佳实践

1. **订单管理**:
   - 为每个订单设置合理的引用标识
   - 定期清理已完成的历史订单
   - 监控订单超时和异常状态

2. **策略集成**:
   - 使用标准的信号格式
   - 实现策略级的订单管理
   - 添加策略级的风控检查

3. **风险控制**:
   - 设置合理的订单频率限制
   - 实现多层次的风控检查
   - 监控实时风险指标

4. **性能优化**:
   - 避免在回调函数中执行耗时操作
   - 合理设置订单超时时间
   - 定期清理历史数据

5. **错误处理**:
   - 为所有操作添加异常处理
   - 实现订单失败重试机制
   - 记录详细的错误日志

## 性能指标

- **订单发送延迟**: < 100ms
- **状态更新延迟**: < 200ms
- **订单处理能力**: > 100 订单/分钟
- **系统可用性**: > 99.9%

---

**文档版本**: v1.0  
**最后更新**: 2025-01-04  
**维护者**: ARBIG开发团队
