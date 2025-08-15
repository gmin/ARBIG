# 账户信息服务使用指南

## 概述

ARBIG账户信息服务 (`AccountService`) 采用混合模式（查询+推送）管理账户资金、持仓信息，提供实时的账户状态监控和数据缓存功能。

## 核心特性

- ✅ **混合模式管理** - 定时查询 + 实时推送
- ✅ **智能缓存机制** - 高效的账户数据缓存
- ✅ **实时状态监控** - 账户、持仓、订单、成交信息
- ✅ **定时自动更新** - 可配置的查询间隔
- ✅ **事件驱动通知** - 基于事件的数据分发
- ✅ **完善的回调机制** - 支持多种数据回调

## 混合模式设计

### 查询模式（主动获取）
- **账户资金信息** - 定时查询（默认30秒）+ 交易前后主动查询
- **持仓信息** - 定时查询（默认30秒）+ 交易前后主动查询

### 推送模式（被动接收）
- **订单状态变化** - CTP实时推送（OnRtnOrder）
- **成交信息** - CTP实时推送（OnRtnTrade）

## 快速开始

### 1. 基本使用

```python
from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from core.services.account_service import AccountService
from core.types import ServiceConfig
from gateways.ctp_gateway import CtpGatewayWrapper

# 创建组件
event_engine = EventEngine()
config_manager = ConfigManager()
ctp_gateway = CtpGatewayWrapper(config_manager)

# 连接CTP
ctp_gateway.connect()

# 创建账户服务
service_config = ServiceConfig(
    name="account",
    enabled=True,
    config={
        'update_interval': 30,      # 30秒查询间隔
        'position_sync': True,      # 同步持仓信息
        'auto_query_after_trade': True  # 成交后自动查询
    }
)

account_service = AccountService(event_engine, service_config, ctp_gateway)

# 启动服务
account_service.start()
```

### 2. 获取账户信息

```python
# 获取账户信息（从缓存）
account = account_service.get_account_info()
if account:
    print(f"可用资金: {account.available}")
    print(f"总资金: {account.balance}")
    print(f"冻结资金: {account.frozen}")

# 主动查询最新账户信息
success = account_service.query_account_info()
```

### 3. 获取持仓信息

```python
# 获取所有持仓
positions = account_service.get_positions()
for pos in positions:
    print(f"{pos.symbol} {pos.direction.value}: {pos.volume} 手")

# 获取特定合约持仓
au_positions = account_service.get_positions('au2509')

# 获取单个合约持仓
position = account_service.get_position_by_symbol('au2509')
```

### 4. 添加回调函数

```python
def on_account_update(account):
    print(f"账户更新: 可用资金 {account.available}")

def on_position_update(position):
    print(f"持仓更新: {position.symbol} {position.volume}")

def on_trade(trade):
    print(f"成交通知: {trade.symbol} {trade.volume}@{trade.price}")

# 添加回调
account_service.add_account_callback(on_account_update)
account_service.add_position_callback(on_position_update)
account_service.add_trade_callback(on_trade)
```

## 配置说明

### 服务配置

```yaml
services:
  account:
    enabled: true
    update_interval: 30           # 定时查询间隔（秒）
    position_sync: true           # 是否同步持仓信息
    auto_query_after_trade: true  # 成交后是否自动查询
```

### 高级配置

```python
service_config = ServiceConfig(
    name="account",
    enabled=True,
    config={
        'update_interval': 30,          # 查询间隔
        'position_sync': True,          # 持仓同步
        'auto_query_after_trade': True, # 成交后查询
        'cache_timeout': 300,           # 缓存超时时间
        'max_query_retries': 3          # 最大查询重试次数
    }
)
```

## API参考

### AccountService

#### 服务生命周期

```python
def start() -> bool                    # 启动服务
def stop() -> None                     # 停止服务
def get_status() -> ServiceStatus      # 获取服务状态
```

#### 数据查询方法

```python
# 账户信息
def get_account_info() -> Optional[AccountData]           # 获取缓存的账户信息
def query_account_info() -> bool                          # 主动查询账户信息
def get_available_funds() -> float                        # 获取可用资金

# 持仓信息
def get_positions(symbol: str = None) -> List[PositionData]     # 获取持仓信息
def get_position_by_symbol(symbol: str) -> Optional[PositionData]  # 获取单个持仓
def query_positions() -> bool                                   # 主动查询持仓

# 订单和成交
def get_orders(symbol: str = None, active_only: bool = False) -> List[OrderData]  # 获取订单
def get_trades(symbol: str = None) -> List[TradeData]           # 获取成交记录
```

#### 回调管理

```python
def add_account_callback(callback: Callable[[AccountData], None])    # 添加账户回调
def add_position_callback(callback: Callable[[PositionData], None])  # 添加持仓回调
def add_order_callback(callback: Callable[[OrderData], None])        # 添加订单回调
def add_trade_callback(callback: Callable[[TradeData], None])        # 添加成交回调
```

#### 数据快照

```python
def get_account_snapshot() -> AccountSnapshot              # 获取账户快照
def get_statistics() -> Dict[str, any]                    # 获取服务统计
```

### 数据结构

#### AccountData
```python
@dataclass
class AccountData:
    accountid: str      # 账户ID
    balance: float      # 总资金
    frozen: float       # 冻结资金
    available: float    # 可用资金
    datetime: datetime  # 更新时间
```

#### PositionData
```python
@dataclass
class PositionData:
    symbol: str         # 合约代码
    exchange: str       # 交易所
    direction: Direction # 持仓方向
    volume: float       # 持仓数量
    frozen: float       # 冻结数量
    price: float        # 持仓均价
    pnl: float         # 持仓盈亏
    yd_volume: float   # 昨仓数量
```

## 示例程序

### 1. 基础演示

运行账户信息服务演示：

```bash
cd /root/ARBIG
python examples/account_demo.py
```

### 2. 综合演示

运行行情+账户综合演示：

```bash
cd /root/ARBIG
python examples/integrated_demo.py
```

### 3. 完整测试

运行完整的功能测试：

```bash
cd /root/ARBIG
python tests/test_account_service.py
```

## 监控和调试

### 1. 服务状态监控

```python
# 获取服务统计
stats = account_service.get_statistics()
print(f"状态: {stats['status']}")
print(f"可用资金: {stats['account_available']}")
print(f"持仓数量: {stats['positions_count']}")
print(f"查询间隔: {stats['query_interval']}")

# 获取最后查询时间
print(f"最后账户查询: {stats['last_account_query']}")
print(f"最后持仓查询: {stats['last_position_query']}")
```

### 2. 实时数据监控

```python
def monitor_account_changes(account):
    """监控账户变化"""
    print(f"[{datetime.now()}] 账户更新:")
    print(f"  可用资金: {account.available:,.2f}")
    print(f"  资金变化: {account.available - previous_balance:+,.2f}")

account_service.add_account_callback(monitor_account_changes)
```

### 3. 性能监控

```python
import time

start_time = time.time()
account_updates = 0

def performance_monitor(account):
    global account_updates
    account_updates += 1
    elapsed = time.time() - start_time
    rate = account_updates / elapsed
    print(f"账户更新速率: {rate:.2f} 次/秒")

account_service.add_account_callback(performance_monitor)
```

## 故障排除

### 常见问题

#### 1. 查询失败

**问题**: 账户或持仓查询失败

**解决方案**:
- 检查CTP交易服务器连接状态
- 验证账户权限
- 检查查询频率限制
- 查看CTP错误日志

#### 2. 数据不更新

**问题**: 缓存数据长时间不更新

**解决方案**:
- 检查定时查询线程状态
- 验证查询间隔配置
- 检查网络连接稳定性
- 重启服务

#### 3. 内存占用过高

**问题**: 长时间运行后内存占用增长

**解决方案**:
- 定期清理历史订单和成交数据
- 调整缓存超时时间
- 监控数据增长速度

### 调试技巧

1. **启用详细日志**:
   ```python
   import logging
   logging.getLogger('core.services.account_service').setLevel(logging.DEBUG)
   ```

2. **监控查询频率**:
   ```python
   def query_monitor():
       while True:
           stats = account_service.get_statistics()
           print(f"最后查询: {stats['last_account_query']}")
           time.sleep(10)
   ```

3. **检查数据一致性**:
   ```python
   # 比较缓存和实时查询结果
   cached_account = account_service.get_account_info()
   account_service.query_account_info()
   time.sleep(2)
   fresh_account = account_service.get_account_info()
   
   if cached_account and fresh_account:
       diff = fresh_account.available - cached_account.available
       print(f"资金差异: {diff}")
   ```

## 最佳实践

1. **合理设置查询间隔**: 根据交易频率调整，避免过于频繁查询
2. **及时处理回调**: 回调函数应快速执行，避免阻塞
3. **监控服务状态**: 定期检查服务运行状态和连接状态
4. **数据验证**: 对关键数据进行合理性验证
5. **异常处理**: 为所有操作添加适当的异常处理
6. **资源清理**: 程序结束时正确停止服务和清理资源

## 性能指标

- **查询响应时间**: < 2秒
- **数据更新延迟**: < 5秒
- **内存使用**: 基础运行约50MB
- **查询成功率**: > 95%

---

**文档版本**: v1.0  
**最后更新**: 2025-01-04  
**维护者**: ARBIG开发团队
