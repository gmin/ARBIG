# ARBIG 量化交易系统

> **A**lgorithmic **R**eal-time **B**asis **I**nvestment **G**ateway  
> 专业的量化交易管理平台

## 🎯 项目简介

ARBIG 是一个专业的量化交易系统，专注于 SHFE 黄金期货量化交易。系统基于 vnpy/CTP 框架，采用微服务架构，当前聚焦于交易执行、策略管理、实时监控与紧急停止能力。

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
```text

> 🎯 **首次使用**: 请先配置 `config/ctp_sim.json` 中的CTP连接信息

### ✨ 核心特性

- 🎛️ **Web管理界面** - 精简后的监控与策略控制台，支持移动端
- 🛑 **紧急停止** - 保留关键的系统级止损操作
- 📊 **实时监控** - 实时持仓、盈亏、行情、策略状态监控
- 🧭 **边界清晰** - 交易执行与策略管理服务职责分离
- ⚡ **高性能** - 基于vnpy的CTP集成，稳定可靠
- 🎯 **专注策略** - 专注SHFE黄金量化交易

## 🏗️ 系统架构

```text

ARBIG 量化交易系统
├── 核心交易服务 (trading_service) - 端口8001
│   ├── CTP集成          # vnpy/CTP期货交易接口
│   ├── 持仓管理          # 实时持仓、账户、订单执行
│   ├── 行情服务          # CTP实时行情与WebSocket推送
│   └── 交易执行          # 下单、撤单、账户查询
│
├── 策略执行服务 (strategy_service) - 端口8002
│   ├── vnpy风格策略引擎   # 基于ARBIGCtaTemplate的策略执行
│   ├── 多策略支持         # 测试、MA+RSI、多模式、突破、均值回归
│   ├── 动态策略加载       # 自动发现和加载策略类
│   └── 策略生命周期管理   # 策略注册、启动、停止、监控
│
└── Web管理服务 (web_admin_service) - 端口80
    ├── 总控台            # 系统状态、账户、持仓、行情监控
    ├── 策略中心          # 策略状态、参数调整、回测入口
    └── 交易日志          # 日志查询与运行记录

```

## 🚀 快速开始

### 环境要求

- **Python**: 3.13 (建议与当前 vnpy 依赖保持一致)
- **操作系统**: macOS/Linux
- **依赖**: vnpy, vnpy-ctp, fastapi, uvicorn

> ⚠️ **CTP重要提醒**: vnpy-ctp 预编译包通常有兼容性问题，**强烈建议从源码编译安装**。详见 [CTP 配置指南](docs/technical/CTP_SETUP.md)。

### 1. 安装依赖

```bash
# 激活vnpy环境
conda activate vnpy

# 安装项目依赖
pip install -r requirements.txt
```

### 🔧 CTP安装（重要）

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

> 📖 **详细说明**: 如遇到问题，请参考 [CTP 配置指南](docs/technical/CTP_SETUP.md) 获取完整的故障排除指南。

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

- **首页**: `http://localhost` - 系统概览和实时行情
- **策略中心**: `http://localhost/strategy` - 策略监控、控制与回测
- **交易日志**: `http://localhost/trading_logs` - 日志查询与运行记录
- **API文档**: `http://localhost:8001/docs` - 完整的 REST API 文档

#### 📊 功能模块

- 🎯 **实时持仓** - 实时持仓与盈亏监控
- 📈 **实时行情** - 主力合约行情和连接状态展示
- 🎛️ **策略控制** - 策略启动、停止、参数调整
- 🔍 **系统监控** - CTP连接、服务健康、关键状态

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

> 🔧 **常见问题**: 如遇到 `ImportError: libthostmduserapi_se.so` 等错误，请参考 [CTP 配置指南](docs/technical/CTP_SETUP.md)。

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

如果测试失败，请查看 [CTP 配置指南](docs/technical/CTP_SETUP.md) 中的故障排除指南。

## 🌟 核心亮点

### 🛑 紧急停止与职责边界

当前版本的 Web 端以监控和策略控制为主，不再承担手动下单和平仓入口。  
系统职责边界已经收敛为：

- **Trading Service**：负责 CTP 接入、行情、账户、持仓和交易执行
- **Strategy Service**：负责策略加载、运行、参数调整、回测与触发记录
- **Web Admin Service**：负责总控台、策略中心、交易日志，以及必要时的紧急停止入口

### 🏗️ 微服务架构

- **核心交易服务**: CTP集成、持仓管理、订单执行
- **策略管理服务**: 策略配置、监控、控制
- **Web管理服务**: 用户界面、API网关

### 📱 现代化界面

- **响应式设计**: 支持桌面和移动设备
- **实时更新**: 持仓、盈亏、价格实时刷新
- **直观操作**: 紧急停止、策略控制

## 📚 文档导航

### 🚀 快速文档

- [**CTP 配置指南**](docs/technical/CTP_SETUP.md) - CTP 连接配置与问题排查 ⭐
- [**完整架构图**](docs/architecture/full_architecture.md) - 当前服务边界与数据流 ⭐
- [**API 参考**](docs/API_REFERENCE.md) - 当前 API 与聚合路由说明

### 📂 文档分类

- **🏗️ 架构文档** - [完整架构图](docs/architecture/full_architecture.md) | [V2 设计草案](docs/architecture/v2_architecture_design.md)
- **🔧 技术文档** - [API 参考](docs/API_REFERENCE.md) | [CTP 配置](docs/technical/CTP_SETUP.md)
- **📊 策略文档** - [策略使用指南](docs/strategies/STRATEGY_USAGE_GUIDE.md) | [策略代码规范](docs/strategies/STRATEGY_CODE_STANDARDS.md)
- **🧪 测试文档** - [测试指南](tests/README.md) | [CTP测试](tests/ctp_connection_test.py)

## 🎯 主要功能

### 💼 交易管理

- ✅ **持仓监控** - 实时持仓、账户与成交状态查询
- ✅ **账户查询** - 资金、保证金查询
- ✅ **行情监控** - 主力合约行情与连接状态查询

### 🎛️ 策略管理

- ✅ **SHFE黄金策略** - 专注黄金期货量化交易
- ✅ **策略控制** - 启动、停止、参数调整
- ✅ **实时监控** - 策略状态、信号跟踪
- ✅ **风险控制** - 紧急停止

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

- **ImportError: libthostmduserapi_se.so** → [CTP 配置指南](docs/technical/CTP_SETUP.md)
- **CTP连接失败** → [CTP 配置指南](docs/technical/CTP_SETUP.md)
- **NumPy版本冲突** → [CTP 配置指南](docs/technical/CTP_SETUP.md)
- **vnpy-ctp编译错误** → [CTP 配置指南](docs/technical/CTP_SETUP.md)

### 🚀 启动问题

- **端口占用** → 检查 `netstat -tlnp | grep -E "(80|8001|8002)"`
- **环境依赖** → 运行 `python start_with_logs.py` 查看环境检查结果
- **服务启动失败** → 查看终端错误信息，检查配置文件

### 💼 交易问题

- **下单失败** → 检查CTP连接状态和账户资金
- **行情数据异常** → 验证CTP行情连接和合约订阅
- **持仓数据不准确** → 重启系统或检查CTP账户状态

> 📖 **完整文档**: 更多问题解决方案请参考 [CTP 配置指南](docs/technical/CTP_SETUP.md)。

---