# ARBIG 项目结构说明

## 项目概述

ARBIG (Algorithmic Real-time Basis Investment Gateway) 是一个专业的量化交易系统，专注于上海期货交易所(SHFE)的黄金期货交易。

## 核心架构

本项目采用**微服务架构**，主要包含以下服务：

### 🏗️ 微服务组件

```
services/
├── trading_service/        # 交易服务 (端口: 8001)
│   ├── main.py            # 服务入口
│   ├── api/               # API路由
│   │   ├── trading.py     # 交易操作API
│   │   ├── market_data.py # 行情数据API
│   │   ├── real_trading.py # 真实交易API
│   │   └── logs.py        # 交易日志API
│   └── core/              # 核心功能
│       ├── ctp_integration.py    # CTP集成
│       ├── market_data_manager.py # 行情管理
│       └── unified_strategy_manager.py # 统一策略管理
│
├── strategy_service/       # 策略服务 (端口: 8002)
│   ├── main.py            # 服务入口
│   ├── core/              # 策略引擎核心
│   │   ├── strategy_engine.py    # 策略执行引擎
│   │   ├── cta_template.py       # vnpy风格策略基类
│   │   ├── data_tools.py         # 数据工具(K线生成、技术指标)
│   │   ├── signal_sender.py      # 信号发送器
│   │   └── framework/            # 策略框架组件
│   │       ├── decision_engine.py   # 决策引擎
│   │       └── signal_generator.py  # 信号生成器
│   └── strategies/        # 策略实现
│       ├── test_strategy.py          # 测试策略
│       ├── double_ma_strategy.py     # 双均线策略
│       ├── simple_shfe_strategy.py   # 简化SHFE策略
│       ├── shfe_quant_strategy.py    # 量化策略
│       └── advanced_shfe_strategy.py # 高级策略(使用框架组件)
│
└── web_admin_service/      # Web管理服务 (端口: 80)
    ├── main.py            # 服务入口
    ├── api/               # API代理
    │   └── trading.py     # 交易API代理
    ├── static/            # 静态资源
    │   ├── js/           # JavaScript文件
    │   └── css/          # 样式文件
    └── templates/         # HTML模板
        ├── index.html     # 主页面
        ├── trading.html   # 交易管理页面
        └── strategy.html  # 策略管理页面
```

### 🧠 核心模块

```
core/
├── config_manager.py      # 配置管理
├── constants.py           # 常量定义
├── event_bus.py           # 事件总线
├── event_engine.py        # 事件引擎
├── position_manager.py    # 持仓管理
├── risk.py               # 风险管理
├── types.py              # 数据类型定义
├── services_archive/     # 已清理的旧服务代码
└── legacy_archive/       # 已清理的遗留代码
```

### 🛠️ 支撑模块

```
shared/                   # 共享模块
├── models/              # 数据模型
├── utils/               # 工具类
└── database/            # 数据库相关

utils/                   # 工具函数
├── logger.py           # 日志工具
└── [其他工具]

config/                  # 配置文件
├── config.py           # 主配置
├── ctp_sim.json        # CTP仿真配置
├── database.json       # 数据库配置
└── strategies.json     # 策略配置

gateways/               # 交易网关
└── ctp_gateway.py      # CTP网关实现
```

## 📚 文档结构

```
docs/
├── README.md                    # 文档总览
├── CURRENT_ARCHITECTURE.md     # 当前架构说明
├── USER_MANUAL.md              # 用户手册
├── WEB_UI_DESIGN.md            # Web界面设计
├── DEPLOYMENT_GUIDE.md         # 部署指南
├── API_REFERENCE.md            # API参考
├── position_management.md      # 持仓管理说明
├── technical/                  # 技术文档
│   ├── DATABASE_CONNECTION_SUMMARY.md
│   ├── DATABASE_INFO.md
│   └── DATA_INFRASTRUCTURE_SUMMARY.md
├── maintenance/                # 维护文档
│   ├── CORE_CLEANUP_SUMMARY.md
│   ├── STRATEGY_MIGRATION_SUMMARY.md
│   └── [其他维护记录]
├── strategies/                 # 策略文档
└── archive/                    # 历史文档
    └── [已过时的文档]
```

## 🚀 启动方式

### 开发环境启动
```bash
# 方式1: 带日志的启动脚本
./start_with_logs.py

# 方式2: 基础启动脚本
python start.py

# 方式3: 手动启动各服务
cd services/trading_service && conda run -n vnpy uvicorn main:app --host 0.0.0.0 --port 8001
cd services/strategy_service && conda run -n vnpy uvicorn main:app --host 0.0.0.0 --port 8002
cd services/web_admin_service && python main.py
```

### 访问地址
- **Web管理界面**: http://localhost/
- **交易服务API**: http://localhost:8001/docs
- **策略服务API**: http://localhost:8002/docs

## 🎯 核心功能

### 1. 交易管理
- 实时行情数据接收和处理
- 订单管理和执行
- 持仓管理(今仓/昨仓分离)
- 智能平仓系统

### 2. 策略系统
- vnpy风格的策略开发框架
- 多种内置策略模板
- 动态策略加载和管理
- 策略参数实时调整

### 3. Web管理界面
- 直观的交易监控面板
- 策略管理和监控
- 实时数据展示
- 操作日志查看

### 4. 风险控制
- 实时风险监控
- 持仓限制管理
- 止损止盈控制

## 🔧 技术栈

- **后端**: Python, FastAPI, vnpy
- **前端**: HTML5, CSS3, JavaScript (ES6+)
- **数据库**: SQLite, Redis (可选)
- **交易接口**: CTP (Comprehensive Trading Platform)
- **部署**: Docker (可选), 系统服务

## 📝 开发指南

### 添加新策略
1. 在 `services/strategy_service/strategies/` 创建策略文件
2. 继承 `ARBIGCtaTemplate` 基类
3. 实现必要的回调方法
4. 定义策略参数模板
5. 通过Web界面或API注册策略

### 扩展API
1. 在对应服务的 `api/` 目录添加路由文件
2. 在 `main.py` 中注册新的路由
3. 更新API文档

### 修改配置
- 主配置: `config/config.py`
- CTP配置: `config/ctp_sim.json`
- 策略配置: `config/strategies.json`

## 🏷️ 版本信息

- **当前版本**: 2.0.0
- **架构**: 微服务
- **最后更新**: 2025-08-17
- **维护状态**: 活跃开发中

---

*本文档会随着项目发展持续更新。如有疑问，请参考具体模块的文档或联系开发团队。*
