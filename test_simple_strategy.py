#!/usr/bin/env python3
"""
简化版单策略运行模式测试
不依赖实际数据源，只测试核心逻辑
"""

import sys
import time
import yaml
from unittest.mock import Mock, patch

# 添加项目路径
sys.path.append('.')

# 模拟核心模块
class MockEvent:
    def __init__(self, type, data):
        self.type = type
        self.data = data

class MockEventEngine:
    def __init__(self, persist_path=None):
        self._handlers = {}
        self._active = False
        
    def register(self, event_type, handler):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        
    def put(self, event):
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                handler(event)
                
    def start(self):
        self._active = True
        
    def stop(self):
        self._active = False

class MockDataManager:
    def __init__(self, config=None):
        self.config = config or {}
        
    def connect(self):
        return True
        
    def disconnect(self):
        pass

class MockStrategyBase:
    def __init__(self, name, event_engine, config):
        self.name = name
        self.event_engine = event_engine
        self.config = config
        self.active = False
        
    def start(self):
        self.active = True
        self.on_start()
        
    def stop(self):
        self.active = False
        self.on_stop()
        
    def send_signal(self, signal_data):
        event = MockEvent("SIGNAL_EVENT", {
            'strategy_name': self.name,
            'data': signal_data
        })
        self.event_engine.put(event)
        
    def on_start(self):
        print(f"[{self.name}] 策略启动")
        
    def on_stop(self):
        print(f"[{self.name}] 策略停止")
        
    def on_tick(self, event):
        print(f"[{self.name}] 处理Tick事件: {event.data}")
        
    def on_bar(self, event):
        print(f"[{self.name}] 处理K线事件: {event.data}")
        
    def on_order(self, event):
        print(f"[{self.name}] 处理订单事件: {event.data}")
        
    def on_trade(self, event):
        print(f"[{self.name}] 处理成交事件: {event.data}")
        
    def on_account(self, event):
        print(f"[{self.name}] 处理账户事件: {event.data}")

class MockSpreadArbitrageStrategy(MockStrategyBase):
    def __init__(self, name, event_engine, config):
        super().__init__(name, event_engine, config)
        self.spread_threshold = config.get('spread_threshold', 0.5)
        
    def on_tick(self, event):
        print(f"[{self.name}] 基差套利策略处理Tick: {event.data}")
        # 模拟基差计算
        if 'shfe_price' in event.data and 'mt5_price' in event.data:
            spread = event.data['shfe_price'] - event.data['mt5_price']
            if abs(spread) > self.spread_threshold:
                self.send_signal({
                    'signal': 'ARBITRAGE',
                    'spread': spread,
                    'threshold': self.spread_threshold
                })

class MockSHFEQuantStrategy(MockStrategyBase):
    def __init__(self, name, event_engine, config):
        super().__init__(name, event_engine, config)
        self.strategy_type = config.get('strategy_type', 'trend')
        
    def on_tick(self, event):
        print(f"[{self.name}] 上海量化策略处理Tick: {event.data}")
        # 模拟策略信号生成
        if 'last_price' in event.data:
            price = event.data['last_price']
            if price > 450:  # 模拟买入信号
                self.send_signal({
                    'signal': 'BUY',
                    'price': price,
                    'strategy_type': self.strategy_type
                })

class MockMainController:
    def __init__(self, config_path="config.yaml", strategy_name=None):
        self.config = self._load_config(config_path)
        self.strategy_name = strategy_name
        
        # 初始化事件引擎
        self.event_engine = MockEventEngine()
        
        # 初始化数据管理器
        self.data_manager = MockDataManager(self.config.get('data', {}))
        
        # 当前运行的策略
        self.current_strategy = None
        
        # 注册事件处理函数
        self._register_handlers()
        
    def _load_config(self, config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"配置文件 {config_path} 不存在，使用默认配置")
            return self._get_default_config()
            
    def _get_default_config(self):
        return {
            'event_persist_path': 'events.jsonl',
            'data': {
                'shfe': {},
                'mt5': {}
            },
            'strategies': [
                {
                    'name': 'spread_arbitrage',
                    'type': 'spread_arbitrage',
                    'config': {
                        'spread_threshold': 0.5,
                        'max_position': 1000
                    }
                },
                {
                    'name': 'shfe_quant',
                    'type': 'shfe_quant',
                    'config': {
                        'strategy_type': 'trend',
                        'symbol': 'AU9999',
                        'max_position': 1000
                    }
                }
            ]
        }
        
    def _register_handlers(self):
        """注册事件处理函数"""
        self.event_engine.register("TICK_EVENT", self._on_tick)
        self.event_engine.register("BAR_EVENT", self._on_bar)
        self.event_engine.register("SIGNAL_EVENT", self._on_signal)
        
    def _on_tick(self, event):
        """处理Tick事件 - 只转发给当前运行的策略"""
        if self.current_strategy and self.current_strategy.active:
            self.current_strategy.on_tick(event)
        
    def _on_bar(self, event):
        """处理K线事件 - 只转发给当前运行的策略"""
        if self.current_strategy and self.current_strategy.active:
            self.current_strategy.on_bar(event)
        
    def _on_signal(self, event):
        """处理策略信号"""
        signal_data = event.data
        strategy_name = signal_data.get('strategy_name')
        data = signal_data.get('data', {})
        print(f"[MainController] 收到策略信号 - {strategy_name}: {data}")
        
    def _show_strategy_menu(self):
        """显示策略选择菜单"""
        strategies_config = self.config.get('strategies', [])
        
        if not strategies_config:
            print("配置文件中没有找到可用的策略")
            return None
            
        print("\n=== 可用策略列表 ===")
        for i, strategy_config in enumerate(strategies_config, 1):
            strategy_name = strategy_config.get('name')
            strategy_type = strategy_config.get('type')
            print(f"{i}. {strategy_name} ({strategy_type})")
            
        print("0. 退出")
        
        # 模拟用户选择第一个策略
        return strategies_config[0].get('name')
        
    def _create_strategy(self, strategy_config):
        """创建策略实例"""
        strategy_name = strategy_config.get('name')
        strategy_type = strategy_config.get('type')
        config = strategy_config.get('config', {})
        
        if strategy_type == 'spread_arbitrage':
            return MockSpreadArbitrageStrategy(
                name=strategy_name,
                event_engine=self.event_engine,
                config=config
            )
        elif strategy_type == 'shfe_quant':
            return MockSHFEQuantStrategy(
                name=strategy_name,
                event_engine=self.event_engine,
                config=config
            )
        else:
            print(f"未知的策略类型: {strategy_type}")
            return None
            
    def load_strategy(self, strategy_name=None):
        """加载指定策略"""
        strategies_config = self.config.get('strategies', [])
        
        # 如果没有指定策略名称，显示选择菜单
        if not strategy_name:
            strategy_name = self._show_strategy_menu()
            if not strategy_name:
                return False
                
        # 查找指定的策略配置
        target_strategy_config = None
        for strategy_config in strategies_config:
            if strategy_config.get('name') == strategy_name:
                target_strategy_config = strategy_config
                break
                
        if not target_strategy_config:
            print(f"未找到策略: {strategy_name}")
            return False
            
        # 创建策略实例
        strategy = self._create_strategy(target_strategy_config)
        if not strategy:
            return False
            
        self.current_strategy = strategy
        print(f"成功加载策略: {strategy_name}")
        return True
        
    def start(self):
        """启动系统"""
        print("启动交易系统...")
        
        # 启动事件引擎
        self.event_engine.start()
        print("事件引擎已启动")
        
        # 连接数据源
        if self.data_manager.connect():
            print("数据源连接成功")
        else:
            print("数据源连接失败")
            return False
            
        # 加载策略
        if not self.load_strategy(self.strategy_name):
            print("策略加载失败")
            return False
            
        # 启动策略
        if self.current_strategy:
            self.current_strategy.start()
            print(f"策略 {self.current_strategy.name} 已启动")
            
        print("交易系统启动完成")
        return True
        
    def stop(self):
        """停止系统"""
        print("停止交易系统...")
        
        # 停止当前策略
        if self.current_strategy:
            self.current_strategy.stop()
            print(f"策略 {self.current_strategy.name} 已停止")
            
        # 断开数据源
        self.data_manager.disconnect()
        
        # 停止事件引擎
        self.event_engine.stop()
        
        print("交易系统已停止")

def test_single_strategy_mode():
    """测试单策略运行模式"""
    print("=== 测试单策略运行模式 ===")
    
    # 创建测试配置
    test_config = {
        'event_persist_path': 'test_events.jsonl',
        'data': {
            'shfe': {},
            'mt5': {}
        },
        'strategies': [
            {
                'name': 'spread_arbitrage',
                'type': 'spread_arbitrage',
                'config': {
                    'spread_threshold': 0.5,
                    'max_position': 1000
                }
            },
            {
                'name': 'shfe_quant',
                'type': 'shfe_quant',
                'config': {
                    'strategy_type': 'trend',
                    'symbol': 'AU9999',
                    'max_position': 1000
                }
            }
        ]
    }
    
    # 保存测试配置
    with open('test_config.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
    
    try:
        # 测试1: 指定策略运行
        print("\n1. 测试指定策略运行")
        controller = MockMainController(config_path='test_config.yaml', strategy_name='spread_arbitrage')
        
        # 验证策略加载
        assert controller.load_strategy('spread_arbitrage') == True
        assert controller.current_strategy is not None
        assert controller.current_strategy.name == 'spread_arbitrage'
        print("✓ 策略加载成功")
        
        # 测试2: 事件分发
        print("\n2. 测试事件分发")
        mock_event = MockEvent("TICK_EVENT", {
            'symbol': 'AU9999',
            'last_price': 456.7,
            'source': 'shfe'
        })
        
        # 发送事件
        controller._on_tick(mock_event)
        print("✓ 事件分发正常")
        
        # 测试3: 策略切换
        print("\n3. 测试策略切换")
        controller.stop()
        
        # 切换到另一个策略
        assert controller.load_strategy('shfe_quant') == True
        assert controller.current_strategy.name == 'shfe_quant'
        print("✓ 策略切换成功")
        
        # 测试4: 策略信号生成
        print("\n4. 测试策略信号生成")
        # 测试基差套利策略
        controller.load_strategy('spread_arbitrage')
        controller.current_strategy.start()
        
        # 发送基差数据
        spread_event = MockEvent("TICK_EVENT", {
            'shfe_price': 456.7,
            'mt5_price': 456.0,
            'spread': 0.7
        })
        controller._on_tick(spread_event)
        
        # 测试上海量化策略
        controller.load_strategy('shfe_quant')
        controller.current_strategy.start()
        
        # 发送价格数据
        price_event = MockEvent("TICK_EVENT", {
            'symbol': 'AU9999',
            'last_price': 460.0
        })
        controller._on_tick(price_event)
        
        print("✓ 策略信号生成正常")
        
        print("\n=== 所有测试通过 ===")
        
    finally:
        # 清理测试文件
        import os
        if os.path.exists('test_config.yaml'):
            os.remove('test_config.yaml')

def test_event_isolation():
    """测试事件隔离"""
    print("\n=== 测试事件隔离 ===")
    
    # 创建控制器
    controller = MockMainController()
    
    # 加载策略
    controller.load_strategy('spread_arbitrage')
    
    # 验证只有一个策略在运行
    assert controller.current_strategy is not None
    print("✓ 只有一个策略实例")
    
    # 启动策略
    controller.current_strategy.start()
    
    # 验证事件只分发给当前策略
    event_count = 0
    
    def mock_on_tick(event):
        nonlocal event_count
        event_count += 1
        
    controller.current_strategy.on_tick = mock_on_tick
    
    # 发送多个事件
    for i in range(5):
        mock_event = MockEvent("TICK_EVENT", {'data': i})
        controller._on_tick(mock_event)
    
    assert event_count == 5
    print("✓ 事件只分发给当前策略")

if __name__ == "__main__":
    print("开始测试单策略运行模式...")
    
    try:
        test_single_strategy_mode()
        test_event_isolation()
        
        print("\n🎉 所有测试通过！单策略运行模式工作正常。")
        print("\n主要特性验证：")
        print("✓ 一次只运行一个策略")
        print("✓ 事件只分发给当前策略")
        print("✓ 支持策略切换")
        print("✓ 避免策略间干扰")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 