# ARBIG 策略代码规范

## 目的

这份文档只描述当前 `strategy_service` 下真实生效的策略开发约定。  
第一原则只有一条：**策略代码要优先服从当前框架，再谈风格统一。**

也就是说：

- 如果框架已经在父类中统一处理了生命周期、持仓更新、成交回调，就不要在子类里重复实现
- 如果某个文档模板和实际基类不一致，以源码为准，而不是以旧文档为准

## 目录与命名

当前策略代码目录：

```text
services/strategy_service/strategies/
├── StrategyName.py
└── __init__.py
```

命名要求：

- 文件名与策略类名保持一致，例如 `MaRsiComboStrategy.py`
- 类名使用 PascalCase
- 策略类统一以 `Strategy` 结尾
- 新增策略后，更新 `services/strategy_service/strategies/__init__.py`

## 基类约定

所有运行中的策略都应继承：

- `services/strategy_service/core/cta_template.py` 中的 `ARBIGCtaTemplate`

需要特别注意：

- 父类已经统一封装 `on_tick()`、`on_bar()`、`on_trade()`、`on_order()`
- 子类的主要职责是实现 `on_tick_impl()`、`on_bar_impl()`
- `on_trade_impl()`、`on_order_impl()` 是可选扩展点
- 除非有非常充分的理由，不要直接重写 `on_tick()`、`on_bar()`、`on_trade()`

原因很简单：

- 父类里已经处理了 `active` 状态判断
- 父类里已经维护了 `tick`、`bar`、`bars`
- 父类里已经统一更新 `pos`、`long_pos`、`short_pos`、均价和成交统计

如果子类再直接改这些基础回调，最容易引入重复记账、状态不一致、调试困难这三类问题。

## 推荐结构

标准策略建议包含以下部分：

```python
class StrategyName(ARBIGCtaTemplate):
    """一句话说明策略用途。"""

    # 可配置参数名列表
    parameters = [
        "trade_volume",
        "max_position",
    ]

    # 需要暴露给外部观察的变量名列表
    variables = [
        "pos",
        "long_pos",
        "short_pos",
    ]

    # 默认参数
    trade_volume = 1
    max_position = 3

    def on_init(self) -> None:
        """初始化内部状态与指标容器。"""

    def on_start(self) -> None:
        """启动时执行一次的准备逻辑。"""

    def on_stop(self) -> None:
        """停止时释放状态或输出摘要。"""

    def on_tick_impl(self, tick) -> None:
        """Tick 级别逻辑。"""

    def on_bar_impl(self, bar) -> None:
        """Bar 级别逻辑，通常是主要信号入口。"""

    def on_trade_impl(self, trade) -> None:
        """可选：成交后的附加处理。"""
```

## `STRATEGY_TEMPLATE` 约定

当前策略引擎会在加载模块时尝试读取模块级别的 `STRATEGY_TEMPLATE`。  
它不是 Python 继承层面的硬约束，但对于策略展示、参数描述和外部使用非常重要，新增策略时应提供。

建议至少包含：

```python
STRATEGY_TEMPLATE = {
    "class_name": "StrategyName",
    "file_name": "StrategyName.py",
    "description": "策略说明",
    "parameters": {
        "trade_volume": {
            "type": "int",
            "default": 1,
            "description": "每次交易手数"
        }
    }
}
```

要求：

- `class_name` 与真实类名一致
- `file_name` 与真实文件名一致
- `parameters` 中的默认值应与类中的默认参数一致
- 文案描述要简洁，不要写市场承诺式表述

## 参数规范

参数设计遵循“少而清晰”的原则。

推荐做法：

- 使用 `snake_case`
- 名称表达业务含义，不要过度缩写
- 带单位的参数显式带后缀，如 `_pct`、`_period`、`_interval`
- 默认值要保守，优先服务测试和联调

常见参数示例：

- 趋势类：`ma_short`、`ma_long`
- 震荡类：`rsi_period`、`rsi_overbought`、`rsi_oversold`
- 风控类：`stop_loss_pct`、`take_profit_pct`
- 仓位类：`trade_volume`、`max_position`
- 节流类：`signal_interval`、`min_signal_interval`

不推荐：

- 参数名只有作者自己看得懂
- 同一含义在不同策略里使用不同命名
- 默认值过激进，导致一上来就高频触发

## 注释与可读性

注释要解释“为什么”，不要机械解释“代码正在做什么”。

推荐：

- 在复杂信号判断前写 1 到 2 行注释，说明设计意图
- 在风控分支前说明这条规则防的是什么风险
- 在兼容性处理处说明背景，例如父类已更新持仓，这里不要重复改

不推荐：

- 每行代码都加注释
- 用表情符号堆砌日志和注释
- 文档字符串写得很长，但和真实实现不一致

## 生命周期与状态管理

子类应遵守以下边界：

- `on_init()`：初始化指标、缓存、内部状态
- `on_start()`：启动后的准备动作
- `on_stop()`：清理状态、输出摘要、停止内部计时器
- `on_tick_impl()`：处理 Tick 级别的实时风控或细粒度逻辑
- `on_bar_impl()`：处理 Bar 级别的主信号逻辑
- `on_trade_impl()`：只处理成交后的附加行为，不重复更新基础持仓变量

特别注意：

- `pos`、`long_pos`、`short_pos`、`long_price`、`short_price` 优先交给父类维护
- 子类如果手动改这些变量，必须非常谨慎，并写明原因

## 日志规范

日志的目标是帮助定位问题，而不是制造噪音。

建议：

- 重要状态变化才记录日志，例如信号出现、风控触发、成交后状态变化
- 日志内容先写结论，再写关键数字
- 统一使用 `self.write_log(...)`

示例：

```python
self.write_log(
    f"产生开多信号: price={bar.close_price}, rsi={self.rsi_value}, pos={self.pos}"
)
```

不建议：

- 高频路径下无条件打印大量日志
- 同一事件在多个层级重复打印
- 依赖“花哨前缀”来表达语义，而不是依赖清晰文本

## 风控要求

每个策略至少要考虑以下问题：

- 是否有限制最大持仓
- 是否限制单次交易手数
- 是否控制信号频率，避免过度交易
- 是否区分测试参数和生产参数

推荐补充：

- 止损与止盈
- 交易时段过滤
- 异常行情下的保护逻辑

## 测试要求

新增或修改策略后，至少检查：

1. 类是否能被策略引擎加载
2. `STRATEGY_TEMPLATE` 是否和类定义一致
3. 参数更新后是否真正生效
4. `on_tick_impl()` / `on_bar_impl()` 是否不会抛出明显异常
5. 成交回调后持仓状态是否合理

如果策略逻辑较复杂，还应补充：

- 不同行情场景下的信号验证
- 风控分支验证
- 启停过程验证

## 评审清单

提交前至少自查以下问题：

- 是否继承了 `ARBIGCtaTemplate`
- 是否实现了必要的 `*_impl` 方法
- 是否错误重写了父类统一回调
- 是否保持命名、参数、模板一致
- 是否足够易读
- 是否在关键决策点加了必要注释

---

文档版本：v2.0  
最后更新：2026-03-13  
维护者：ARBIG 开发团队
