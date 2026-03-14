# ARBIG 策略使用指南

## 策略总览

当前代码中的可用策略以 `services/strategy_service/strategies/` 目录为准。  
截至当前版本，实际可用的核心策略如下：

### 测试验证类

- `SystemIntegrationTestStrategy`
  - 用途：验证策略服务、交易服务、Web 监控链路是否正常
  - 特点：更适合作为系统联调和回归测试入口

### 技术分析类

- `MaRsiComboStrategy`
  - 用途：基于均线与 RSI 的黄金期货技术策略
  - 特点：参数清晰，适合作为基础技术策略参考

- `MultiModeAdaptiveStrategy`
  - 用途：在趋势、均值回归、突破等模式之间切换
  - 特点：结构更综合，适合验证多模式框架

- `BreakoutStrategy`
  - 用途：突破型交易
  - 特点：更偏趋势延续和波动放大场景

- `MeanReversionStrategy`
  - 用途：均值回归交易
  - 特点：更适合价格偏离后的回归场景

## 推荐使用顺序

建议按“先验证链路，再测试业务策略”的顺序推进：

1. `SystemIntegrationTestStrategy`
   - 先验证服务启动、行情获取、信号发送、订单链路

2. `MaRsiComboStrategy`
   - 作为第一批业务策略测试对象
   - 参数相对直观，便于观察策略逻辑和风控效果

3. `MultiModeAdaptiveStrategy`
   - 在基础链路稳定后测试
   - 适合观察复杂参数对不同行情环境的适应性

4. `BreakoutStrategy` / `MeanReversionStrategy`
   - 作为补充策略测试
   - 用于验证不同风格策略在同一系统下的表现

## 常见参数

不同策略参数不完全一致，但以下参数在当前策略中较常见：

| 参数名 | 说明 | 常见范围 |
| -------- | ------ | ---------- |
| `trade_volume` | 单次交易手数 | `1-3` |
| `max_position` | 最大持仓 | `3-10` |
| `signal_interval` | 信号间隔（秒） | `30-300` |
| `ma_short` | 短周期均线 | `5-10` |
| `ma_long` | 长周期均线 | `15-30` |
| `rsi_period` | RSI 周期 | `14` |
| `stop_loss_pct` | 止损比例 | `0.005-0.05` |
| `take_profit_pct` | 止盈比例 | `0.008-0.08` |

实际参数定义请直接参考各策略文件中的 `STRATEGY_TEMPLATE` 或类默认参数。

## 测试建议

### 环境检查

在测试策略前，建议先确认：

```bash
curl http://localhost:8001/health
curl http://localhost:8002/status
curl http://localhost:8000/  # 或直接打开 Web 页面
```

### 建议步骤

1. 先启动 `SystemIntegrationTestStrategy`
   - 确认服务间调用链正常
   - 确认日志、持仓、状态查询都能正常返回

2. 再逐个测试业务策略
   - 每次只启一个新策略
   - 先用小仓位和保守参数

3. 观察关键指标
   - 信号频率
   - 订单执行成功率
   - 持仓同步准确性
   - 日志是否完整

## 使用注意事项

### 风险控制

- 建议始终从小仓位开始测试
- 不同策略的止损止盈机制并不完全一致
- 非交易时间的 CTP 异常不一定代表策略本身有问题

### 监控建议

- 通过 `http://localhost/strategy` 查看策略中心
- 通过 `http://localhost/trading_logs` 查看交易日志
- 通过 `http://localhost:8002/docs` 查看策略服务接口

### 紧急处理

- 当前 Web 端保留“紧急停止”能力
- 如需停止策略，优先使用策略中心或紧急停止接口
- Web 端当前不再承担手动下单和平仓入口

## 参考位置

- 策略代码：`services/strategy_service/strategies/`
- 策略服务入口：`services/strategy_service/main.py`
- 策略引擎：`services/strategy_service/core/strategy_engine.py`
- 策略编码规范：`docs/strategies/STRATEGY_CODE_STANDARDS.md`

---

最后更新：2026-03-13  
文档版本：v3.0
