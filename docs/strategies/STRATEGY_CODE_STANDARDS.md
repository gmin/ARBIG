# ARBIG策略代码规范

## 📋 **代码结构规范**

### **文件组织**
```
services/strategy_service/strategies/
├── StrategyName.py          # 策略实现文件
├── __init__.py             # 策略导入配置
└── docs/                   # 策略文档（可选）
```

### **类命名规范**
- ✅ **文件名与类名一致**：`MaRsiComboStrategy.py` → `class MaRsiComboStrategy`
- ✅ **使用PascalCase**：`SystemIntegrationTestStrategy`
- ✅ **以Strategy结尾**：明确标识策略类

---

## 🏗️ **策略类结构**

### **标准模板**
```python
"""
策略名称 - 策略简短描述

## 策略概述
详细的策略说明...

## 主要特点
- 特点1
- 特点2

## 技术指标
- 指标说明

## 适用场景  
- 场景说明
"""

class StrategyName(ARBIGCtaTemplate):
    """
    策略类文档字符串
    
    ## 策略逻辑
    详细的策略逻辑说明
    
    ## 参数说明
    参数的详细说明
    """
    
    # ==================== 策略参数配置 ====================
    
    # 参数分组注释
    param1 = value1    # 参数说明：详细的参数用途和建议值
    param2 = value2    # 参数说明：详细的参数用途和建议值
    
    def __init__(self, strategy_name: str, symbol: str, setting: dict, signal_sender=None, **kwargs):
        """策略初始化"""
        
    def on_init(self):
        """策略初始化回调"""
        
    def on_start(self):
        """策略启动回调"""
        
    def on_stop(self):
        """策略停止回调"""
        
    def on_tick(self, tick: TickData):
        """Tick数据处理"""
        
    def on_bar(self, bar: BarData):
        """Bar数据处理 - 主要信号生成入口"""
        
    def on_tick_impl(self, tick: TickData) -> None:
        """Tick数据处理实现（抽象方法）"""
        
    def on_bar_impl(self, bar: BarData) -> None:
        """Bar数据处理实现（抽象方法）"""
```

---

## 📝 **注释规范**

### **方法注释**
```python
def method_name(self, param: Type) -> ReturnType:
    """
    方法简短描述 - 功能概述
    
    ## 功能说明
    详细的功能说明...
    
    ## 处理流程
    1. 步骤1
    2. 步骤2
    3. 步骤3
    
    Args:
        param: 参数说明
        
    Returns:
        返回值说明
        
    Raises:
        Exception: 异常情况说明
    """
```

### **参数注释**
```python
# ==================== 参数分组标题 ====================

# 参数子分组
param_name = default_value    # 参数说明：用途、建议值、注意事项
```

### **代码块注释**
```python
# 🎯 功能标识：核心逻辑说明
if condition:
    # 详细的逻辑说明
    pass

# 🔧 优化标识：性能优化说明  
optimized_code()

# 🛡️ 风控标识：风险控制说明
risk_control()

# 📊 监控标识：数据记录说明
logging_code()
```

---

## 🎯 **策略参数规范**

### **参数分类**
1. **技术指标参数**
   - 均线周期：`ma_short`, `ma_long`
   - 振荡指标：`rsi_period`, `rsi_overbought`, `rsi_oversold`
   - 通道指标：`bollinger_period`, `bollinger_std`

2. **风控参数**
   - 止损止盈：`stop_loss_pct`, `take_profit_pct`
   - 持仓限制：`max_position`, `trade_volume`

3. **时间控制参数**
   - 信号间隔：`signal_interval`, `min_signal_interval`
   - 交易时间：`start_time`, `end_time`

### **参数命名规范**
- ✅ 使用snake_case：`ma_short`, `rsi_period`
- ✅ 语义明确：`stop_loss_pct` 而不是 `sl`
- ✅ 单位明确：`_pct`(百分比), `_interval`(间隔), `_period`(周期)

---

## 🔧 **代码质量要求**

### **必需方法**
- ✅ `on_init()` - 策略初始化
- ✅ `on_start()` - 策略启动  
- ✅ `on_stop()` - 策略停止
- ✅ `on_tick()` - Tick数据处理
- ✅ `on_bar()` - Bar数据处理（主要信号生成）
- ✅ `on_tick_impl()` - 抽象方法实现
- ✅ `on_bar_impl()` - 抽象方法实现

### **推荐方法**
- 🔧 `_generate_signal()` - 信号生成逻辑
- 🛡️ `_check_risk()` - 风控检查
- 📊 `_calculate_indicators()` - 技术指标计算
- 💾 `get_strategy_status()` - 策略状态查询

### **日志规范**
```python
# 使用统一的日志格式
self.write_log(f"🎯 [策略名称] 信号类型: 详细信息")
self.write_log(f"🔧 [策略名称] 优化信息: 详细说明")
self.write_log(f"🛡️ [策略名称] 风控信息: 详细说明")
self.write_log(f"📊 [策略名称] 监控信息: 详细数据")
```

---

## 📊 **性能要求**

### **响应时间**
- Tick处理：< 1ms
- Bar处理：< 10ms
- 信号生成：< 50ms

### **内存使用**
- ArrayManager大小：建议100-200
- 历史数据缓存：控制在合理范围
- 避免内存泄漏

### **API调用**
- 持仓查询：合理使用缓存，避免频繁调用
- 信号发送：异步处理，不阻塞主流程

---

## 🛡️ **风控要求**

### **必需风控**
- ✅ **持仓限制**：`max_position` 参数
- ✅ **交易量控制**：`trade_volume` 参数
- ✅ **时间间隔控制**：避免过度交易

### **推荐风控**
- 🔧 **止损止盈**：`stop_loss_pct`, `take_profit_pct`
- 📊 **实时持仓查询**：与交易服务同步
- 💾 **持仓缓存机制**：减少服务压力

---

## 🧪 **测试要求**

### **基础测试**
- ✅ 策略类结构检查
- ✅ 参数配置验证
- ✅ 方法调用测试

### **功能测试**
- 🔧 数据处理能力测试
- 📊 信号生成逻辑测试
- 🛡️ 风控机制验证

### **集成测试**
- 🚀 与交易服务集成测试
- 📈 实盘环境验证
- 💰 资金安全验证

---

## 📚 **开发流程**

### **策略开发步骤**
1. **需求分析**：明确策略目标和适用场景
2. **技术设计**：选择合适的技术指标和逻辑
3. **代码实现**：按照规范实现策略类
4. **离线测试**：使用测试框架验证基础功能
5. **模拟测试**：在模拟环境测试策略表现
6. **实盘测试**：小仓位实盘验证
7. **生产部署**：正式投入使用

### **代码审查要点**
- 📋 代码结构是否符合规范
- 🔧 注释是否清晰详细
- 🛡️ 风控机制是否完善
- 📊 日志记录是否充分
- 🚀 性能是否满足要求

---

**文档版本**：v1.0  
**最后更新**：2025-08-30  
**维护者**：ARBIG开发团队  
