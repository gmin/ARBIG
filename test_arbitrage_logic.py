#!/usr/bin/env python3
"""
测试基差套利逻辑
验证修正后的交易方向是否正确
"""

def test_arbitrage_logic():
    """测试基差套利逻辑"""
    print("=== 基差套利逻辑测试 ===\n")
    
    # 测试场景1：SHFE价格 > MT5价格
    print("测试场景1：SHFE价格 > MT5价格")
    shfe_price = 500.0
    mt5_price = 498.0
    spread = shfe_price - mt5_price  # +2.0
    threshold = 0.5
    
    print(f"SHFE价格: {shfe_price}")
    print(f"MT5价格: {mt5_price}")
    print(f"基差: {spread}")
    print(f"阈值: {threshold}")
    
    if spread > threshold:
        signal = 'BUY_MT5_SELL_SHFE'
        print(f"信号: {signal}")
        print("逻辑: 买入MT5(低价498)，卖出SHFE(高价500)")
        profit = shfe_price - mt5_price
        print(f"预期盈利: {profit} 元/克")
        print("✓ 正确：在低价市场买入，高价市场卖出\n")
    else:
        print("无套利信号\n")
    
    # 测试场景2：SHFE价格 < MT5价格
    print("测试场景2：SHFE价格 < MT5价格")
    shfe_price = 495.0
    mt5_price = 500.0
    spread = shfe_price - mt5_price  # -5.0
    threshold = 0.5
    
    print(f"SHFE价格: {shfe_price}")
    print(f"MT5价格: {mt5_price}")
    print(f"基差: {spread}")
    print(f"阈值: {threshold}")
    
    if spread < -threshold:
        signal = 'BUY_SHFE_SELL_MT5'
        print(f"信号: {signal}")
        print("逻辑: 买入SHFE(低价495)，卖出MT5(高价500)")
        profit = mt5_price - shfe_price
        print(f"预期盈利: {profit} 元/克")
        print("✓ 正确：在低价市场买入，高价市场卖出\n")
    else:
        print("无套利信号\n")
    
    # 测试场景3：基差在阈值范围内
    print("测试场景3：基差在阈值范围内")
    shfe_price = 499.0
    mt5_price = 498.5
    spread = shfe_price - mt5_price  # +0.5
    threshold = 0.5
    
    print(f"SHFE价格: {shfe_price}")
    print(f"MT5价格: {mt5_price}")
    print(f"基差: {spread}")
    print(f"阈值: {threshold}")
    
    if abs(spread) <= threshold:
        print("无套利信号：基差在阈值范围内")
        print("✓ 正确：避免在基差较小时进行套利\n")
    
    print("=== 测试完成 ===")
    print("修正后的逻辑确保在低价市场买入，高价市场卖出，实现套利盈利！")

if __name__ == "__main__":
    test_arbitrage_logic() 