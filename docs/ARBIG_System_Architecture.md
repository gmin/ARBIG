# ARBIG系统架构设计文档

## 1. 系统整体架构

### 1.1 架构层次
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CTP系统       │    │   交易服务       │    │   策略服务       │    │   具体策略       │
│                 │    │                 │    │                 │    │                 │
│ - 行情推送      │───▶│ - CTP集成       │───▶│ - 策略引擎       │───▶│ - TestStrategy  │
│ - 成交回调      │    │ - 数据存储      │    │ - 数据轮询      │    │ - 其他策略      │
│ - 订单回调      │    │ - API服务       │    │ - 回调分发      │    │                 │
│ - 持仓管理      │    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 1.2 数据流向
- **行情数据**: CTP → 交易服务 → 策略服务 → 策略
- **成交数据**: CTP → 交易服务 → 策略服务 → 策略 → 持仓查询
- **订单数据**: CTP → 交易服务 (暂未传递到策略服务)
- **持仓数据**: CTP → 交易服务 ← 策略服务查询

## 2. 交易服务 (Trading Service)

### 2.1 核心职责
- **CTP接口封装**: 封装vnpy的CTP接口
- **数据存储**: 存储行情、成交、订单、持仓数据
- **API服务**: 提供HTTP API供其他服务调用
- **纯数据提供**: 不包含业务逻辑，只负责数据

### 2.2 CTP集成模块 (ctp_integration.py)

#### 2.2.1 数据存储
```python
class CtpIntegration:
    def __init__(self):
        # 数据存储字典
        self.ticks: Dict[str, TickData] = {}      # 行情数据
        self.trades: Dict[str, TradeData] = {}    # 成交数据
        self.orders: Dict[str, OrderData] = {}    # 订单数据
        self.positions: Dict[str, PositionData] = {} # 持仓数据
        
        # 回调函数列表
        self.tick_callbacks: list[Callable] = []
        self.trade_callbacks: list[Callable] = []
        self.order_callbacks: list[Callable] = []
```

#### 2.2.2 CTP回调处理
```python
def _on_tick(self, event):
    """行情回调"""
    tick = event.data
    logger.info(f"📈📈📈 [交易服务] CTP行情回调被触发！")
    
    # 存储行情数据
    self.ticks[tick.symbol] = tick
    
    # 触发回调链
    for callback in self.tick_callbacks:
        callback(tick)

def _on_trade(self, event):
    """成交回调"""
    trade = event.data
    logger.info(f"🔥🔥🔥 [交易服务] CTP成交回调被触发！")
    logger.info(f"🔥 成交ID: {trade.tradeid}")
    logger.info(f"🔥 订单ID: {trade.orderid}")
    
    # 存储成交数据
    self.trades[trade.tradeid] = trade
    
    # 触发回调链
    for callback in self.trade_callbacks:
        callback(trade)

def _on_order(self, event):
    """订单回调"""
    order = event.data
    logger.info(f"📋📋📋 [交易服务] CTP订单回调被触发！")
    logger.info(f"📋 订单状态: {order.status}")
    
    # 存储订单数据
    self.orders[order.orderid] = order
    
    # 触发回调链
    for callback in self.order_callbacks:
        callback(order)
```

### 2.3 API接口 (real_trading.py)

#### 2.3.1 核心API
```python
# 行情查询
GET /real_trading/tick/{symbol}

# 成交查询 (策略服务轮询使用)
GET /real_trading/trades/{strategy_name}

# 持仓查询 (策略服务查询真实持仓)
GET /real_trading/positions?symbol={symbol}

# 订单提交
POST /real_trading/strategy_signal

# CTP状态查询
GET /real_trading/status
```

#### 2.3.2 数据格式
```python
# 成交数据返回格式
{
    "success": true,
    "data": {
        "strategy_name": "TestStrategy",
        "trades": [
            {
                "trade_id": "12345",
                "order_id": "1_123456_1",
                "symbol": "au2510",
                "direction": "LONG",
                "offset": "OPEN",
                "price": 780.50,
                "volume": 1,
                "datetime": "2025-08-26T14:30:00"
            }
        ],
        "count": 1
    }
}

# 持仓数据返回格式
{
    "success": true,
    "data": {
        "au2510": {
            "long_position": 2,
            "short_position": 0,
            "net_position": 2,
            "current_price": 780.50,
            "total_pnl": 150.0
        }
    }
}
```

## 3. 策略服务 (Strategy Service)

### 3.1 核心职责
- **策略管理**: 注册、启动、停止策略
- **数据轮询**: 从交易服务轮询行情和成交数据
- **回调分发**: 将数据分发给具体策略
- **持仓同步**: 查询并同步真实持仓到策略

### 3.2 策略引擎 (strategy_engine.py)

#### 3.2.1 核心属性
```python
class StrategyEngine:
    def __init__(self):
        # 策略管理
        self.strategies: Dict[str, ARBIGCtaTemplate] = {}  # 策略实例
        self.strategy_configs: Dict[str, Dict[str, Any]] = {}  # 策略配置
        self.active_strategies: List[str] = []  # 活跃策略列表
        
        # 数据处理
        self.processed_trade_ids: set = set()  # 已处理成交ID (去重)
        self.trading_service_url = "http://localhost:8001"  # 交易服务地址
        
        # 线程管理
        self.running = False
        self.data_thread = None
```

#### 3.2.2 简化的数据处理机制
```python
def _data_processing_loop(self):
    """简化的数据处理循环 - 只处理行情数据"""
    while self.running:
        try:
            # 只获取行情数据
            self._fetch_market_data()

            # 🔧 移除成交数据轮询：现在使用实时持仓查询机制
            # 不再需要持续轮询成交数据来维护持仓

            # 休眠1秒
            threading.Event().wait(1.0)
        except Exception as e:
            logger.error(f"数据处理循环异常: {e}")

def _fetch_trade_data(self):
    """🔧 已废弃：成交数据轮询功能

    原因：现在使用实时持仓查询机制，不再需要通过成交数据维护持仓
    - 行情回调专注信号生成
    - 信号处理时主动查询持仓
    - 成交回调用于异步更新缓存（如果需要的话）
    """
    # 🔧 功能已移除：不再轮询成交数据
    pass
```

#### 3.2.3 简化的策略管理
```python
# 🔧 已删除：策略引擎层面的持仓同步机制
# 原因：持仓管理完全由策略自主负责

class StrategyEngine:
    def __init__(self):
        # 策略管理
        self.strategies: Dict[str, ARBIGCtaTemplate] = {}
        self.strategy_configs: Dict[str, Dict[str, Any]] = {}
        self.active_strategies: List[str] = []

        # 🔧 已删除：processed_trade_ids - 不再需要成交去重
        # 🔧 已删除：成交数据处理相关的所有方法

    # 核心功能：只保留策略生命周期管理
    def register_strategy(self, strategy_name, strategy_type, symbol, params)
    def start_strategy(self, strategy_name)
    def stop_strategy(self, strategy_name)
```

#### 3.2.4 策略匹配逻辑
```python
def _match_order_to_strategy(self, order_id: str) -> Optional[str]:
    """通过订单ID匹配到策略名称"""
    try:
        # 简化匹配：单策略环境下直接匹配
        if len(self.active_strategies) == 1:
            strategy_name = self.active_strategies[0]
            logger.info(f"🎯 单策略匹配: {order_id} -> {strategy_name}")
            return strategy_name

        # TODO: 多策略环境下的复杂匹配逻辑
        # 可以通过订单ID格式、策略名称映射等方式实现

        return None

    except Exception as e:
        logger.warning(f"订单匹配失败: {e}")
        return None
```

### 3.3 API接口 (strategy_api.py)

#### 3.3.1 策略管理API
```python
# 注册策略
POST /strategies/register
{
    "strategy_name": "TestStrategy",
    "strategy_type": "TestStrategy",
    "symbol": "au2510",
    "params": {
        "signal_interval": 15,
        "trade_volume": 1,
        "max_position": 2
    }
}

# 启动策略
POST /strategies/{strategy_name}/start

# 停止策略
POST /strategies/{strategy_name}/stop

# 查询策略状态
GET /strategies/{strategy_name}

# 查询所有策略
GET /strategies
```

## 4. 策略基类 (ARBIGCtaTemplate)

### 4.1 核心职责
- **策略生命周期管理**: 初始化、启动、停止
- **数据回调处理**: 行情回调、成交回调
- **交易信号生成**: 调用具体策略的实现方法
- **风控检查**: 持仓限制、风险控制

### 4.2 核心属性
```python
class ARBIGCtaTemplate:
    def __init__(self, strategy_name: str, symbol: str, params: dict):
        # 策略基本信息
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.params = params

        # 交易状态
        self.pos = 0  # 当前持仓 (由策略引擎从CTP查询更新)
        self.active = False
        self.trading = True

        # 数据存储
        self.trades: Dict[str, TradeData] = {}  # 成交记录
        self.ticks: Dict[str, TickData] = {}    # 行情记录

        # 策略参数
        self.max_position = params.get('max_position', 2)
        self.trade_volume = params.get('trade_volume', 1)
```

### 4.3 优化的回调处理机制
```python
def on_tick(self, tick: TickData):
    """🎯 纯净的行情回调 - 专注信号生成"""
    logger.info(f"📈 收到tick数据: {tick.symbol} 价格={tick.last_price}")

    # 存储行情数据
    self.ticks[tick.symbol] = tick

    # 🎯 专注核心职责：生成交易信号
    try:
        self._generate_trading_signal(tick)
    except Exception as e:
        logger.error(f"策略 {self.strategy_name} 信号生成异常: {e}")

def on_order(self, order: OrderData):
    """📋 简化的订单回调 - 只关注关键状态"""
    # 只记录重要的订单状态变化
    if hasattr(order, 'status'):
        status = order.status.value
        if status in ["ALLTRADED", "REJECTED", "CANCELLED"]:
            logger.info(f"📋 订单状态: {order.orderid} - {status}")

            # 拒单时的特殊处理
            if status == "REJECTED":
                logger.warning(f"⚠️ 订单被拒绝，可能需要检查资金或持仓限制")
                self.signal_lock = False  # 解除信号锁定

def on_trade(self, trade: TradeData):
    """🔥 成交回调 - 异步更新持仓缓存"""
    logger.info(f"🔥 成交确认: {trade.direction} {trade.volume}手 @ {trade.price}")

    # 🔧 异步更新持仓缓存，不阻塞成交处理
    self._update_position_cache_after_trade()

    # 调用具体策略实现
    try:
        self.on_trade_impl(trade)
    except Exception as e:
        logger.error(f"策略 {self.strategy_name} 成交处理异常: {e}")
```

### 4.4 实时持仓查询机制
```python
def _query_real_position(self) -> Optional[int]:
    """实时查询真实持仓"""
    try:
        import requests

        # 查询交易服务的持仓API
        response = requests.get(
            f"http://localhost:8001/real_trading/positions?symbol={self.symbol}",
            timeout=2.0
        )

        if response.status_code == 200:
            position_data = response.json()
            if position_data.get("success") and position_data.get("data"):
                positions = position_data["data"]

                # 获取净持仓
                if self.symbol in positions:
                    net_position = positions[self.symbol].get("net_position", 0)
                    self.write_log(f"🔍 查询到真实持仓: {net_position}")
                    return net_position
                else:
                    self.write_log(f"🔍 合约 {self.symbol} 无持仓")
                    return 0
            else:
                self.write_log(f"⚠️ 持仓查询返回空数据")
                return None
        else:
            self.write_log(f"⚠️ 持仓查询失败: HTTP {response.status_code}")
            return None

    except Exception as e:
        self.write_log(f"⚠️ 持仓查询异常: {e}")
        return None
```

### 4.5 分离式信号生成和风控机制
```python
def _generate_trading_signal(self, tick: TickData):
    """🎯 纯净的交易信号生成 - 只生成信号，不执行交易"""
    current_price = tick.last_price

    # 🚨 信号生成前置检查
    if self.signal_lock:
        self.write_log(f"🔒 信号生成被锁定，等待交易完成")
        return

    # 🎯 核心逻辑1：分析市场条件
    market_analysis = self._analyze_market_conditions(tick)

    # 🎯 核心逻辑2：生成交易决策
    signal_decision = self._make_trading_decision(market_analysis, current_price)

    # 🎯 核心逻辑3：发送信号（不执行交易）
    if signal_decision['action'] in ['BUY', 'SELL']:
        self.write_log(f"🎯 生成交易信号: {signal_decision['action']} - {signal_decision['reason']}")
        # 🔧 发送信号给信号处理模块，而不是直接执行
        self._send_trading_signal(signal_decision, current_price)
    else:
        self.write_log(f"🎯 无交易信号: {signal_decision['reason']}")

def _process_trading_signal(self, signal_decision: dict, current_price: float):
    """🔧 信号处理模块 - 主动查询持仓并执行交易"""
    action = signal_decision['action']

    self.write_log(f"🔧 信号处理模块：接收到{action}信号，开始处理")

    # 🔧 主动查询持仓进行风控检查
    if not self._pre_trade_safety_check():
        self.write_log(f"🔧 信号处理模块：风控检查未通过，信号被拒绝")
        return

    # 🎯 风控通过，执行交易订单
    self.write_log(f"🔧 信号处理模块：风控通过，执行{action}订单")
    if action == 'BUY':
        self.buy(current_price, self.trade_volume, stop=False)
    elif action == 'SELL':
        self.sell(current_price, self.trade_volume, stop=False)

def _pre_trade_safety_check(self) -> bool:
    """🔧 交易前安全检查 - 独立的持仓风控模块"""
    real_position = self._query_real_position()
    if real_position is None:
        self.write_log(f"⚠️ 无法查询持仓，停止交易")
        return False

    # 更新持仓缓存
    if real_position != self.cached_position:
        self.write_log(f"🔄 持仓同步: {self.cached_position} → {real_position}")
        self.cached_position = real_position
        self.pos = real_position

    # 风控检查
    predicted_position = abs(real_position + self.trade_volume)
    if predicted_position > self.max_position:
        self.write_log(f"⚠️ 风控阻止: 当前={real_position}, 预测={predicted_position}, 限制={self.max_position}")
        return False

    return True
```

## 5. 具体策略实现 (TestStrategy)

### 5.1 策略逻辑
```python
class TestStrategy(ARBIGCtaTemplate):
    def __init__(self, strategy_name: str, symbol: str, params: dict):
        super().__init__(strategy_name, symbol, params)

        # 策略特定参数
        self.signal_interval = params.get('signal_interval', 15)
        self.last_signal_time = 0

    def on_tick_impl(self, tick: TickData):
        """具体策略的行情处理逻辑"""
        current_time = time.time()

        # 信号间隔控制
        if current_time - self.last_signal_time < self.signal_interval:
            return

        # 风控检查
        if not self.check_risk_control(tick.last_price):
            return

        # 生成交易信号 (简化逻辑)
        if self.pos == 0:
            # 无持仓时买入
            self.buy(tick.last_price, self.trade_volume)
            self.last_signal_time = current_time

    def on_trade_impl(self, trade: TradeData):
        """具体策略的成交处理逻辑"""
        logger.info(f"🔥 子类 - 成交详情: {trade.direction} {trade.volume}手 @ {trade.price}")
        logger.info(f"🔥 子类 - 当前持仓: {self.pos}")

        # 策略特定的成交处理逻辑
        # 注意: self.pos 已经由策略引擎从CTP查询更新，不需要自己计算
```

## 6. 关键设计原则

### 6.1 数据流原则
- **单向流动**: 数据只能从CTP → 交易服务 → 策略服务 → 策略
- **不逆向查询**: 策略不直接访问CTP，通过服务层获取数据
- **分层解耦**: 每层只关心自己的职责，不越界处理

### 6.2 简化的数据处理机制
- **交易服务层**: 存储所有原始数据，提供查询API
- **策略服务层**: 🔧 已简化 - 移除成交数据轮询和去重机制
- **策略层**: 🔧 已优化 - 主动查询持仓，不依赖成交数据累加

### 6.3 优化的持仓管理原则
- **策略自主管理**: 策略完全自主负责持仓查询和管理
- **实时查询**: 交易前实时查询CTP的真实持仓数据
- **安全第一**: 宁可有延迟，也要确保持仓数据准确
- **缓存机制**:
  - 持仓缓存：减少频繁查询的性能开销
  - 按需查询：只在交易前和接近上限时查询
  - 异步更新：成交后异步更新缓存，不阻塞处理
- **职责分离**: 策略引擎不再参与持仓管理，专注策略生命周期

### 6.4 错误处理原则
- **分层异常处理**: 每层都有独立的异常处理机制
- **不中断服务**: 单个回调失败不影响整体服务运行
- **详细日志**: 每个关键环节都有详细的调试日志
- **优雅降级**: 出现问题时能够优雅降级，不崩溃

## 7. 配置参数

### 7.1 系统配置
```python
# 服务地址
TRADING_SERVICE_URL = "http://localhost:8001"
STRATEGY_SERVICE_URL = "http://localhost:8002"

# 轮询配置
POLLING_INTERVAL = 1.0  # 数据轮询间隔(秒)
HTTP_TIMEOUT = 2.0      # HTTP请求超时(秒)

# 去重配置
MAX_PROCESSED_TRADES = 10000  # 最大已处理成交ID数量

# 日志配置
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### 7.2 策略配置
```python
# TestStrategy默认配置
DEFAULT_STRATEGY_CONFIG = {
    "signal_interval": 15,    # 信号间隔(秒)
    "trade_volume": 1,        # 交易手数
    "max_position": 2,        # 最大持仓
    "symbol": "au2510"        # 交易合约
}
```

## 8. 时序图

### 8.1 成交处理完整流程
```
时间轴: 成交发生时的完整数据流

CTP系统     交易服务     策略服务     策略引擎     具体策略
   |           |           |           |           |
   |--成交-->  |           |           |           |
   |           |--存储-->  |           |           |
   |           |           |<--轮询--  |           |
   |           |--返回-->  |           |           |
   |           |           |--解析-->  |           |
   |           |           |--去重-->  |           |
   |           |           |--匹配-->  |           |
   |           |           |--创建TradeData--> |   |
   |           |           |--分发-->  |--回调--> |
   |           |<--持仓查询-|           |           |
   |           |--持仓数据->|           |           |
   |           |           |--更新pos->|           |
```

### 8.2 优化后的交易信号生成流程
```
时间轴: 简化的信号生成和执行流程

CTP系统     交易服务     策略服务     具体策略
   |           |           |           |
   |           |           |<--tick--  |
   |           |           |           |--信号生成
   |           |           |           |--信号处理
   |           |<--持仓查询-|           |
   |           |--持仓数据->|           |
   |           |           |           |--持仓同步
   |           |           |           |--风控检查
   |           |           |           |--发出订单
   |<--订单--  |           |           |
   |--成交-->  |           |           |
   |           |--存储-->  |           |
   |           |           |           |--成交确认
   |           |<--持仓查询-|           | (异步缓存更新)
   |           |--持仓数据->|           |
```

### 8.3 架构简化对比
```
优化前：复杂的数据流
CTP → 交易服务 → 策略服务轮询 → 成交匹配 → 策略分发 → 持仓更新

优化后：简洁的数据流
CTP → 交易服务 ← 策略主动查询 ← 策略信号处理 ← 行情回调
```

---

**文档版本**: v2.0
**创建时间**: 2025-08-26
**最后更新**: 2025-08-26 (重大架构优化：简化回调系统，移除成交数据轮询)

## 版本更新记录

### v2.0 (2025-08-26) - 重大架构优化
- **🔧 移除成交数据轮询**: 不再轮询成交数据，大幅减少HTTP请求
- **🎯 行情回调纯净化**: 专注信号生成，不掺杂持仓查询逻辑
- **📋 订单回调简化**: 只处理关键状态（REJECTED, CANCELLED, ALLTRADED）
- **🔧 策略自主持仓管理**: 策略完全自主负责持仓查询和风控
- **⚡ 性能大幅提升**: 删除200+行复杂处理代码，系统更简洁高效

### v1.1 (2025-08-26) - 实时持仓查询
- 添加实时持仓查询机制
- 实现安全风控检查

### v1.0 (2025-08-26) - 初始版本
- 完整的系统架构设计
- 四层架构：CTP → 交易服务 → 策略服务 → 策略
