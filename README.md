# ARBIG 量化交易系统

> **A**lgorithmic **R**eal-time **B**asis **I**nvestment **G**ateway  
> 专业的量化交易管理平台

## 🎯 项目简介

ARBIG 是一个专业的量化交易系统，专注于SHFE黄金期货量化交易。系统基于vnpy/CTP框架，采用微服务架构，提供智能平仓、实时监控和策略管理功能。核心特色是前端控制的今昨仓智能分解平仓系统。

## ⚡ 快速启动

```bash
# 1. 进入项目目录
cd /root/ARBIG

# 2. 激活vnpy环境
conda activate vnpy

# 3. 一键启动系统（推荐）
python start_with_logs.py

# 4. 访问Web界面
# 浏览器打开: http://localhost
```

> 🎯 **首次使用**: 请先配置 `config/ctp_sim.json` 中的CTP连接信息

### ✨ 核心特性

- 🎛️ **Web管理界面** - 现代化的交易管理控制台，支持移动端
- 🛡️ **智能平仓** - 前端控制的今昨仓智能分解平仓
- 📊 **实时监控** - 实时持仓、盈亏、策略状态监控
- 🔧 **手动交易** - 完整的手动开仓、平仓功能
- ⚡ **高性能** - 基于vnpy的CTP集成，稳定可靠
- 🎯 **专注策略** - 专注SHFE黄金量化交易

## 🏗️ 系统架构

```
ARBIG 量化交易系统
├── 核心交易服务 (trading_service) - 端口8001
│   ├── CTP集成          # vnpy/CTP期货交易接口
│   ├── 持仓管理          # 实时持仓查询，今昨仓处理
│   ├── 订单执行          # 手动交易、平仓操作
│   └── 策略管理          # SHFE黄金量化策略
│
├── 策略执行服务 (strategy_service) - 端口8002
│   ├── vnpy风格策略引擎   # 基于ARBIGCtaTemplate的策略执行
│   ├── 多策略支持         # 测试、双均线、量化、高级策略
│   ├── 动态策略加载       # 自动发现和加载策略类
│   └── 策略生命周期管理   # 策略注册、启动、停止、监控
│
└── Web管理服务 (web_admin_service) - 端口80
    ├── 交易界面          # 实时持仓、手动交易
    ├── 策略监控          # 策略状态、参数调整
    └── 系统管理          # 服务状态、健康检查
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
python start_with_logs.py
```

#### 🔧 手动启动各服务

```bash
# 1. 启动核心交易服务
conda activate vnpy
python services/trading_service/main.py --port 8001

# 2. 启动策略管理服务
conda activate vnpy
python services/strategy_service/main.py --port 8002

# 3. 启动Web管理服务
conda activate vnpy
python services/web_admin_service/main.py --port 80
```

> **⚠️ 注意**: 手动启动时，建议按顺序启动各服务

### 4. 访问Web管理界面

启动成功后，打开浏览器访问以下地址：

#### 🎛️ Web管理界面
- **首页**: http://localhost - 系统概览和实时行情
- **交易页面**: http://localhost/trading - 手动交易、持仓管理
- **策略管理**: http://localhost/strategy - 策略监控和控制
- **API文档**: http://localhost:8001/docs - 完整的REST API文档

#### 📊 功能模块
- 🎯 **实时持仓** - 包含今昨仓详情的持仓监控
- 💼 **智能平仓** - 前端控制的今昨仓分解平仓
- 📈 **手动交易** - 支持开仓、平仓操作
- 🎛️ **策略控制** - 策略启动、停止、参数调整
- 🔍 **系统监控** - CTP连接、服务健康状态

### 5. 启动状态检查

#### ✅ 验证系统启动成功

```bash
# 检查服务端口
netstat -tlnp | grep -E "(80|8001|8002)"

# 测试API连接
curl http://localhost:8001/real_trading/positions
curl http://localhost/api/v1/trading/positions

# 检查CTP连接状态
curl http://localhost:8001/real_trading/status
```

#### 🔍 启动成功标志
- ✅ **核心交易服务**: 端口8001正常监听
- ✅ **策略管理服务**: 端口8002正常监听
- ✅ **Web管理服务**: 端口80正常监听
- ✅ **CTP连接**: 交易和行情连接状态正常（非交易时间连接失败是正常的）

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
```

### 🔍 CTP连接测试详解

CTP连接测试成功的标志：
- ✅ 交易服务器连接成功
- ✅ 交易服务器登录成功
- ✅ 行情服务器连接成功
- ✅ 行情服务器登录成功
- ✅ 成功接收行情数据

如果测试失败，请查看 [CTP_SETUP.md](CTP_SETUP.md) 中的故障排除指南。

## 🌟 核心亮点

### 🎯 智能平仓系统
ARBIG的核心创新是**前端控制的智能平仓系统**：

- **今昨仓自动识别**: 系统自动获取vnpy的真实今昨仓数据
- **前端智能分解**: 用户平仓时，前端自动分解为今仓和昨仓订单
- **透明化操作**: 用户可以看到今仓、昨仓的具体数量
- **优化执行**: 优先平今仓（手续费更低），再平昨仓

**示例**: 持有3手多单（今仓2手+昨仓1手），点击平仓3手时：
1. 前端显示：今仓2手，昨仓1手
2. 自动发送：平今仓2手 + 平昨仓1手
3. 用户反馈：平仓成功3手（发送2个订单）

### 🏗️ 微服务架构
- **核心交易服务**: CTP集成、持仓管理、订单执行
- **策略管理服务**: 策略配置、监控、控制
- **Web管理服务**: 用户界面、API网关

### 📱 现代化界面
- **响应式设计**: 支持桌面和移动设备
- **实时更新**: 持仓、盈亏、价格实时刷新
- **直观操作**: 一键平仓、策略控制

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
- ✅ **智能平仓** - 前端控制的今昨仓分解平仓
- ✅ **手动交易** - 支持开仓、平仓操作
- ✅ **持仓监控** - 实时持仓，包含今昨仓详情
- ✅ **账户查询** - 资金、保证金查询

### 🎛️ 策略管理
- ✅ **SHFE黄金策略** - 专注黄金期货量化交易
- ✅ **策略控制** - 启动、停止、参数调整
- ✅ **实时监控** - 策略状态、信号跟踪
- ✅ **风险控制** - 紧急停止、一键平仓

### 📊 系统监控
- ✅ **服务状态** - 三个微服务的健康监控
- ✅ **CTP连接** - 交易和行情连接状态
- ✅ **实时数据** - 持仓、盈亏、价格实时更新
- ✅ **移动端支持** - 响应式Web界面

## 📁 项目文件说明

### 🚀 核心脚本
- **`start_with_logs.py`** - 一键启动脚本，推荐使用 ⭐
- **`services/trading_service/main.py`** - 核心交易服务 ⭐
- **`services/strategy_service/main.py`** - 策略管理服务 ⭐
- **`services/web_admin_service/main.py`** - Web管理服务 ⭐

### 🧪 测试目录 (`tests/`)
- **核心测试**: CTP连接、下单、历史查询、账户查询
- **Web测试**: API测试、前端测试
- **测试工具**: 完整测试套件和专项测试

### 📂 主要目录
- **`services/`** - 微服务架构
  - `trading_service/` - 核心交易服务
  - `strategy_service/` - 策略管理服务
  - `web_admin_service/` - Web管理服务
- **`config/`** - 配置文件
  - `ctp_sim.json` - CTP连接配置
- **`tests/`** - 测试文件
- **`logs/`** - 系统日志

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
- **端口占用** → 检查 `netstat -tlnp | grep -E "(80|8001|8002)"`
- **环境依赖** → 运行 `python start_with_logs.py` 查看环境检查结果
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


