# 如何修改主力合约

## 📋 概述

ARBIG系统已经实现了主力合约的灵活配置，所有模块都从统一的配置文件读取主力合约信息。

## 🎯 修改步骤

### 1. 修改配置文件

编辑 `config/config.py`，修改主力合约配置：

```python
CONFIG = {
    # 主力合约配置
    'main_contract': {
        'symbol': 'au2512',  # 👈 修改这里
        'name': '黄金主力',
        'exchange': 'SHFE',
        'description': '上海期货交易所黄金主力合约'
    },

    # 支持的合约列表
    'supported_contracts': [
        {'symbol': 'au2512', 'name': '黄金主力', 'exchange': 'SHFE', 'category': '贵金属', 'is_main': True},  # 👈 修改这里
        {'symbol': 'ag2512', 'name': '白银主力', 'exchange': 'SHFE', 'category': '贵金属', 'is_main': False},
        {'symbol': 'cu2512', 'name': '铜主力', 'exchange': 'SHFE', 'category': '有色金属', 'is_main': False}
    ],

    # 自动订阅的合约
    'auto_subscribe_contracts': ['au2512'],  # 👈 修改这里
    
    # ... 其他配置
}
```

### 2. 重启系统

修改配置后，需要重启所有服务：

```bash
# 停止所有服务
pkill -f "python.*services"

# 重新启动服务
python services/trading_service/main.py &
python services/strategy_service/main.py &
python services/web_admin_service/main.py &
```

### 3. 重新注册策略

如果已经注册了策略，需要重新注册以使用新的主力合约：

```bash
python strategy_manager.py

# 1. 停止旧策略
# 2. 注销旧策略
# 3. 注册新策略（使用新的主力合约）
# 4. 启动新策略
```

## 📝 示例：从 au2512 切换到 au2606

### 步骤1：修改 config/config.py

```python
CONFIG = {
    'main_contract': {
        'symbol': 'au2606',  # ✅ 改为2606合约
        'name': '黄金主力',
        'exchange': 'SHFE',
        'description': '上海期货交易所黄金主力合约'
    },

    'supported_contracts': [
        {'symbol': 'au2606', 'name': '黄金主力', 'exchange': 'SHFE', 'category': '贵金属', 'is_main': True},
        {'symbol': 'ag2606', 'name': '白银主力', 'exchange': 'SHFE', 'category': '贵金属', 'is_main': False},
        {'symbol': 'cu2606', 'name': '铜主力', 'exchange': 'SHFE', 'category': '有色金属', 'is_main': False}
    ],

    'auto_subscribe_contracts': ['au2606'],
}
```

### 步骤2：重启服务

```bash
# 停止所有服务
pkill -f "python.*services"

# 启动服务
./start_all.sh
```

### 步骤3：验证配置

```bash
# 验证配置是否生效
python -c "
from config.config import get_main_contract_symbol
print('当前主力合约:', get_main_contract_symbol())
"
```

应该输出：
```
当前主力合约: au2606
```

## 🔍 受影响的模块

以下模块会自动使用新的主力合约配置：

1. **策略引擎** (`services/strategy_service/core/strategy_engine.py`)
   - 自动订阅新的主力合约行情

2. **回测引擎** (`services/strategy_service/backtesting/backtest_engine.py`)
   - 默认回测品种自动更新

3. **Web管理界面** (`services/web_admin_service/api/trading.py`)
   - 一键平仓等功能自动使用新合约

4. **行情服务** (`services/trading_service/api/market_data.py`)
   - 模拟行情推送自动更新品种列表

## ⚠️ 注意事项

1. **持仓检查**：切换主力合约前，请确保旧合约的持仓已经平仓
2. **策略重新注册**：已注册的策略需要重新注册才能使用新合约
3. **历史数据**：旧合约的历史数据和日志会保留，不会被删除
4. **配置备份**：修改配置前建议备份 `config/config.py`

## 🎯 最佳实践

### 合约换月流程

1. **提前准备**（换月前1周）
   - 确认新主力合约代码
   - 准备配置文件修改

2. **执行切换**（换月当天）
   - 平掉旧合约所有持仓
   - 停止所有策略
   - 修改配置文件
   - 重启系统
   - 重新注册和启动策略

3. **验证确认**
   - 检查行情订阅是否正常
   - 确认策略运行正常
   - 监控交易执行情况

## 📚 相关文档

- [系统配置说明](./CONFIGURATION.md)
- [策略管理指南](./STRATEGY_MANAGEMENT.md)
- [API参考文档](./API_REFERENCE.md)

## 🆘 常见问题

### Q: 修改配置后系统没有使用新合约？
A: 请确保已经重启所有服务，并重新注册策略。

### Q: 可以同时交易多个合约吗？
A: 可以，在 `supported_contracts` 中添加多个合约，策略可以选择交易不同的合约。

### Q: 如何查看当前使用的主力合约？
A: 运行 `python -c "from config.config import get_main_contract_symbol; print(get_main_contract_symbol())"`

### Q: 修改配置需要重新编译吗？
A: 不需要，Python是解释型语言，修改配置后重启服务即可生效。

