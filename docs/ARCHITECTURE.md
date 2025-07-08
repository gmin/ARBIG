# ARBIG 系统架构文档

## 📋 文档信息

- **版本**: v2.0
- **更新日期**: 2025-01-09
- **架构变更**: Web管理系统重构

## 🎯 架构概述

ARBIG 采用现代化的 Web 管理架构，将系统分为三个核心层次：

1. **Web管理层** (`web_admin`) - 用户交互界面
2. **API服务层** (`trading_api`) - 业务接口服务  
3. **核心系统层** (`core`) - 交易引擎和服务

## 🏗️ 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    ARBIG 量化交易系统                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │   web_admin     │    │   trading_api   │                │
│  │   🎛️ Web管理系统 │◄──►│   🔧 交易API服务 │                │
│  │                 │    │                 │                │
│  │ • 交易管理       │    │ • 交易接口       │                │
│  │ • 风控管理       │    │ • 账户接口       │                │
│  │ • 系统监控       │    │ • 行情接口       │                │
│  │ • 信号监控       │    │ • 风控接口       │                │
│  │ • 历史记录       │    │                 │                │
│  └─────────────────┘    └─────────────────┘                │
│           │                       │                        │
│           └───────────┬───────────┘                        │
│                       ▼                                    │
│              ┌─────────────────┐                           │
│              │      core       │                           │
│              │   ⚙️ 核心系统    │                           │
│              │                 │                           │
│              │ • EventEngine   │                           │
│              │ • Services      │                           │
│              │ • CTP Gateway   │                           │
│              │ • Strategy      │                           │
│              └─────────────────┘                           │
│                       │                                    │
│                       ▼                                    │
│              ┌─────────────────┐                           │
│              │   外部接口       │                           │
│              │                 │                           │
│              │ • CTP仿真盘      │                           │
│              │ • 数据库        │                           │
│              │ • 日志系统      │                           │
│              └─────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

## 📦 模块详细说明

### 1. Web管理系统 (`web_admin/`)

**功能定位**: 用户交互界面，提供完整的交易管理功能

#### 核心组件

```
web_admin/
├── app.py                  # FastAPI主应用
├── static/                 # 静态资源
│   └── index.html         # 主界面
├── system_monitor.py       # 系统监控模块
├── trading_monitor.py      # 交易监控模块
├── risk_controller.py      # 风控控制器
├── data_provider.py        # 数据提供者
└── models.py              # 数据模型
```

#### 主要功能

**🎛️ 交易管理**
- 手动下单界面
- 订单状态监控
- 持仓实时查看
- 账户资金查询

**🛡️ 风控管理**
- 紧急暂停交易 (`emergencyHalt()`)
- 一键平仓功能 (`emergencyClose()`)
- 策略暂停控制 (`haltStrategy()`)
- 风险参数调整

**📊 系统监控**
- 服务状态监控 (CTP连接、各服务状态)
- 性能指标监控 (CPU、内存、延时)
- 连接质量监控 (网络状态、重连次数)

**📈 信号监控**
- 交易信号记录 (`record_trading_signal()`)
- 信号执行跟踪 (`link_order_to_signal()`)
- 信号分析统计 (`get_signal_analysis()`)
- 策略表现评估

**📋 历史记录**
- 操作日志记录
- 交易历史查询
- 风控操作审计
- 系统事件日志

#### 技术特点

- **实时通信**: WebSocket推送实时数据
- **响应式设计**: 支持桌面和移动端访问
- **安全控制**: 重要操作需要确认码
- **模块化设计**: 各功能模块独立可扩展

### 2. 交易API服务 (`trading_api/`)

**功能定位**: 业务接口服务，提供标准化的API接口

#### 核心组件

```
trading_api/
└── app.py                 # FastAPI应用，包含所有API接口
```

#### API接口分类

**🔧 交易接口**
- `POST /api/orders` - 下单接口
- `DELETE /api/orders/{order_id}` - 撤单接口
- `GET /api/orders` - 订单查询
- `GET /api/trades` - 成交查询

**💰 账户接口**
- `GET /api/account` - 账户信息查询
- `GET /api/positions` - 持仓查询
- `GET /api/balance` - 资金查询

**📈 行情接口**
- `GET /api/market_data` - 实时行情
- `GET /api/ticks/{symbol}` - 历史Tick数据
- `GET /api/klines/{symbol}` - K线数据

**🛡️ 风控接口**
- `POST /api/risk/emergency_halt` - 紧急暂停
- `POST /api/risk/emergency_close` - 紧急平仓
- `GET /api/risk/metrics` - 风险指标

#### 技术特点

- **RESTful设计**: 标准的REST API接口
- **异步处理**: 基于FastAPI的异步架构
- **数据验证**: Pydantic模型验证
- **错误处理**: 统一的错误响应格式

### 3. 核心系统 (`core/`)

**功能定位**: 交易引擎和业务逻辑核心

#### 核心组件

```
core/
├── event_engine.py         # 事件引擎
├── config_manager.py       # 配置管理
├── types.py               # 数据类型定义
├── services/              # 业务服务
│   ├── market_data_service.py    # 行情服务
│   ├── account_service.py        # 账户服务
│   ├── trading_service.py        # 交易服务
│   └── risk_service.py           # 风控服务
├── ctp/                   # CTP相关
└── mt5/                   # MT5相关
```

#### 服务架构

**⚡ 事件引擎 (`EventEngine`)**
- 高性能事件处理
- 异步事件分发
- 事件持久化存储

**📊 行情服务 (`MarketDataService`)**
- 实时行情接收
- 数据清洗和验证
- 行情数据分发

**💼 账户服务 (`AccountService`)**
- 账户信息管理
- 持仓数据维护
- 资金状态跟踪

**🔄 交易服务 (`TradingService`)**
- 订单生命周期管理
- 交易执行引擎
- 成交数据处理

**🛡️ 风控服务 (`RiskService`)**
- 实时风险监控
- 风控规则引擎
- 紧急处置机制

## 🔄 数据流架构

### 1. 行情数据流

```
CTP仿真盘 → CTP Gateway → MarketDataService → EventEngine → Web管理系统
                                    ↓
                              TradingService (策略计算)
                                    ↓
                              订单生成 → 风控检查 → 下单执行
```

### 2. 交易信号流

```
策略引擎 → 信号生成 → TradingMonitor.record_trading_signal()
                              ↓
                        订单创建 → link_order_to_signal()
                              ↓
                        Web界面显示 → 信号分析统计
```

### 3. 风控数据流

```
实时监控 → RiskService → 风险评估 → 风控决策
                              ↓
                        Web界面展示 ← SystemMonitor
                              ↓
                        人工干预 → RiskController → 执行操作
```

## 🔧 技术栈

### 后端技术
- **Python 3.8+**: 主要开发语言
- **FastAPI**: Web框架和API服务
- **VNPy**: 量化交易框架
- **Uvicorn**: ASGI服务器
- **WebSockets**: 实时通信
- **Pydantic**: 数据验证
- **AsyncIO**: 异步编程

### 前端技术
- **HTML5/CSS3**: 界面结构和样式
- **JavaScript ES6+**: 交互逻辑
- **WebSocket API**: 实时数据通信
- **Chart.js**: 数据可视化
- **Bootstrap**: 响应式布局

### 数据存储
- **SQLite**: 本地数据存储
- **JSON**: 配置文件格式
- **JSONL**: 事件日志存储

### 外部接口
- **CTP API**: 期货交易接口
- **SimNow**: CTP仿真环境

## 🚀 部署架构

### 开发环境
```bash
# 启动Web管理系统
python -m web_admin.app

# 启动交易API服务  
python -m trading_api.app

# 统一启动脚本
python start_arbig.py
```

### 生产环境
```bash
# 使用Supervisor管理进程
supervisord -c deploy/supervisor.conf

# 使用Nginx反向代理
nginx -c deploy/nginx.conf

# 使用Docker容器化部署
docker-compose up -d
```

## 📈 性能特点

### 高性能设计
- **事件驱动**: 基于事件的异步架构
- **内存优化**: 高效的数据结构设计
- **连接池**: 数据库连接复用
- **缓存机制**: 热点数据缓存

### 可扩展性
- **模块化**: 各组件独立可扩展
- **微服务**: 可拆分为独立服务
- **水平扩展**: 支持多实例部署
- **插件化**: 策略和服务可插拔

### 可靠性
- **故障恢复**: 自动重连和恢复机制
- **数据一致性**: 事务保证和数据校验
- **监控告警**: 全方位系统监控
- **日志审计**: 完整的操作日志

## 🔄 架构演进

### v1.0 → v2.0 主要变化

**架构重构**
- `web_monitor` → `web_admin` (更准确的命名)
- `web_service` → `trading_api` (功能导向命名)
- 引入三层架构设计

**功能增强**
- 新增交易信号监控系统
- 完善风控管理功能
- 增强系统监控能力
- 优化用户交互界面

**技术升级**
- 统一启动脚本 (`start_arbig.py`)
- 模块化设计优化
- 导入路径标准化
- 文档结构重组

## 🎯 未来规划

### 短期目标 (1-3个月)
- [ ] 完善策略回测系统
- [ ] 增加更多技术指标
- [ ] 优化Web界面体验
- [ ] 增强移动端支持

### 中期目标 (3-6个月)  
- [ ] 支持多账户管理
- [ ] 实现策略市场
- [ ] 增加机器学习策略
- [ ] 云端部署支持

### 长期目标 (6-12个月)
- [ ] 多资产类别支持
- [ ] 分布式架构升级
- [ ] 智能风控系统
- [ ] 社区生态建设

---

*本文档将随着系统架构的演进持续更新*
