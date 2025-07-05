# 行情订阅服务使用指南

## 概述

ARBIG行情订阅服务 (`MarketDataService`) 是基于vnpy/CTP框架实现的统一行情数据管理服务，提供实时行情订阅、数据缓存和事件分发功能。

## 核心特性

- ✅ **统一订阅管理** - 支持多客户端订阅同一合约
- ✅ **实时数据分发** - 基于事件驱动的行情数据分发
- ✅ **高效数据缓存** - 内存缓存最新Tick数据
- ✅ **CTP集成** - 完整集成vnpy-ctp网关
- ✅ **状态监控** - 实时服务状态和统计信息
- ✅ **错误处理** - 完善的异常处理和日志记录

## 快速开始

### 1. 基本使用

```python
from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from core.services.market_data_service import MarketDataService
from core.types import ServiceConfig
from gateways.ctp_gateway import CtpGatewayWrapper

# 创建组件
event_engine = EventEngine()
config_manager = ConfigManager()
ctp_gateway = CtpGatewayWrapper(config_manager)

# 连接CTP
ctp_gateway.connect()

# 创建行情服务
service_config = ServiceConfig(
    name="market_data",
    enabled=True,
    config={
        'symbols': ['au2509', 'au2512'],
        'cache_size': 1000
    }
)

market_service = MarketDataService(event_engine, service_config, ctp_gateway)

# 启动服务
market_service.start()
```

### 2. 订阅行情

```python
# 订阅合约
success = market_service.subscribe_symbol('au2509', 'my_strategy')
if success:
    print("订阅成功")

# 获取最新行情
tick = market_service.get_latest_tick('au2509')
if tick:
    print(f"最新价: {tick.last_price}")
```

### 3. 添加回调函数

```python
def on_tick(tick):
    print(f"收到行情: {tick.symbol} @ {tick.last_price}")

# 添加回调
market_service.add_tick_callback(on_tick)
```

## 配置说明

### 服务配置

```yaml
services:
  market_data:
    enabled: true
    symbols: ["AU2509", "AU2512"]  # 自动订阅的合约
    cache_size: 1000               # 缓存大小
```

### CTP配置

支持两种配置方式：

#### 1. JSON配置文件 (`config/ctp_sim.json`)

```json
{
    "用户名": "242407",
    "密码": "Crh1234567!",
    "经纪商代码": "9999",
    "交易服务器": "182.254.243.31:30001",
    "行情服务器": "182.254.243.31:30011",
    "产品名称": "simnow_client_test",
    "授权编码": "0000000000000000"
}
```

#### 2. YAML配置文件 (`config.yaml`)

```yaml
ctp:
  trading:
    userid: "242407"
    password: "Crh1234567!"
    brokerid: "9999"
    td_address: "182.254.243.31:30001"
  market:
    md_address: "182.254.243.31:30011"
```

## API参考

### MarketDataService

#### 核心方法

```python
# 服务生命周期
def start() -> bool                              # 启动服务
def stop() -> None                               # 停止服务

# 订阅管理
def subscribe_symbol(symbol: str, subscriber_id: str) -> bool    # 订阅合约
def unsubscribe_symbol(symbol: str, subscriber_id: str) -> bool  # 取消订阅

# 数据访问
def get_latest_tick(symbol: str) -> Optional[TickData]           # 获取最新Tick
def get_market_snapshot() -> MarketSnapshot                      # 获取市场快照
def get_subscription_status() -> Dict[str, List[str]]            # 获取订阅状态

# 回调管理
def add_tick_callback(callback: Callable[[TickData], None])      # 添加Tick回调
def remove_tick_callback(callback: Callable[[TickData], None])   # 移除Tick回调

# 状态监控
def get_status() -> ServiceStatus                                # 获取服务状态
def get_statistics() -> Dict[str, any]                          # 获取统计信息
```

#### 事件处理

```python
# Tick数据处理
def on_tick(tick: TickData) -> None              # 处理Tick数据回调
```

### CtpGatewayWrapper

#### 连接管理

```python
def connect() -> bool                            # 连接CTP服务器
def disconnect() -> None                         # 断开CTP连接

# 状态查询
def is_connected() -> bool                       # 检查连接状态
def is_md_connected() -> bool                    # 检查行情服务器连接
def is_td_connected() -> bool                    # 检查交易服务器连接
```

#### 行情订阅

```python
def subscribe(symbol: str, exchange: str = "SHFE") -> bool       # 订阅合约
def unsubscribe(symbol: str, exchange: str = "SHFE") -> bool     # 取消订阅
```

#### 数据访问

```python
def get_latest_tick(symbol: str, exchange: str = "SHFE") -> Optional[TickData]
def get_contracts() -> Dict[str, ContractData]
def get_ticks() -> Dict[str, TickData]
def get_status_info() -> Dict[str, any]
```

## 示例程序

### 1. 基础演示

运行基础行情订阅演示：

```bash
cd /root/ARBIG
python examples/market_data_demo.py
```

### 2. 完整测试

运行完整的功能测试：

```bash
cd /root/ARBIG
python tests/test_market_data_service.py
```

## 监控和调试

### 1. 日志配置

```python
from utils.logger import get_logger

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)  # 设置调试级别
```

### 2. 状态监控

```python
# 获取服务统计
stats = market_service.get_statistics()
print(f"状态: {stats['status']}")
print(f"订阅合约数: {stats['subscribed_symbols']}")
print(f"缓存Tick数: {stats['cached_ticks']}")

# 获取CTP状态
gateway_stats = ctp_gateway.get_status_info()
print(f"行情连接: {gateway_stats['md_connected']}")
print(f"交易连接: {gateway_stats['td_connected']}")
```

### 3. 性能指标

- **Tick处理延迟**: < 10ms
- **内存使用**: 缓存1000个Tick约占用10MB
- **订阅响应时间**: < 1秒
- **连接恢复时间**: < 30秒

## 故障排除

### 常见问题

#### 1. 连接失败

**问题**: CTP连接超时或失败

**解决方案**:
- 检查网络连接
- 验证账户信息
- 确认服务器地址正确
- 检查防火墙设置

#### 2. 无法收到行情

**问题**: 订阅成功但收不到Tick数据

**解决方案**:
- 确认合约代码正确
- 检查交易时间
- 验证合约是否存在
- 查看CTP日志

#### 3. 内存使用过高

**问题**: 长时间运行后内存占用过大

**解决方案**:
- 调整缓存大小配置
- 定期清理历史数据
- 监控订阅合约数量

### 调试技巧

1. **启用详细日志**:
   ```python
   import logging
   logging.getLogger('core.services.market_data_service').setLevel(logging.DEBUG)
   ```

2. **监控事件流**:
   ```python
   def debug_event_handler(event):
       print(f"事件: {event.type}, 数据: {event.data}")
   
   event_engine.register("TICK_EVENT", debug_event_handler)
   ```

3. **检查连接状态**:
   ```python
   # 定期检查连接
   import time
   while True:
       if not ctp_gateway.is_md_connected():
           print("行情连接断开，尝试重连...")
           ctp_gateway.connect()
       time.sleep(10)
   ```

## 最佳实践

1. **资源管理**: 始终在程序结束时调用 `stop()` 方法
2. **错误处理**: 为所有回调函数添加异常处理
3. **性能优化**: 避免在回调函数中执行耗时操作
4. **监控告警**: 实现连接状态和数据流监控
5. **配置管理**: 使用配置文件管理参数，避免硬编码

## 版本历史

- **v1.0.0** (2025-01-04): 初始版本，支持基础行情订阅功能
- 基于vnpy-ctp实现CTP接口集成
- 支持多客户端订阅管理
- 实现事件驱动的数据分发机制

---

**文档版本**: v1.0  
**最后更新**: 2025-01-04  
**维护者**: ARBIG开发团队
