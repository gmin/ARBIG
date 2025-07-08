#!/usr/bin/env python3
"""
交易信号监控测试脚本
演示如何记录和跟踪交易信号
"""

import asyncio
import uuid
from datetime import datetime
from web_admin.trading_monitor import trading_monitor

async def test_signal_monitoring():
    """测试交易信号监控"""
    
    print("🧪 开始测试交易信号监控...")
    
    # 启动交易监控
    await trading_monitor.start_monitoring()
    
    # 模拟技术分析信号
    signal_1 = {
        "signal_id": str(uuid.uuid4()),
        "signal_type": "technical",
        "strategy_name": "MA_Cross_Strategy",
        "symbol": "au2508",
        "direction": "buy",
        "strength": 0.8,
        "trigger_reason": "5日均线上穿20日均线，成交量放大",
        "trigger_conditions": {
            "ma5": 774.2,
            "ma20": 773.8,
            "volume_ratio": 1.5,
            "price": 774.14,
            "cross_confirmed": True
        },
        "market_context": {
            "market_trend": "上涨",
            "volatility": "中等",
            "support_level": 770.0,
            "resistance_level": 780.0
        }
    }
    
    # 记录信号
    trading_monitor.record_trading_signal(signal_1)
    print(f"✅ 记录技术分析信号: {signal_1['trigger_reason']}")
    
    # 模拟基本面信号
    signal_2 = {
        "signal_id": str(uuid.uuid4()),
        "signal_type": "fundamental",
        "strategy_name": "News_Sentiment_Strategy",
        "symbol": "au2508",
        "direction": "buy",
        "strength": 0.6,
        "trigger_reason": "美联储鸽派言论，黄金避险需求增加",
        "trigger_conditions": {
            "news_sentiment": 0.7,
            "fed_rate_probability": 0.3,
            "dollar_index": 102.5,
            "sentiment_change": 0.2
        },
        "market_context": {
            "economic_data": "通胀数据低于预期",
            "geopolitical_risk": "中等",
            "currency_strength": "美元走弱"
        }
    }
    
    trading_monitor.record_trading_signal(signal_2)
    print(f"✅ 记录基本面信号: {signal_2['trigger_reason']}")
    
    # 模拟套利信号
    signal_3 = {
        "signal_id": str(uuid.uuid4()),
        "signal_type": "arbitrage",
        "strategy_name": "Calendar_Spread_Strategy",
        "symbol": "au2508",
        "direction": "sell",
        "strength": 0.9,
        "trigger_reason": "au2508与au2512价差异常扩大，套利机会出现",
        "trigger_conditions": {
            "spread": 15.2,
            "normal_spread": 8.5,
            "spread_zscore": 2.3,
            "liquidity_check": True
        },
        "market_context": {
            "near_month_volume": 15000,
            "far_month_volume": 8000,
            "basis_trend": "扩大"
        }
    }
    
    trading_monitor.record_trading_signal(signal_3)
    print(f"✅ 记录套利信号: {signal_3['trigger_reason']}")
    
    # 模拟风控信号
    signal_4 = {
        "signal_id": str(uuid.uuid4()),
        "signal_type": "risk_control",
        "strategy_name": "Risk_Management_System",
        "symbol": "au2508",
        "direction": "sell",
        "strength": 1.0,
        "trigger_reason": "持仓风险度超过80%，触发强制减仓",
        "trigger_conditions": {
            "risk_ratio": 0.85,
            "max_risk_ratio": 0.80,
            "position_pnl": -50000,
            "stop_loss_triggered": True
        },
        "market_context": {
            "account_balance": 2000000,
            "total_margin": 1700000,
            "unrealized_pnl": -50000
        }
    }
    
    trading_monitor.record_trading_signal(signal_4)
    print(f"✅ 记录风控信号: {signal_4['trigger_reason']}")
    
    # 等待一下让监控循环运行
    await asyncio.sleep(2)
    
    # 模拟订单执行
    order_1 = {
        "order_id": "CTP.1_test_001",
        "symbol": "au2508",
        "exchange": "SHFE",
        "direction": "buy",
        "offset": "open",
        "order_type": "limit",
        "volume": 1,
        "traded": 0,
        "price": 774.14,
        "status": "submitted",
        "signal_id": signal_1["signal_id"],
        "strategy_name": signal_1["strategy_name"],
        "trigger_reason": signal_1["trigger_reason"]
    }
    
    trading_monitor.update_order(order_1)
    print(f"✅ 创建订单并关联到信号: {order_1['order_id']}")
    
    # 模拟订单成交
    order_1["status"] = "filled"
    order_1["traded"] = 1
    trading_monitor.update_order(order_1)
    print(f"✅ 订单成交: {order_1['order_id']}")
    
    # 获取信号分析
    print("\n📊 信号分析报告:")
    print("=" * 50)
    
    analysis = trading_monitor.get_signal_analysis()
    print(f"总信号数: {analysis['total_signals']}")
    print(f"已执行信号: {analysis['executed_signals']}")
    print(f"执行率: {analysis['execution_rate']:.1%}")
    print(f"平均信号强度: {analysis['avg_strength']:.2f}")
    
    print("\n按类型分布:")
    for signal_type, count in analysis['signal_by_type'].items():
        print(f"  {signal_type}: {count}")
    
    print("\n按策略分布:")
    for strategy, count in analysis['signal_by_strategy'].items():
        print(f"  {strategy}: {count}")
    
    print("\n最近信号:")
    for signal in analysis['recent_signals'][:3]:
        print(f"  [{signal['signal_time'][:19]}] {signal['strategy_name']}")
        print(f"    类型: {signal['signal_type']} | 方向: {signal['direction']} | 强度: {signal['strength']}")
        print(f"    原因: {signal['trigger_reason']}")
        print(f"    执行: {'✅' if signal['executed'] else '⏳'}")
        print()
    
    # 获取交易概览
    print("📈 交易概览:")
    print("=" * 50)
    
    overview = trading_monitor.get_trading_overview()
    print(f"活跃订单数: {len(overview['active_orders'])}")

    recent_signals = overview.get('recent_signals', [])
    print(f"最近信号数: {len(recent_signals)}")

    if recent_signals:
        print("\n最新信号:")
        latest_signal = recent_signals[0]
        print(f"  策略: {latest_signal['strategy_name']}")
        print(f"  触发原因: {latest_signal['trigger_reason']}")
        print(f"  信号强度: {latest_signal['strength']}")
    
    print("\n🎉 交易信号监控测试完成!")

if __name__ == "__main__":
    asyncio.run(test_signal_monitoring())
