# ARBIG Web指挥中轴架构设计文档

## 📋 文档信息

- **文档版本**: v1.0
- **创建日期**: 2025-01-04
- **最后更新**: 2025-01-04
- **作者**: ARBIG开发团队

## 🎯 设计目标

将ARBIG系统重构为**Web指挥中轴**架构，实现：
- Web界面成为系统的统一控制中心
- main.py转变为纯粹的服务容器
- 用户通过Web界面完成所有操作和监控

## 🏗️ 架构概览

### 传统架构 vs 新架构

#### ❌ 传统架构（当前）
```
main.py (主控制器)
    ├── 启动所有服务
    ├── 管理服务生命周期
    ├── 处理策略逻辑
    └── Web仅作为监控界面
```

#### ✅ 新架构（Web指挥中轴）
```
Web指挥中轴 (控制中心)
    ├── 系统控制台
    ├── 实时监控
    ├── 策略管理
    ├── 数据分析
    └── 用户交互
         │
         ▼ (API调用)
main.py (服务容器)
    ├── 服务管理器
    ├── API提供者
    ├── 状态报告器
    └── 命令执行器
         │
         ▼
核心服务层
    ├── MarketDataService
    ├── AccountService
    ├── RiskService
    └── TradingService
         │
         ▼
CTP Gateway
```

## 🎮 Web指挥中轴功能模块

### 1. 系统控制台
**职责**: 系统级操作和控制

**功能列表**:
- ✅ 服务启动/停止/重启
- ✅ 运行模式切换
- ✅ 系统参数配置
- ✅ 紧急停止/平仓
- ✅ 系统状态监控

**界面组件**:
```
┌─────────────────┐
│   系统控制台    │
│ ○ 行情服务      │
│ ○ 账户服务      │
│ ○ 风控服务      │
│ ○ 交易服务      │
│                 │
│ 运行模式: 完整  │
│ [切换模式]      │
│                 │
│ [紧急停止]      │
│ [紧急平仓]      │
└─────────────────┘
```

### 2. 实时行情监控
**职责**: 行情数据展示和分析

**功能列表**:
- ✅ 实时K线图表
- ✅ 实时价格显示
- ✅ 成交量分析
- ✅ 技术指标展示
- ✅ 多合约监控

**界面组件**:
```
┌─────────────────────────────────────┐
│              实时行情               │
│ ┌─────────────────────────────────┐ │
│ │         K线图表区域             │ │
│ │                                 │ │
│ │                                 │ │
│ └─────────────────────────────────┘ │
│ AU2509: 485.50 ↑2.30 (+0.48%)     │
│ 成交量: 12,580  持仓: 45,230       │
└─────────────────────────────────────┘
```

### 3. 仓位管理中心
**职责**: 账户和持仓信息管理

**功能列表**:
- ✅ 账户资金展示
- ✅ 持仓明细管理
- ✅ 盈亏统计分析
- ✅ 风险指标监控
- ✅ 历史交易记录

**界面组件**:
```
┌─────────────────────────────┐ ┌─────────────────────────┐
│         账户资金            │ │        持仓明细         │
│ 总资产: ¥1,000,000         │ │ AU2509 多5手            │
│ 可用: ¥850,000             │ │ 均价: 483.20            │
│ 保证金: ¥150,000           │ │ 现价: 485.50            │
│ 浮盈: ¥25,000              │ │ 盈亏: +¥11,500          │
│ 今日盈亏: +¥5,000          │ │ 保证金: ¥120,000        │
└─────────────────────────────┘ └─────────────────────────┘
```

### 4. 策略管理中心
**职责**: 策略的全生命周期管理

**功能列表**:
- ✅ 策略选择和切换
- ✅ 策略参数配置
- ✅ 策略运行监控
- ✅ 策略绩效分析
- ✅ 策略历史回测

**界面组件**:
```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   策略选择      │ │   策略监控      │ │   策略分析      │
│ ○ 趋势策略      │ │ 当前: 套利策略  │ │ 今日收益: +2.3% │
│ ● 套利策略      │ │ 运行: 2h30m     │ │ 最大回撤: -1.2% │
│ ○ 高频策略      │ │ 信号: 15        │ │ 胜率: 68.5%     │
│ ○ 无策略        │ │ 成交: 8         │ │ 夏普: 1.85      │
│                 │ │                 │ │                 │
│ [切换策略]      │ │ [暂停策略]      │ │ [详细报告]      │
│ [策略参数]      │ │ [重启策略]      │ │ [历史回测]      │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 5. 数据分析中心
**职责**: 历史数据分析和报告生成

**功能列表**:
- ✅ 交易绩效分析
- ✅ 风险指标计算
- ✅ 历史数据回测
- ✅ 报表生成导出
- ✅ 数据可视化

## 🔧 main.py重构设计

### 新的职责定位
main.py从**主控制器**转变为**服务容器**：

```python
class ARBIGServiceContainer:
    """ARBIG服务容器 - 纯粹的服务管理器"""
    
    def __init__(self):
        """初始化服务容器"""
        self.services = {}
        self.ctp_gateway = None
        self.event_engine = None
        self.running = False
        
    # 服务管理接口
    def start_service(self, service_name: str) -> ServiceResult
    def stop_service(self, service_name: str) -> ServiceResult
    def restart_service(self, service_name: str) -> ServiceResult
    def get_service_status(self, service_name: str) -> ServiceStatus
    
    # 系统管理接口
    def start_system(self) -> SystemResult
    def stop_system(self) -> SystemResult
    def get_system_status(self) -> SystemStatus
    
    # 命令执行接口
    def execute_command(self, command: Command) -> CommandResult
    
    # 配置管理接口
    def update_config(self, config: dict) -> ConfigResult
    def get_config(self) -> dict
```

### 服务启动策略
```python
def start_service(self, service_name: str) -> ServiceResult:
    """启动指定服务"""
    
    # 1. 检查依赖关系
    if not self._check_dependencies(service_name):
        return ServiceResult(False, "依赖服务未启动")
    
    # 2. 检查前置条件
    if not self._check_prerequisites(service_name):
        return ServiceResult(False, "前置条件不满足")
    
    # 3. 启动服务
    try:
        service = self._create_service(service_name)
        if service.start():
            self.services[service_name] = service
            return ServiceResult(True, f"{service_name}启动成功")
        else:
            return ServiceResult(False, f"{service_name}启动失败")
    except Exception as e:
        return ServiceResult(False, f"{service_name}启动异常: {e}")
```

## 🌐 Web API设计

### 1. 服务控制API
```python
# 服务管理
POST /api/services/start          # 启动服务
POST /api/services/stop           # 停止服务
POST /api/services/restart        # 重启服务
GET  /api/services/status         # 获取服务状态
GET  /api/services/list           # 获取服务列表

# 系统管理
POST /api/system/start            # 启动系统
POST /api/system/stop             # 停止系统
POST /api/system/mode             # 切换运行模式
GET  /api/system/status           # 获取系统状态
```

### 2. 策略管理API
```python
# 策略控制
GET  /api/strategies/list         # 获取策略列表
GET  /api/strategies/current      # 获取当前策略
POST /api/strategies/switch       # 切换策略
POST /api/strategies/pause        # 暂停策略
POST /api/strategies/resume       # 恢复策略

# 策略配置
GET  /api/strategies/{name}/config    # 获取策略配置
POST /api/strategies/{name}/config    # 更新策略配置
GET  /api/strategies/{name}/stats     # 获取策略统计
```

### 3. 数据查询API
```python
# 行情数据
GET  /api/market/ticks            # 获取实时行情
GET  /api/market/klines           # 获取K线数据
GET  /api/market/symbols          # 获取合约列表

# 账户数据
GET  /api/account/info            # 获取账户信息
GET  /api/account/positions       # 获取持仓信息
GET  /api/account/orders          # 获取订单信息
GET  /api/account/trades          # 获取成交信息

# 风控数据
GET  /api/risk/metrics            # 获取风险指标
GET  /api/risk/limits             # 获取风控限制
POST /api/risk/limits             # 更新风控限制
```

### 4. 实时通信API
```python
# WebSocket连接
WS   /ws/market                   # 实时行情推送
WS   /ws/account                  # 账户变动推送
WS   /ws/orders                   # 订单状态推送
WS   /ws/system                   # 系统状态推送
```

## 📊 数据流设计

### 实时数据流
```
CTP Gateway → 核心服务 → 数据缓存 → WebSocket → Web界面
```

### 控制指令流
```
Web界面 → HTTP API → main.py → 核心服务 → CTP Gateway
```

### 状态同步流
```
核心服务 ←→ main.py ←→ Web界面
```

## 🔄 服务依赖关系

### 依赖图
```
CTP Gateway (基础)
    ↓
MarketDataService ← CTP Gateway (必须)
AccountService ← CTP Gateway (必须)
    ↓
RiskService ← AccountService (必须)
    ↓
TradingService ← MarketDataService + AccountService + RiskService + CTP Gateway (全部必须)
```

### 启动顺序
```
1. ConfigManager
2. CTP Gateway
3. EventEngine
4. MarketDataService
5. AccountService (如果有交易连接)
6. RiskService (如果AccountService成功)
7. TradingService (如果所有前置服务成功)
```

## 🎯 运行模式设计

### 模式定义
- **FULL_TRADING**: 完整交易模式 - 所有服务正常
- **MONITOR_ONLY**: 仅监控模式 - 有行情和账户，无交易
- **MARKET_DATA_ONLY**: 仅行情模式 - 只有行情数据

### 模式切换
用户可以通过Web界面主动切换运行模式，系统也会根据服务状态自动调整模式。

## 📝 实施计划

### 第一阶段：架构重构
1. 重构main.py为服务容器
2. 设计Web控制API
3. 实现基础的服务控制功能

### 第二阶段：Web界面开发
1. 开发系统控制台
2. 实现实时监控界面
3. 集成数据展示功能

### 第三阶段：策略管理
1. 实现策略切换功能
2. 开发策略配置界面
3. 集成策略分析功能

### 第四阶段：数据分析
1. 实现历史数据分析
2. 开发报表生成功能
3. 完善数据可视化

## 🔒 安全考虑

### 访问控制
- 用户认证和授权
- 操作权限分级
- 敏感操作确认

### 操作审计
- 完整的操作日志
- 用户行为追踪
- 系统变更记录

### 数据安全
- 敏感数据加密
- 安全的API通信
- 数据备份和恢复

---

**下一步**: 基于此设计文档，开始实施第一阶段的架构重构工作。
