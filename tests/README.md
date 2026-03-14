# ARBIG测试套件

## 📁 测试目录结构

```
tests/
├── README.md                          # 本文件
├── run_tests.py                       # 测试运行器（按类别运行）
├── validate_imports.py                # 导入路径验证工具
├── system/                            # 系统级测试
│   ├── simple_system_test.py          # 基础系统功能测试
│   └── test_non_trading_functions.py  # 非交易时间功能测试
├── strategy/                          # 策略相关测试
│   ├── test_strategy_offline.py       # 策略离线测试框架
│   └── test_strategy_management.py    # 策略管理系统测试
├── integration/                       # 集成测试
│   └── test_gfd_default.py            # GFD默认参数和订单测试
└── legacy/                            # 遗留测试文件（需CTP环境）
    ├── ctp_connection_test.py         # CTP连接测试
    └── test_order_placement.py        # 交互式下单测试
```

## 🎯 测试分类

### 系统级测试 (`system/`)

测试整个ARBIG系统的基础功能和服务状态

- **`simple_system_test.py`** - 基础系统健康检查
  - 服务进程状态、端口监听、API响应、配置文件检查

- **`test_non_trading_functions.py`** - 非交易时间功能测试
  - 服务健康状态、API接口、配置文件验证


### 策略相关测试 (`strategy/`)

- **`test_strategy_offline.py`** - 策略离线测试框架（不需要服务运行）
  - 提供 MockSignalSender、MockDataGenerator、StrategyTester
  - 支持策略初始化、数据处理、参数敏感性等综合测试
  - 自动加载全部 5 个策略进行测试

- **`test_strategy_management.py`** - 策略管理系统测试（需服务运行）
  - 策略 API、注册、生命周期、性能跟踪、Web 代理

### 集成测试 (`integration/`)

- **`test_gfd_default.py`** - GFD默认参数和订单测试

### 遗留测试 (`legacy/`)

保留的历史测试文件，需要 CTP 环境

- `ctp_connection_test.py` - CTP连接全流程测试
- `test_order_placement.py` - 交互式下单测试工具

## 🚀 运行测试

### 离线策略测试（推荐先运行）

```bash
cd /path/to/ARBIG
python tests/strategy/test_strategy_offline.py
```

### 系统测试（需要服务运行）

```bash
python start_with_logs.py

python tests/system/simple_system_test.py
python tests/system/test_non_trading_functions.py
```

### 按类别运行

```bash
python tests/run_tests.py
```

## 📋 测试前准备

- Python 3.13+ 环境（vnpy 4.0 要求）
- 已安装项目依赖 (`pip install -r requirements.txt`)

| 服务 | 端口 |
|------|------|
| Web管理服务 | 8000 |
| 交易服务 | 8001 |
| 策略服务 | 8002 |

## 🐛 故障排除

1. **服务连接失败** — `lsof -i :8000 -i :8001 -i :8002`
2. **模块导入错误** — 确保在项目根目录运行，或执行 `python tests/validate_imports.py`
3. **API响应超时** — 查看 `logs/gold_arbitrage.log`
