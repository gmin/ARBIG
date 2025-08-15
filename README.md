# ARBIG 量化交易系统

> **A**lgorithmic **R**eal-time **B**asis **I**nvestment **G**ateway  
> 专业的量化交易管理平台

## 🎯 项目简介

ARBIG 是一个现代化的量化交易系统，专注于黄金跨市场套利和量化策略交易。系统采用 Web 管理架构，提供完整的交易管理、风控管理和系统监控功能。

## ⚡ 快速启动

```bash
# 1. 进入项目目录
cd /root/ARBIG

# 2. 激活vnpy环境
conda activate vnpy

# 3. 一键启动系统
python start.py --mode full --auto

# 4. 访问Web界面
# 浏览器打开: http://localhost
```

> 🎯 **首次使用**: 请先配置 `config/ctp_sim.json` 中的CTP连接信息

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

> ⚠️ **CTP重要提醒**: vnpy-ctp预编译包通常有兼容性问题，**强烈建议从源码编译安装**。详见 [CTP_SETUP.md](CTP_SETUP.md) 完整解决方案。

### 1. 安装依赖

```bash
# 激活vnpy环境
conda activate vnpy

# 安装项目依赖
pip install -r requirements.txt
```

#### 🔧 CTP安装（重要）

由于vnpy-ctp兼容性问题，需要从源码编译安装：

```bash
# 1. 卸载预编译版本
pip uninstall vnpy-ctp -y

# 2. 从源码编译安装
cd /root
git clone https://github.com/vnpy/vnpy_ctp.git
cd vnpy_ctp
pip install meson-python ninja pybind11
pip install .

# 3. 验证安装
python -c "from vnpy_ctp import CtpGateway; print('✅ vnpy-ctp安装成功！')"
```

> 📖 **详细说明**: 如遇到问题，请参考 [CTP_SETUP.md](CTP_SETUP.md) 获取完整的故障排除指南

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

#### 🚀 推荐启动方式（一键启动）

```bash
# 进入项目目录并激活环境
cd /root/ARBIG
conda activate vnpy

# 一键启动完整系统（推荐）
python start.py --mode full --auto
```

#### 🎛️ 交互式启动

```bash
# 交互式菜单启动
python start.py

# 然后选择：
# 1 - 🚀 启动完整系统 (推荐)
# 2 - 🔧 仅启动Web管理界面
# 3 - 📊 仅启动核心交易服务
# 4 - 🧪 运行系统测试
# 0 - 👋 退出
```

#### ⚙️ 单独服务启动

```bash
# 仅启动Web管理界面
python start.py --mode web --auto

# 仅启动核心交易服务
python start.py --mode trading --auto

# 运行系统测试
python start.py --mode test --auto
```

#### 🔧 手动启动各服务

```bash
# 1. 先启动核心交易服务（必须）
conda activate vnpy
python services/trading_service/main.py --port 8001

# 2. 再启动Web管理服务
conda activate vnpy
python services/web_admin_service/main.py --port 80
```

> **⚠️ 注意**: 手动启动时，必须先启动交易服务，再启动Web服务

### 4. 访问Web管理界面

启动成功后，打开浏览器访问以下地址：

#### 🎛️ Web管理界面
- **首页**: http://localhost - 系统概览和实时行情
- **交易管理**: http://localhost/trading - 手动下单、持仓管理
- **API文档**: http://localhost:8001/docs - 完整的REST API文档

#### 📊 功能模块
- 🎯 **实时行情** - au2510黄金主力合约实时数据
- � **手动交易** - 支持市价单、限价单交易
- � **持仓监控** - 实时持仓、盈亏统计
- �️ **风控管理** - 紧急暂停、一键平仓
- � **系统状态** - CTP连接、服务监控

### 5. 启动状态检查

#### ✅ 验证系统启动成功

```bash
# 检查服务端口
netstat -tlnp | grep -E "(80|8001)"

# 测试API连接
curl http://localhost:8001/real_trading/status
curl http://localhost/api/v1/trading/config/main_contract

# 检查CTP连接状态
curl http://localhost/api/v1/trading/ctp_status
```

#### 🔍 启动成功标志
- ✅ **交易服务**: 端口8001正常监听
- ✅ **Web服务**: 端口80正常监听
- ✅ **CTP连接**: 交易和行情连接均为已连接状态
- ✅ **主力合约**: 正确显示au2510合约信息

#### 🛠️ CTP连接问题排查

如果CTP连接失败，请按以下步骤排查：

```bash
# 1. 测试CTP连接
python tests/ctp_connection_test.py

# 2. 检查vnpy-ctp安装
python -c "from vnpy_ctp import CtpGateway; print('CTP模块正常')"

# 3. 检查配置文件
cat config/ctp_sim.json
```

> 🔧 **常见问题**: 如遇到 `ImportError: libthostmduserapi_se.so` 等错误，请参考 [CTP_SETUP.md](CTP_SETUP.md) 中的完整解决方案

## 🧪 功能测试

```bash
# 激活环境
conda activate vnpy

# 测试CTP连接（重要）
python tests/ctp_connection_test.py

# 测试下单功能
python tests/test_order_placement.py

# 运行完整测试套件
python start.py --mode test --auto
```

### 🔍 CTP连接测试详解

CTP连接测试成功的标志：
- ✅ 交易服务器连接成功
- ✅ 交易服务器登录成功
- ✅ 行情服务器连接成功
- ✅ 行情服务器登录成功
- ✅ 成功接收行情数据

如果测试失败，请查看 [CTP_SETUP.md](CTP_SETUP.md) 中的故障排除指南。

## 📚 文档导航

> 📖 **完整文档中心**: [docs/README.md](docs/README.md) - 所有技术文档的导航入口 ⭐

### 🚀 快速文档
- [**CTP配置指南**](CTP_SETUP.md) - CTP连接配置与问题解决 ⭐
- [**当前系统架构**](docs/CURRENT_ARCHITECTURE.md) - 微服务架构详细说明 ⭐
- [**用户手册**](docs/USER_MANUAL.md) - 详细使用说明

### 📂 文档分类
- **🏗️ 架构文档** - [当前架构](docs/CURRENT_ARCHITECTURE.md) | [历史架构](docs/archive/)
- **🔧 技术文档** - [交易服务](docs/TRADING_SERVICE_GUIDE.md) | [API规范](docs/WEB_API_SPECIFICATION.md)
- **📊 策略文档** - [策略总览](docs/strategies/README.md) | [基差套利](docs/strategies/SPREAD_THRESHOLD_GUIDE.md)
- **🧪 测试文档** - [测试指南](tests/README.md) | [CTP测试](tests/ctp_connection_test.py)

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

## 📁 项目文件说明

### 🚀 核心脚本
- **`start.py`** - 统一启动脚本，推荐使用 ⭐
- **`services/trading_service/main.py`** - 核心交易服务 ⭐
- **`services/web_admin_service/main.py`** - Web管理服务 ⭐

### 🧪 测试目录 (`tests/`)
- **核心测试**: CTP连接、下单、历史查询、账户查询
- **Web测试**: API测试、前端测试
- **测试工具**: 完整测试套件和专项测试

### 📂 主要目录
- **`services/`** - 微服务架构
  - `trading_service/` - 核心交易服务
  - `web_admin_service/` - Web管理服务
- **`config/`** - 配置文件
  - `config.py` - 主配置文件
  - `ctp_sim.json` - CTP连接配置
- **`tests/`** - 测试文件
- **`docs/`** - 项目文档

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## ❓ 常见问题快速索引

### 🔧 CTP相关问题
- **ImportError: libthostmduserapi_se.so** → [CTP_SETUP.md](CTP_SETUP.md#vnpy-ctp-安装问题解决方案)
- **CTP连接失败** → [CTP_SETUP.md](CTP_SETUP.md#故障排除指南)
- **NumPy版本冲突** → [CTP_SETUP.md](CTP_SETUP.md#根本原因)
- **vnpy-ctp编译错误** → [CTP_SETUP.md](CTP_SETUP.md#编译错误)

### 🚀 启动问题
- **端口占用** → 检查 `netstat -tlnp | grep -E "(80|8001)"`
- **环境依赖** → 运行 `python start.py` 查看环境检查结果
- **服务启动失败** → 查看终端错误信息，检查配置文件

### 💼 交易问题
- **下单失败** → 检查CTP连接状态和账户资金
- **行情数据异常** → 验证CTP行情连接和合约订阅
- **持仓数据不准确** → 重启系统或检查CTP账户状态

> 📖 **完整文档**: 更多问题解决方案请参考 [CTP_SETUP.md](CTP_SETUP.md)

## 📞 联系我们

- 项目主页: [GitHub Repository](https://github.com/your-repo/arbig)
- 问题反馈: [Issues](https://github.com/your-repo/arbig/issues)
- 文档中心: [Documentation](docs/)

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！



