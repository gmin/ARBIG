#!/usr/bin/env python3
"""
策略离线测试框架
用于在非交易时间测试各种策略的基本功能
包括策略初始化、参数配置、信号生成等功能验证
"""

import sys
import os
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Type
import asyncio

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from vnpy.trader.object import TickData, BarData
from vnpy.trader.constant import Exchange
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from utils.logger import get_logger

logger = get_logger(__name__)


class MockSignalSender:
    """模拟信号发送器"""
    
    def __init__(self):
        self.signals = []
        
    def send_signal(self, signal_data: dict):
        """接收策略发送的信号"""
        signal_data['timestamp'] = datetime.now().isoformat()
        self.signals.append(signal_data)
        logger.info(f"📡 收到信号: {signal_data}")
        
    def get_signals(self) -> List[dict]:
        """获取所有接收到的信号"""
        return self.signals.copy()
        
    def clear_signals(self):
        """清空信号记录"""
        self.signals.clear()


class MockDataGenerator:
    """模拟行情数据生成器"""
    
    def __init__(self, symbol: str = "au2510", base_price: float = 500.0):
        self.symbol = symbol
        self.base_price = base_price
        self.current_price = base_price
        self.tick_count = 0
        self.bar_count = 0
        
    def generate_tick(self) -> TickData:
        """生成模拟tick数据"""
        # 价格随机波动 ±0.5%
        price_change = random.uniform(-0.005, 0.005)
        self.current_price = self.current_price * (1 + price_change)
        
        # 确保价格在合理范围内
        self.current_price = max(self.base_price * 0.8, 
                               min(self.base_price * 1.2, self.current_price))
        
        self.tick_count += 1
        
        tick = TickData(
            symbol=self.symbol,
            exchange=Exchange.SHFE,
            datetime=datetime.now(),
            gateway_name="mock",
            last_price=round(self.current_price, 2),
            volume=random.randint(1, 100),
            bid_price_1=round(self.current_price - 0.02, 2),
            ask_price_1=round(self.current_price + 0.02, 2),
            bid_volume_1=random.randint(10, 50),
            ask_volume_1=random.randint(10, 50)
        )
        
        return tick
        
    def generate_bar(self, interval_minutes: int = 1) -> BarData:
        """生成模拟bar数据"""
        # 生成OHLC数据
        open_price = self.current_price
        
        # 模拟价格在bar内的波动
        high_price = open_price * random.uniform(1.0, 1.01)
        low_price = open_price * random.uniform(0.99, 1.0)
        
        # 收盘价在high和low之间
        close_price = random.uniform(low_price, high_price)
        self.current_price = close_price
        
        self.bar_count += 1
        
        bar = BarData(
            symbol=self.symbol,
            exchange=Exchange.SHFE,
            datetime=datetime.now() - timedelta(minutes=interval_minutes * self.bar_count),
            interval=f"{interval_minutes}m",
            gateway_name="mock",
            open_price=round(open_price, 2),
            high_price=round(high_price, 2),
            low_price=round(low_price, 2),
            close_price=round(close_price, 2),
            volume=random.randint(100, 1000)
        )
        
        return bar


class StrategyTester:
    """策略测试器"""
    
    def __init__(self):
        self.strategies = {}
        self.test_results = {}
        
    def load_strategy(self, strategy_class: Type[ARBIGCtaTemplate], 
                     strategy_name: str, symbol: str = "au2510", 
                     setting: Dict[str, Any] = None) -> bool:
        """加载策略进行测试"""
        try:
            if setting is None:
                setting = {}
                
            # 创建模拟信号发送器
            signal_sender = MockSignalSender()
            
            # 创建策略实例
            strategy = strategy_class(
                strategy_name=strategy_name,
                symbol=symbol,
                setting=setting,
                signal_sender=signal_sender
            )
            
            self.strategies[strategy_name] = {
                'strategy': strategy,
                'signal_sender': signal_sender,
                'data_generator': MockDataGenerator(symbol)
            }
            
            logger.info(f"✅ 策略加载成功: {strategy_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 策略加载失败 {strategy_name}: {e}")
            return False
    
    def test_strategy_initialization(self, strategy_name: str) -> Dict[str, Any]:
        """测试策略初始化"""
        if strategy_name not in self.strategies:
            return {"success": False, "error": "策略未加载"}
            
        try:
            strategy_info = self.strategies[strategy_name]
            strategy = strategy_info['strategy']
            
            # 测试初始化
            strategy.on_init()
            
            # 测试启动
            strategy.on_start()
            
            result = {
                "success": True,
                "strategy_name": strategy_name,
                "symbol": strategy.symbol,
                "parameters": {
                    attr: getattr(strategy, attr) 
                    for attr in dir(strategy) 
                    if not attr.startswith('_') and not callable(getattr(strategy, attr))
                },
                "methods": [
                    method for method in dir(strategy) 
                    if not method.startswith('_') and callable(getattr(strategy, method))
                ]
            }
            
            logger.info(f"✅ 策略初始化测试通过: {strategy_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 策略初始化测试失败 {strategy_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def test_strategy_data_processing(self, strategy_name: str, 
                                    tick_count: int = 50, 
                                    bar_count: int = 30) -> Dict[str, Any]:
        """测试策略数据处理能力"""
        if strategy_name not in self.strategies:
            return {"success": False, "error": "策略未加载"}
            
        try:
            strategy_info = self.strategies[strategy_name]
            strategy = strategy_info['strategy']
            signal_sender = strategy_info['signal_sender']
            data_generator = strategy_info['data_generator']
            
            # 清空之前的信号
            signal_sender.clear_signals()
            
            # 启动策略
            strategy.trading = True
            
            # 发送tick数据
            logger.info(f"📊 开始发送 {tick_count} 个tick数据...")
            for i in range(tick_count):
                tick = data_generator.generate_tick()
                strategy.on_tick(tick)
                time.sleep(0.01)  # 模拟实时数据间隔
            
            # 发送bar数据
            logger.info(f"📊 开始发送 {bar_count} 个bar数据...")
            for i in range(bar_count):
                bar = data_generator.generate_bar()
                strategy.on_bar(bar)
                time.sleep(0.01)
            
            # 收集结果
            signals = signal_sender.get_signals()
            
            result = {
                "success": True,
                "strategy_name": strategy_name,
                "data_processed": {
                    "tick_count": tick_count,
                    "bar_count": bar_count
                },
                "signals_generated": len(signals),
                "signals": signals,
                "strategy_state": {
                    "pos": getattr(strategy, 'pos', 0),
                    "trading": strategy.trading
                }
            }
            
            logger.info(f"✅ 策略数据处理测试完成: {strategy_name}")
            logger.info(f"   处理数据: {tick_count} ticks, {bar_count} bars")
            logger.info(f"   生成信号: {len(signals)} 个")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 策略数据处理测试失败 {strategy_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def test_strategy_parameters(self, strategy_name: str, 
                               parameter_variations: Dict[str, List[Any]]) -> Dict[str, Any]:
        """测试策略参数敏感性"""
        if strategy_name not in self.strategies:
            return {"success": False, "error": "策略未加载"}
            
        results = []
        
        try:
            # 获取原始策略类
            original_strategy = self.strategies[strategy_name]['strategy']
            strategy_class = type(original_strategy)
            symbol = original_strategy.symbol
            
            # 测试不同参数组合
            for param_name, values in parameter_variations.items():
                for value in values:
                    test_name = f"{strategy_name}_{param_name}_{value}"
                    test_setting = {param_name: value}
                    
                    # 加载测试策略
                    if self.load_strategy(strategy_class, test_name, symbol, test_setting):
                        # 运行快速测试
                        init_result = self.test_strategy_initialization(test_name)
                        data_result = self.test_strategy_data_processing(test_name, 20, 10)
                        
                        results.append({
                            "parameter": param_name,
                            "value": value,
                            "initialization": init_result["success"],
                            "data_processing": data_result["success"],
                            "signals_count": data_result.get("signals_generated", 0)
                        })
                        
                        # 清理测试策略
                        if test_name in self.strategies:
                            del self.strategies[test_name]
            
            return {
                "success": True,
                "strategy_name": strategy_name,
                "parameter_tests": results
            }
            
        except Exception as e:
            logger.error(f"❌ 策略参数测试失败 {strategy_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def run_comprehensive_test(self, strategy_name: str) -> Dict[str, Any]:
        """运行综合测试"""
        logger.info(f"🚀 开始综合测试: {strategy_name}")
        
        results = {}
        
        # 1. 初始化测试
        logger.info("1️⃣ 测试策略初始化...")
        results['initialization'] = self.test_strategy_initialization(strategy_name)
        
        # 2. 数据处理测试
        logger.info("2️⃣ 测试数据处理...")
        results['data_processing'] = self.test_strategy_data_processing(strategy_name)
        
        # 3. 参数测试（如果策略有可调参数）
        strategy = self.strategies[strategy_name]['strategy']
        testable_params = self._get_testable_parameters(strategy)
        
        if testable_params:
            logger.info("3️⃣ 测试参数敏感性...")
            results['parameter_sensitivity'] = self.test_strategy_parameters(
                strategy_name, testable_params
            )
        
        # 4. 生成测试报告
        results['summary'] = self._generate_test_summary(results)
        
        logger.info(f"✅ 综合测试完成: {strategy_name}")
        return results
    
    def _get_testable_parameters(self, strategy) -> Dict[str, List[Any]]:
        """获取可测试的参数"""
        testable_params = {}
        
        # 检查常见的策略参数
        if hasattr(strategy, 'trade_volume'):
            testable_params['trade_volume'] = [1, 2, 3]
        
        if hasattr(strategy, 'max_position'):
            testable_params['max_position'] = [3, 5, 10]
            
        if hasattr(strategy, 'signal_interval'):
            testable_params['signal_interval'] = [15, 30, 60]
            
        if hasattr(strategy, 'ma_short'):
            testable_params['ma_short'] = [3, 5, 10]
            
        if hasattr(strategy, 'ma_long'):
            testable_params['ma_long'] = [15, 20, 30]
            
        return testable_params
    
    def _generate_test_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试摘要"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "tests_run": len(results) - 1,  # 减去summary本身
            "overall_success": True
        }
        
        # 检查各项测试结果
        for test_name, result in results.items():
            if test_name == 'summary':
                continue
                
            if isinstance(result, dict) and not result.get("success", True):
                summary["overall_success"] = False
                break
        
        return summary


def load_available_strategies():
    """加载所有可用的策略类"""
    strategies = {}
    
    try:
        # SystemIntegrationTestStrategy
        from services.strategy_service.strategies.SystemIntegrationTestStrategy import SystemIntegrationTestStrategy
        strategies['SystemIntegrationTestStrategy'] = SystemIntegrationTestStrategy
        logger.info("✅ 加载策略: SystemIntegrationTestStrategy")
    except ImportError as e:
        logger.warning(f"⚠️ 无法加载 SystemIntegrationTestStrategy: {e}")
    
    try:
        # MaRsiComboStrategy
        from services.strategy_service.strategies.MaRsiComboStrategy import MaRsiComboStrategy
        strategies['MaRsiComboStrategy'] = MaRsiComboStrategy
        logger.info("✅ 加载策略: MaRsiComboStrategy")
    except ImportError as e:
        logger.warning(f"⚠️ 无法加载 MaRsiComboStrategy: {e}")
    
    try:
        from services.strategy_service.strategies.BreakoutStrategy import BreakoutStrategy
        strategies['BreakoutStrategy'] = BreakoutStrategy
        logger.info("✅ 加载策略: BreakoutStrategy")
    except ImportError as e:
        logger.warning(f"⚠️ 无法加载 BreakoutStrategy: {e}")
    
    try:
        from services.strategy_service.strategies.MeanReversionStrategy import MeanReversionStrategy
        strategies['MeanReversionStrategy'] = MeanReversionStrategy
        logger.info("✅ 加载策略: MeanReversionStrategy")
    except ImportError as e:
        logger.warning(f"⚠️ 无法加载 MeanReversionStrategy: {e}")
    
    try:
        from services.strategy_service.strategies.MultiModeAdaptiveStrategy import MultiModeAdaptiveStrategy
        strategies['MultiModeAdaptiveStrategy'] = MultiModeAdaptiveStrategy
        logger.info("✅ 加载策略: MultiModeAdaptiveStrategy")
    except ImportError as e:
        logger.warning(f"⚠️ 无法加载 MultiModeAdaptiveStrategy: {e}")
    
    return strategies


def main():
    """主测试函数"""
    print("🧪 策略离线测试框架启动")
    print("=" * 50)
    
    # 创建测试器
    tester = StrategyTester()
    
    # 加载所有可用策略
    available_strategies = load_available_strategies()
    
    if not available_strategies:
        print("❌ 没有找到可测试的策略")
        return
    
    print(f"📋 找到 {len(available_strategies)} 个可测试策略:")
    for name in available_strategies.keys():
        print(f"  - {name}")
    
    print("\n🚀 开始测试所有策略...")
    print("=" * 50)
    
    all_results = {}
    
    # 逐个测试策略
    for strategy_name, strategy_class in available_strategies.items():
        print(f"\n📊 测试策略: {strategy_name}")
        print("-" * 30)
        
        # 加载策略
        if tester.load_strategy(strategy_class, strategy_name):
            # 运行综合测试
            results = tester.run_comprehensive_test(strategy_name)
            all_results[strategy_name] = results
            
            # 显示测试结果
            success = results.get('summary', {}).get('overall_success', False)
            status = "✅ 通过" if success else "❌ 失败"
            print(f"结果: {status}")
            
            # 显示信号生成情况
            data_result = results.get('data_processing', {})
            if data_result.get('success'):
                signals_count = data_result.get('signals_generated', 0)
                print(f"信号生成: {signals_count} 个")
        else:
            print(f"❌ 策略加载失败: {strategy_name}")
    
    # 生成最终报告
    print("\n📊 测试总结")
    print("=" * 50)
    
    total_strategies = len(available_strategies)
    successful_strategies = sum(
        1 for results in all_results.values() 
        if results.get('summary', {}).get('overall_success', False)
    )
    
    print(f"总策略数: {total_strategies}")
    print(f"测试通过: {successful_strategies}")
    print(f"测试失败: {total_strategies - successful_strategies}")
    print(f"成功率: {successful_strategies/total_strategies*100:.1f}%")
    
    # 详细结果
    print("\n📋 详细结果:")
    for strategy_name, results in all_results.items():
        success = results.get('summary', {}).get('overall_success', False)
        status = "✅" if success else "❌"
        
        data_result = results.get('data_processing', {})
        signals = data_result.get('signals_generated', 0) if data_result.get('success') else 0
        
        print(f"  {status} {strategy_name}: {signals} 个信号")
    
    print(f"\n🎉 测试完成！时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
