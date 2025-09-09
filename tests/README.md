# ARBIG测试套件

## 📁 测试目录结构

```
tests/
├── README.md                    # 本文件 - 测试套件说明
├── run_all_tests.py            # 主测试运行器
├── system/                     # 系统级测试
│   ├── simple_system_test.py   # 基础系统功能测试
│   ├── test_non_trading_functions.py  # 非交易时间功能测试
│   └── test_service_connection.py     # 服务连接状态测试
├── strategy/                   # 策略相关测试
│   └── test_strategy_management.py    # 策略管理系统测试
├── integration/                # 集成测试
│   └── test_gfd_default.py    # GFD默认参数和订单测试
└── legacy/                     # 遗留测试文件
    ├── ctp_connection_test.py
    ├── test_account_query.py
    ├── test_frontend.py
    ├── test_history_query.py
    ├── test_order_placement.py
    └── test_web_trading.py
```

## 🎯 测试分类

### 系统级测试 (`system/`)
测试整个ARBIG系统的基础功能和服务状态

- **`simple_system_test.py`** - 基础系统健康检查
  - 服务进程状态
  - 端口监听状态
  - API响应测试
  - 配置文件检查

- **`test_non_trading_functions.py`** - 非交易时间功能测试
  - 服务健康状态
  - API接口测试
  - 数据库连接
  - 配置文件验证

- **`test_service_connection.py`** - 服务连接状态测试
  - 多端口连接检查
  - API文档可访问性
  - 服务响应状态
  - 连接故障诊断

### 策略相关测试 (`strategy/`)
测试策略管理系统的各项功能

- **`test_strategy_management.py`** - 策略管理系统测试
  - 策略注册/启停
  - 性能统计功能
  - 生命周期管理
  - Web界面代理

### 集成测试 (`integration/`)
测试各个服务之间的集成和协作

- 待添加：端到端测试
- 待添加：交易流程测试
- 待添加：数据流测试

### 遗留测试 (`legacy/`)
保留的历史测试文件，主要用于参考

- `ctp_connection_test.py` - CTP连接测试
- `test_order_placement.py` - 订单下单测试
- `test_web_trading.py` - Web交易测试
- 等等...

## 🚀 运行测试

### 运行所有测试
```bash
cd /root/ARBIG
python tests/run_all_tests.py
```

### 运行特定类别测试
```bash
# 系统测试
python tests/system/simple_system_test.py
python tests/system/test_non_trading_functions.py

# 策略测试
python tests/strategy/test_strategy_management.py
```

### 运行单个测试
```bash
# 基础系统测试
python tests/system/simple_system_test.py

# 策略管理测试
python tests/strategy/test_strategy_management.py
```

## 📋 测试前准备

### 基础要求
- Python 3.8+ 环境
- 已安装项目依赖 (`pip install -r requirements.txt`)
- 数据库服务运行中 (MySQL)

### 服务启动
```bash
# 启动所有服务
python scripts/start_all_services.py

# 或手动启动
cd services/trading_service && python main.py &
cd services/strategy_service && python main.py &
cd services/web_admin_service && python main.py --port 8080 &
```

### 环境配置
确保以下配置正确：
- `config/config.yaml` - 基础配置
- 数据库连接参数
- 服务端口配置

## 📊 测试报告

测试结果会保存到 `logs/` 目录：
- `logs/simple_test_YYYYMMDD_HHMMSS.json` - 基础测试结果
- `logs/strategy_management_test_YYYYMMDD_HHMMSS.json` - 策略测试结果
- `logs/test_results_YYYYMMDD_HHMMSS.json` - 详细测试结果

## 🔍 测试覆盖范围

### ✅ 已覆盖功能
- 服务启动和健康检查
- 基础API接口测试
- 策略管理功能测试
- 性能统计功能测试
- Web界面代理测试

### 🔄 待添加测试
- CTP连接和交易功能测试 (需交易时间)
- 数据库CRUD操作测试
- WebSocket实时数据测试
- 错误处理和异常恢复测试
- 性能和压力测试

## 🐛 故障排除

### 常见问题

1. **服务连接失败**
   - 检查服务是否启动：`ps aux | grep python`
   - 检查端口占用：`netstat -tlnp | grep 800[12]`
   - 检查防火墙设置

2. **数据库连接失败**
   - 检查MySQL服务状态：`systemctl status mysql`
   - 验证连接参数：`config/database.yaml`
   - 检查数据库权限

3. **模块导入错误**
   - 确保在项目根目录运行测试
   - 检查Python路径设置
   - 验证依赖包安装

4. **API响应超时**
   - 检查服务负载
   - 增加超时时间设置
   - 查看服务日志：`logs/*.log`

### 日志查看
```bash
# 查看最新测试日志
ls -la logs/test_* | tail -5

# 查看服务日志
tail -f logs/trading_service.log
tail -f logs/strategy_service.log
tail -f logs/web_admin_service.log
```

## 📝 测试开发指南

### 添加新测试
1. 确定测试类别 (system/strategy/integration)
2. 创建测试文件，继承相应的测试基类
3. 实现测试方法，遵循命名约定
4. 添加必要的文档和注释
5. 更新本README文档

### 测试命名约定
- 测试文件：`test_*.py`
- 测试类：`*Tester`
- 测试方法：`test_*()`
- 辅助方法：`_helper_*()`

### 最佳实践
- 每个测试应该独立运行
- 测试前清理环境，测试后恢复状态
- 使用有意义的断言和错误消息
- 添加适当的超时和重试机制
- 记录详细的测试日志