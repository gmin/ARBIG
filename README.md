# ARBIG 量化交易系统

> **A**lgorithmic **R**eal-time **B**asis **I**nvestment **G**ateway  
> 专业的量化交易管理平台

## 🎯 项目简介

ARBIG 是一个现代化的量化交易系统，专注于黄金跨市场套利和量化策略交易。系统采用 Web 管理架构，提供完整的交易管理、风控管理和系统监控功能。

### ✨ 核心特性

- 🎛️ **Web管理界面** - 现代化的交易管理控制台
- 🛡️ **实时风控** - 紧急暂停、一键平仓等风控功能  
- 📊 **交易监控** - 实时监控交易信号、订单状态、持仓情况
- 🔧 **API服务** - 完整的REST API接口
- ⚡ **高性能** - 基于vnpy的事件驱动架构
- 🔒 **安全可靠** - 多层风控保护机制

## 🏗️ 系统架构

```
ARBIG 量化交易系统
├── web_admin/          🎛️ Web管理系统
│   ├── 交易管理         # 手动下单、订单管理
│   ├── 风控管理         # 紧急暂停、一键平仓
│   ├── 系统监控         # 服务状态、延时监控
│   ├── 信号监控         # 交易信号跟踪分析
│   └── 历史记录         # 操作日志、交易历史
│
├── trading_api/        🔧 交易API服务
│   ├── 交易接口         # 下单、撤单、查询
│   ├── 账户接口         # 资金、持仓查询
│   ├── 行情接口         # 实时行情、历史数据
│   └── 风控接口         # 风险控制API
│
└── core/              ⚙️ 核心系统
    ├── 事件引擎         # 高性能事件处理
    ├── 服务组件         # 交易、风控、数据服务
    ├── CTP网关          # 期货交易接口
    └── 策略引擎         # 量化策略执行
```

## 🚀 快速开始

### 环境要求

- **Python**: 3.8+ (推荐使用vnpy环境)
- **操作系统**: Linux/Windows
- **依赖**: vnpy, vnpy-ctp, fastapi, uvicorn

### 1. 安装依赖

```bash
# 激活vnpy环境
conda activate vnpy

# 安装项目依赖
pip install -r requirements.txt
```

### 2. 配置CTP连接

编辑 `config/ctp_sim.json` 配置文件：

```json
{
    "用户名": "your_username",
    "密码": "your_password", 
    "经纪商代码": "9999",
    "交易服务器": "182.254.243.31:30001",
    "行情服务器": "182.254.243.31:30011"
}
```

### 3. 启动系统

```bash
# 使用统一启动脚本
python start_arbig.py

# 或者分别启动服务
python -m web_admin.app      # Web管理系统 (端口8000)
python -m trading_api.app    # 交易API服务 (端口8001)
```

### 4. 访问Web管理界面

打开浏览器访问: **http://localhost:8000**

- 🎛️ **交易管理** - 手动下单、订单监控
- 🛡️ **风控管理** - 紧急暂停、一键平仓
- 📊 **系统监控** - 实时状态、性能指标
- 📈 **信号监控** - 交易信号跟踪分析

## 🧪 功能测试

```bash
# 测试CTP连接
python tests/ctp_connection_test.py

# 测试下单功能
python test_order_placement.py

# 测试信号监控
python test_signal_monitoring.py
```

## 📚 文档导航

### 📖 用户文档
- [**用户手册**](docs/USER_MANUAL.md) - 详细使用说明
- [**API文档**](docs/API_REFERENCE.md) - 接口调用指南
- [**部署指南**](docs/DEPLOYMENT.md) - 生产环境部署

### 🔧 技术文档  
- [**系统架构**](docs/ARCHITECTURE.md) - 详细架构设计
- [**开发指南**](docs/DEVELOPMENT.md) - 开发环境搭建
- [**CTP配置**](docs/CTP_SETUP.md) - CTP连接配置

### 📊 策略文档
- [**策略总览**](docs/strategies/README.md) - 策略文档导航
- [**基差套利**](docs/strategies/SPREAD_THRESHOLD_GUIDE.md) - 基差套利阈值指南
- [**策略开发**](docs/STRATEGY_DEVELOPMENT.md) - 策略开发指南
- [**风控管理**](docs/RISK_MANAGEMENT.md) - 风控机制说明

## 🎯 主要功能

### 💼 交易管理
- ✅ 手动下单 - 支持限价单、市价单
- ✅ 订单管理 - 实时订单状态跟踪
- ✅ 持仓管理 - 实时持仓监控
- ✅ 账户查询 - 资金、保证金查询

### 🛡️ 风控管理
- ✅ **紧急暂停** - 一键暂停所有交易
- ✅ **一键平仓** - 紧急情况下快速平仓
- ✅ **策略控制** - 单独暂停/恢复策略
- ✅ **风险监控** - 实时风险指标监控

### 📊 系统监控
- ✅ **服务状态** - CTP连接、服务运行状态
- ✅ **性能监控** - 延时、CPU、内存监控
- ✅ **交易信号** - 信号触发原因跟踪
- ✅ **历史记录** - 完整的操作审计日志

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系我们

- 项目主页: [GitHub Repository](https://github.com/your-repo/arbig)
- 问题反馈: [Issues](https://github.com/your-repo/arbig/issues)
- 文档中心: [Documentation](docs/)

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！
