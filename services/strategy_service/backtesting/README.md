# ARBIG专业回测系统

基于vnpy BacktestingEngine的专业策略回测系统，支持策略验证、参数优化和性能分析。

## 🎯 功能特点

- ✅ **专业回测引擎**: 基于vnpy的BacktestingEngine
- ✅ **策略适配**: 自动适配ARBIG策略到vnpy回测引擎
- ✅ **批量回测**: 支持多策略并行回测和对比分析
- ✅ **参数优化**: 自动寻找最优策略参数
- ✅ **性能分析**: 完整的回测报告和风险指标
- ✅ **API接口**: HTTP API支持远程调用
- ✅ **结果管理**: 回测结果保存和查询

## 📦 安装依赖

### 1. 安装vnpy回测模块
```bash
# 激活vnpy环境
conda activate vnpy

# 安装vnpy_ctastrategy
pip install vnpy_ctastrategy

# 验证安装
python -c "from vnpy_ctastrategy import BacktestingEngine; print('✅ vnpy_ctastrategy安装成功')"
```

### 2. 检查依赖
```bash
# 检查必要的Python包
pip list | grep -E "(vnpy|pandas|numpy|fastapi)"
```

## 🚀 快速开始

### 1. 启动策略服务
```bash
# 进入项目根目录
cd /root/ARBIG

# 启动策略服务（包含回测API）
python services/strategy_service/main.py
```

### 2. 检查回测功能
```bash
# 检查回测API是否可用
curl http://localhost:8002/backtest/health

# 查看可用策略
curl http://localhost:8002/backtest/strategies
```

### 3. 运行示例
```bash
# 运行回测示例
python services/strategy_service/backtesting/examples/backtest_examples.py
```

## 📊 使用方法

### 方法1: Python API调用

```python
from services.strategy_service.backtesting.backtest_manager import BacktestManager, quick_backtest
import asyncio

async def run_backtest():
    # 快速回测
    result = await quick_backtest(
        strategy_name="LargeOrderFollowing",
        strategy_setting={"max_position": 10},
        days=30
    )
    print(f"收益率: {result['basic_result']['total_return']:.2%}")

# 运行
asyncio.run(run_backtest())
```

### 方法2: HTTP API调用

```bash
# 快速回测
curl -X POST "http://localhost:8002/backtest/quick" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "LargeOrderFollowing",
    "strategy_setting": {"max_position": 10},
    "days": 30
  }'

# 单个策略回测
curl -X POST "http://localhost:8002/backtest/run" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "LargeOrderFollowing",
    "strategy_setting": {"max_position": 10},
    "start_date": "2024-01-01",
    "end_date": "2024-03-31",
    "capital": 1000000
  }'
```

### 方法3: 批量回测

```python
# 批量回测多个策略
strategies_config = [
    {
        "strategy_name": "LargeOrderFollowing",
        "strategy_setting": {"max_position": 10}
    },
    {
        "strategy_name": "VWAPDeviationReversion",
        "strategy_setting": {"max_position": 8}
    }
]

manager = BacktestManager()
result = await manager.run_batch_backtest(
    strategies_config=strategies_config,
    backtest_setting={
        "start_date": datetime(2024, 1, 1),
        "end_date": datetime(2024, 3, 31),
        "capital": 1000000
    }
)

# 查看对比结果
print("最佳策略:", result["comparison"]["summary"]["best_strategy"])
```

## 📈 回测结果解读

### 基础指标
- **total_return**: 总收益率
- **annual_return**: 年化收益率
- **max_drawdown**: 最大回撤
- **sharpe_ratio**: 夏普比率
- **win_rate**: 胜率

### 交易统计
- **total_trade_count**: 总交易次数
- **winning_trade_count**: 盈利交易次数
- **losing_trade_count**: 亏损交易次数
- **profit_loss_ratio**: 盈亏比

### 风险指标
- **volatility**: 波动率
- **calmar_ratio**: 卡尔马比率
- **sortino_ratio**: 索提诺比率

## 🔧 参数优化

```python
# 参数优化示例
optimization_config = {
    "optimization_setting": {
        "max_position": [5, 8, 10, 12],
        "large_order_threshold": [2.0, 3.0, 4.0]
    },
    "target_name": "sharpe_ratio"
}

result = await manager.optimize_strategy_parameters(
    strategy_name="LargeOrderFollowing",
    optimization_config=optimization_config
)
```

## 📁 文件结构

```
services/strategy_service/backtesting/
├── backtest_engine.py          # 核心回测引擎
├── strategy_adapter.py         # 策略适配器
├── backtest_manager.py         # 回测管理器
├── examples/
│   └── backtest_examples.py    # 使用示例
└── README.md                   # 本文档
```

## ⚠️ 注意事项

### 1. 数据源限制
- 当前使用vnpy内置数据源
- 历史数据可能有限
- 建议后续接入专业数据源

### 2. 策略适配
- ARBIG策略需要适配到vnpy格式
- 部分功能可能需要调整
- 建议先用简单策略测试

### 3. 性能考虑
- 回测计算量较大
- 批量回测需要时间
- 建议合理设置回测周期

### 4. 结果解释
- 回测结果仅供参考
- 实盘效果可能不同
- 需要考虑交易成本和滑点

## 🐛 故障排除

### 问题1: vnpy_ctastrategy导入失败
```bash
# 解决方案
pip install vnpy_ctastrategy
# 或者
conda install -c vnpy vnpy_ctastrategy
```

### 问题2: 策略适配失败
```python
# 检查策略是否继承正确的基类
from services.strategy_service.core.cta_template import ARBIGCtaTemplate

class YourStrategy(ARBIGCtaTemplate):
    pass
```

### 问题3: 历史数据不足
```python
# 使用模拟数据进行测试
# 或者接入外部数据源
```

### 问题4: 回测结果异常
```python
# 检查策略参数设置
# 检查回测时间范围
# 查看日志输出
```

## 📞 技术支持

如果遇到问题，请：

1. 查看日志输出
2. 检查策略参数设置
3. 验证数据源可用性
4. 参考示例代码

## 🔄 后续计划

- [ ] 接入更多数据源
- [ ] 优化策略适配器
- [ ] 增加更多性能指标
- [ ] 支持实时回测
- [ ] 增加可视化图表

---

**注意**: 回测结果仅供参考，实际交易请谨慎决策。
