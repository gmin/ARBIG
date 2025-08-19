# 策略重命名指南

## 📋 重命名概述

为了让策略文件名更直观地反映其核心特征，我们对所有策略进行了重命名。新的命名规则遵循"核心特征_策略类型_strategy.py"的格式。

## 🔄 重命名对照表

### **已完成重命名**

| 原文件名 | 新文件名 | 核心特征 | 状态 |
|---------|---------|----------|------|
| `microstructure_strategy.py` | `large_order_following_strategy.py` | 大单跟踪 | ✅ 已重命名 |
| `mean_reversion_strategy.py` | `vwap_deviation_reversion_strategy.py` | VWAP偏离回归 | ✅ 已重命名 |

### **待重命名文件**

| 原文件名 | 建议新文件名 | 核心特征 | 优先级 |
|---------|-------------|----------|--------|
| `double_ma_strategy.py` | `ma_crossover_trend_strategy.py` | 均线交叉趋势 | 🔴 高 |
| `simple_shfe_strategy.py` | `ma_rsi_combo_strategy.py` | 均线RSI组合 | 🔴 高 |
| `shfe_quant_strategy.py` | `multi_mode_adaptive_strategy.py` | 多模式自适应 | 🟡 中 |
| `advanced_shfe_strategy.py` | `component_framework_strategy.py` | 组件框架 | 🟢 低 |
| `test_strategy.py` | `system_integration_test_strategy.py` | 系统集成测试 | 🟢 低 |

## 🎯 命名规则说明

### **命名格式**
```
[核心特征]_[策略类型]_strategy.py
```

### **核心特征词汇**
- `large_order` - 大单相关
- `vwap_deviation` - VWAP偏离
- `ma_crossover` - 均线交叉
- `ma_rsi_combo` - 均线RSI组合
- `multi_mode` - 多模式
- `component_framework` - 组件框架
- `system_integration_test` - 系统集成测试

### **策略类型词汇**
- `following` - 跟踪型
- `reversion` - 回归型
- `trend` - 趋势型
- `combo` - 组合型
- `adaptive` - 自适应型
- `framework` - 框架型
- `test` - 测试型

## 🔧 重命名操作步骤

### **步骤1: 文件重命名**
```bash
# 在 services/strategy_service/strategies/ 目录下执行
mv double_ma_strategy.py ma_crossover_trend_strategy.py
mv simple_shfe_strategy.py ma_rsi_combo_strategy.py
mv shfe_quant_strategy.py multi_mode_adaptive_strategy.py
mv advanced_shfe_strategy.py component_framework_strategy.py
mv test_strategy.py system_integration_test_strategy.py
```

### **步骤2: 类名重命名**
```python
# 在每个重命名的文件中更新类名
DoubleMaStrategy → MaCrossoverTrendStrategy
SimpleSHFEStrategy → MaRsiComboStrategy
SHFEQuantStrategy → MultiModeAdaptiveStrategy
AdvancedSHFEStrategy → ComponentFrameworkStrategy
TestStrategy → SystemIntegrationTestStrategy
```

### **步骤3: 导入引用更新**
```python
# 在策略注册文件中更新导入
from strategies.ma_crossover_trend_strategy import MaCrossoverTrendStrategy
from strategies.ma_rsi_combo_strategy import MaRsiComboStrategy
from strategies.multi_mode_adaptive_strategy import MultiModeAdaptiveStrategy
from strategies.component_framework_strategy import ComponentFrameworkStrategy
from strategies.system_integration_test_strategy import SystemIntegrationTestStrategy
```

### **步骤4: 配置文件更新**
```json
// 更新策略配置中的类名引用
{
    "strategies": [
        {
            "name": "ma_crossover_trend_au2510",
            "class": "MaCrossoverTrendStrategy",
            "file": "ma_crossover_trend_strategy.py"
        },
        {
            "name": "ma_rsi_combo_au2510", 
            "class": "MaRsiComboStrategy",
            "file": "ma_rsi_combo_strategy.py"
        }
    ]
}
```

## 📁 重命名后的目录结构

```
services/strategy_service/strategies/
├── 🎯 高收益策略
│   ├── large_order_following_strategy.py          # 大单跟踪策略
│   └── vwap_deviation_reversion_strategy.py       # VWAP偏离回归策略
├── 📈 经典策略  
│   ├── ma_crossover_trend_strategy.py             # 均线交叉趋势策略
│   ├── ma_rsi_combo_strategy.py                   # 均线RSI组合策略
│   └── multi_mode_adaptive_strategy.py            # 多模式自适应策略
├── 🔧 框架策略
│   └── component_framework_strategy.py            # 组件框架策略
├── 🧪 测试策略
│   └── system_integration_test_strategy.py        # 系统集成测试策略
└── 📚 文档
    ├── STRATEGY_DESIGN_DOCUMENT.md                # 策略设计文档
    └── STRATEGY_RENAMING_GUIDE.md                 # 本重命名指南
```

## 🎯 重命名的好处

### **1. 直观性**
- 一眼就能看出策略的核心特征
- 不需要打开文件就知道策略类型

### **2. 可维护性**
- 新团队成员容易理解
- 减少策略选择时的困惑

### **3. 扩展性**
- 为未来新策略提供命名规范
- 便于策略分类和管理

### **4. 专业性**
- 体现策略的核心竞争力
- 便于对外交流和展示

## ⚠️ 注意事项

### **重命名前的准备**
1. **备份代码**: 确保有完整的代码备份
2. **停止运行**: 暂停所有使用这些策略的服务
3. **记录依赖**: 记录所有引用这些策略的地方

### **重命名后的验证**
1. **导入测试**: 确保所有导入都能正常工作
2. **功能测试**: 验证策略功能没有受到影响
3. **配置检查**: 确保配置文件中的引用都已更新

### **团队协调**
1. **通知团队**: 提前通知所有相关人员
2. **更新文档**: 同步更新所有相关文档
3. **培训说明**: 向团队说明新的命名规则

---

**总结**: 通过这次重命名，我们的策略文件将更加直观和专业。建议按照优先级逐步完成重命名，确保系统稳定运行。
