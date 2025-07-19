# ARBIG 测试套件

本目录包含ARBIG量化交易系统的核心测试脚本。

## 🚀 快速开始

### 运行核心测试
```bash
python tests/run_tests.py --all
```

### 运行指定测试
```bash
python tests/run_tests.py --test test_order_placement.py
```

### 运行完整测试套件
```bash
python tests/run_all_tests.py
```

## 📋 核心测试文件

### 🔧 基础功能测试

#### `ctp_connection_test.py`
- **功能**: CTP连接测试，验证网络和连接状态
- **运行**: `python tests/ctp_connection_test.py`

#### `test_account_query.py`
- **功能**: 账户信息查询测试
- **运行**: `python tests/test_account_query.py`

### 💰 交易功能测试

#### `test_order_placement.py` ⭐
- **功能**: 完整的下单测试，支持各种订单类型
- **运行**: `python tests/test_order_placement.py`

#### `test_history_query.py` ⭐
- **功能**: 历史订单和成交查询测试
- **运行**: `python tests/test_history_query.py`

### 🌐 Web功能测试

#### `test_web_trading.py`
- **功能**: Web API交易测试
- **运行**: `python tests/test_web_trading.py`

#### `test_frontend.py`
- **功能**: 前端界面测试
- **运行**: `python tests/test_frontend.py`

### 🛠️ 测试工具

#### `run_tests.py`
- **功能**: 核心测试运行器
- **运行**: `python tests/run_tests.py --all`

#### `run_all_tests.py`
- **功能**: 完整测试套件
- **运行**: `python tests/run_all_tests.py`

#### `run_trading_tests.py`
- **功能**: 交易专项测试
- **运行**: `python tests/run_trading_tests.py`

## 🎯 推荐测试顺序

### 1. 基础连接测试
```bash
python tests/ctp_connection_test.py
```

### 2. 账户功能测试
```bash
python tests/test_account_query.py
```

### 3. 交易功能测试
```bash
python tests/test_order_placement.py
```

### 4. 历史数据测试
```bash
python tests/test_history_query.py
```

### 5. Web功能测试
```bash
python tests/test_web_trading.py
```

## ⚠️ 注意事项

1. **环境要求**: 所有测试都需要在vnpy环境下运行
2. **CTP连接**: 涉及CTP的测试需要有效的CTP账户配置
3. **测试数据**: 某些测试可能会产生实际的交易订单，请在仿真环境下运行
4. **依赖关系**: 某些测试需要先启动ARBIG系统服务

## 🔧 故障排除

### 测试失败常见原因
1. **环境问题**: 未激活vnpy环境
2. **配置问题**: CTP配置文件不正确
3. **网络问题**: 无法连接CTP服务器
4. **依赖问题**: 缺少必要的Python包

### 解决方案
```bash
# 1. 激活环境
conda activate vnpy

# 2. 检查配置
cat config/ctp_sim.json

# 3. 检查依赖
python help.py

# 4. 运行诊断
python diagnose_web_issue.py
```
