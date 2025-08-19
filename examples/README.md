# ARBIG 示例代码

本目录包含ARBIG系统的使用示例和演示代码。

## 📁 目录结构

```
examples/
├── README.md              # 本文件
├── api_examples/          # API使用示例 (计划中)
├── strategy_examples/     # 策略开发示例 (计划中)
├── integration_examples/  # 集成示例 (计划中)
└── archive/              # 已过时的示例代码
    ├── trading_demo.py    # 旧的交易服务演示
    ├── account_demo.py    # 旧的账户服务演示
    ├── market_data_demo.py # 旧的行情服务演示
    └── integrated_demo.py  # 旧的集成演示
```

## ⚠️ 重要说明

**archive目录中的示例代码已过时**，它们基于已清理的单体架构代码（core.services），不适用于当前的微服务架构。

## 🚀 当前推荐的使用方式

### 1. Web界面使用 (推荐)
```bash
# 启动系统
python start_with_logs.py

# 访问Web界面
# 浏览器打开: http://localhost
```

### 2. API直接调用
```bash
# 查看API文档
# 交易服务: http://localhost:8001/docs
# 策略服务: http://localhost:8002/docs
```

### 3. 策略开发
参考 `services/strategy_service/strategies/` 目录下的现有策略实现：
- `test_strategy.py` - 简单测试策略
- `double_ma_strategy.py` - 双均线策略
- `simple_shfe_strategy.py` - 简化SHFE策略
- `shfe_quant_strategy.py` - 量化策略
- `advanced_shfe_strategy.py` - 高级策略

## 📝 计划中的新示例

我们计划添加以下新的示例代码：

### API使用示例
- HTTP客户端调用交易API
- WebSocket实时数据订阅
- 策略管理API调用

### 策略开发示例
- 自定义策略开发模板
- 技术指标使用示例
- 策略参数优化示例

### 集成示例
- 第三方系统集成
- 数据导入导出
- 监控和告警集成

## 🔄 迁移说明

如果您之前使用archive中的旧示例代码，请参考以下迁移指南：

### 旧代码 → 新架构
- `core.services.*` → 微服务API调用
- 事件驱动模式 → RESTful API模式
- 单体服务 → 微服务架构

### 具体迁移步骤
1. 将服务调用改为HTTP API调用
2. 使用Web界面进行交互操作
3. 策略开发改为继承ARBIGCtaTemplate

---

*新的示例代码正在开发中，敬请期待。如有疑问请参考项目文档或联系开发团队。*
