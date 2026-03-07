# ARBIG 策略全集分析文档

## 📋 文档概述

**版本**: v3.0
**创建日期**: 2025-08-17
**更新日期**: 2026-03-07
**交易品种**: 上期所黄金期货（au2604）
**策略框架**: ARBIGCtaTemplate
**交易级别**: K线级别（非Tick高频）

---

## 🎯 现有策略全览

### 策略架构

```
ARBIGCtaTemplate（基类）
├── MaRsiComboStrategy        # 趋势跟踪
├── BreakoutStrategy          # 突破交易
├── MeanReversionStrategy     # 均值回归
├── MultiModeAdaptiveStrategy # 多模态切换（待改造为调度器）
└── SystemIntegrationTestStrategy  # 系统测试（非交易策略）
```

### 策略分类

| 编号 | 策略 | 文件 | 类型 | 适用行情 | 设计文档 |
|------|------|------|------|----------|----------|
| 1 | **MaRsiComboStrategy** | `MaRsiComboStrategy.py` | 趋势跟踪 | 单边趋势 | `MaRsiComboStrategy_design.md` |
| 2 | **BreakoutStrategy** | `BreakoutStrategy.py` | 突破交易 | 趋势启动 | `BreakoutStrategy_design.md` |
| 3 | **MeanReversionStrategy** | `MeanReversionStrategy.py` | 均值回归 | 震荡整理 | `MeanReversionStrategy_design.md` |
| 4 | **MultiModeAdaptiveStrategy** | `MultiModeAdaptiveStrategy.py` | 多模态 | 全行情 | `MultiModeAdaptiveStrategy_design.md` |
| 5 | SystemIntegrationTestStrategy | `SystemIntegrationTestStrategy.py` | 测试 | — | — |

### 已清理的策略（不再使用）

以下策略已从项目中移除，仅保留在 `__pycache__` 历史记录中：
- ~~LargeOrderFollowingStrategy~~（大单跟踪 — Tick级，已弃用）
- ~~VWAPDeviationReversionStrategy~~（VWAP偏离 — Tick级，已弃用）
- ~~EnhancedMaRsiComboStrategy~~（增强均线RSI — 与MaRsiCombo重复，已弃用）

---

## 📊 核心策略对比

### 三大交易策略对比

| | **MaRsiComboStrategy** | **BreakoutStrategy** | **MeanReversionStrategy** |
|---|---|---|---|
| **策略类型** | 趋势跟踪 | 突破交易 | 均值回归 |
| **信号来源** | MA5/MA20金叉死叉 + RSI过滤 | 布林带突破 + N根K线确认 | 布林带触及 + RSI极端 |
| **入场时机** | 趋势确认后（偏晚） | 趋势启动时（偏早） | 价格偏离均值时（逆势） |
| **止盈方式** | 固定百分比 | 固定百分比 | 布林带中轨（动态） |
| **止损幅度** | 0.6% | 0.8% | 0.6% |
| **RSI阈值** | 30/70 | 30/70（过滤用） | 25/75（更极端） |
| **确认机制** | RSI辅助 | 2根K线回踩确认 | 2根K线连续确认 |
| **假信号过滤** | RSI过滤 | 回踩容忍度 | 带宽过滤（趋势市不交易）|
| **适合行情** | 单边趋势 | 波动率放大 | 震荡整理 |
| **对锁** | ✅ 允许 | ❌ 不允许 | ❌ 不允许 |
| **反向平仓** | 盈利才平，亏损保留 | 强制平仓 | 强制平仓 |
| **持仓持久化** | ✅ | ✅ | ✅ |

### 互补性分析

```
      趋势市                  震荡市
  ←─────────────────────────────────→
  MaRsiComboStrategy    MeanReversionStrategy
  BreakoutStrategy      ↑ 带宽过滤保护
  ↑                     ↑
  趋势确认后入场        价格偏离均值时逆势入场
  趋势启动时入场        回到中轨止盈
```

- **MaRsiCombo + Breakout**：都是顺势交易，入场时机不同（确认后 vs 启动时）
- **MeanReversion**：逆势交易，与趋势策略形成互补
- **三者组合**：通过 MultiModeAdaptiveStrategy 调度，覆盖全行情

---

## 🔧 共同技术架构

### 框架规范

所有策略都继承 `ARBIGCtaTemplate`，遵循以下规范：

1. **Hook 方法**：使用 `on_bar_impl` / `on_tick_impl` / `on_trade_impl`，不覆盖父类方法
2. **持仓管理**：`long_pos` / `short_pos` / `long_price` / `short_price` 由父类 `on_trade()` 统一更新
3. **持仓持久化**：`data/real_positions_{name}_{symbol}.json`
4. **智能平仓**：上期所今昨仓自动拆分（优先平昨仓）
5. **交易时间**：SHFE 正确时段（09:00-10:15, 10:30-11:30, 13:30-15:00, 21:00-02:30）

### 文件结构

```
services/strategy_service/strategies/
├── MaRsiComboStrategy.py              # 趋势跟踪策略
├── MaRsiComboStrategy_design.md       # 趋势跟踪设计文档
├── BreakoutStrategy.py                # 突破交易策略
├── BreakoutStrategy_design.md         # 突破交易设计文档
├── MeanReversionStrategy.py           # 均值回归策略
├── MeanReversionStrategy_design.md    # 均值回归设计文档
├── MultiModeAdaptiveStrategy.py       # 多模态切换策略
├── MultiModeAdaptiveStrategy_design.md # 多模态设计文档
├── SystemIntegrationTestStrategy.py   # 系统集成测试
├── __init__.py                        # 策略注册
└── STRATEGY_DESIGN_DOCUMENT.md        # 本文档（策略总览）
```

---

## 🎯 策略发展路线图

### 当前阶段：独立策略完善 ✅

- [x] MaRsiComboStrategy 开发 + 优化
- [x] BreakoutStrategy 开发 + Bug修复
- [x] MeanReversionStrategy 开发 + Bug修复
- [x] 全策略 Bug 审查 + 修复
- [x] 设计文档编写

### 下一阶段：回测验证

- [ ] 三个策略独立回测
- [ ] 比较收益率、胜率、最大回撤等指标
- [ ] 根据回测结果调优参数

### 最终阶段：多模态整合

- [ ] 实现市场环境自动识别算法（波动率 + 趋势强度）
- [ ] 改造 MultiModeAdaptiveStrategy 为调度器
- [ ] 根据行情自动委托给对应策略执行
- [ ] 集成测试 + 参数优化

---

## ⚠️ 风险控制要点

### 通用风控规则

1. **严格止损**：单笔损失不超过 0.6-0.8%
2. **仓位限制**：单方向最大 3 手
3. **反向信号**：强制平仓（BreakoutStrategy / MeanReversionStrategy）
4. **交易时间**：严格限制在 SHFE 交易时段
5. **持仓持久化**：每次成交后保存，重启不丢失

### 策略特有风控

| 策略 | 特有风控 |
|------|----------|
| MaRsiComboStrategy | ATR动态加仓阈值、盈利才平亏损保留 |
| BreakoutStrategy | 假突破回踩容忍度过滤、RSI极端区域不追 |
| MeanReversionStrategy | 带宽过滤（趋势市不交易）、中轨动态止盈 |

---

**文档版本**: v3.0
**最后更新**: 2026-03-07
**维护者**: ARBIG量化团队

**更新记录**:
- v3.0 (2026-03-07): 重构文档，移除已弃用策略，更新为当前四策略架构
- v2.0 (2025-08-17): 初始版本
