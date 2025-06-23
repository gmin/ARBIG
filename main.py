"""
主控制器
整合事件引擎、数据管理器和策略，提供统一的启动和配置接口
"""

import time
import yaml
from typing import Dict, Any
from core.event_engine import EventEngine
from core.data import DataManager
from core.constants import *
from strategies.spread_arbitrage import SpreadArbitrageStrategy
from strategies.shfe_quant import SHFEQuantStrategy

class MainController:
    """
    主控制器
    负责启动和管理整个交易系统
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化主控制器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        
        # 初始化事件引擎
        persist_path = self.config.get('event_persist_path', 'events.jsonl')
        self.event_engine = EventEngine(persist_path=persist_path)
        
        # 初始化数据管理器
        self.data_manager = DataManager(self.config.get('data', {}))
        
        # 策略列表
        self.strategies = []
        
        # 注册事件处理函数
        self._register_handlers()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"配置文件 {config_path} 不存在，使用默认配置")
            return self._get_default_config()
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return self._get_default_config()
            
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
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
                }
            ]
        }
        
    def _register_handlers(self):
        """注册事件处理函数"""
        # 注册数据管理器的事件处理
        self.event_engine.register(TICK_EVENT, self._on_tick)
        self.event_engine.register(BAR_EVENT, self._on_bar)
        
        # 注册信号处理
        self.event_engine.register(SIGNAL_EVENT, self._on_signal)
        
        # 注册日志处理
        self.event_engine.register(LOG_EVENT, self._on_log)
        self.event_engine.register(ERROR_EVENT, self._on_error)
        
    def _on_tick(self, event):
        """处理Tick事件"""
        # 这里可以添加数据验证、风控等逻辑
        pass
        
    def _on_bar(self, event):
        """处理K线事件"""
        pass
        
    def _on_signal(self, event):
        """处理策略信号"""
        signal_data = event.data
        strategy_name = signal_data.get('strategy_name')
        data = signal_data.get('data', {})
        
        print(f"[MainController] 收到策略信号 - {strategy_name}: {data}")
        
        # 这里可以添加信号执行逻辑
        # 如发送订单、风控检查等
        
    def _on_log(self, event):
        """处理日志事件"""
        log_data = event.data
        print(f"[LOG] {log_data}")
        
    def _on_error(self, event):
        """处理错误事件"""
        error_data = event.data
        print(f"[ERROR] {error_data}")
        
    def load_strategies(self):
        """加载策略"""
        strategies_config = self.config.get('strategies', [])
        
        for strategy_config in strategies_config:
            strategy_name = strategy_config.get('name')
            strategy_type = strategy_config.get('type')
            config = strategy_config.get('config', {})
            
            if strategy_type == 'spread_arbitrage':
                strategy = SpreadArbitrageStrategy(
                    name=strategy_name,
                    event_engine=self.event_engine,
                    config=config
                )
            elif strategy_type == 'shfe_quant':
                strategy = SHFEQuantStrategy(
                    name=strategy_name,
                    event_engine=self.event_engine,
                    config=config
                )
            else:
                print(f"未知的策略类型: {strategy_type}")
                continue
                
            self.strategies.append(strategy)
            print(f"加载策略: {strategy_name} ({strategy_type})")
            
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
        self.load_strategies()
        
        # 启动策略
        for strategy in self.strategies:
            strategy.start()
            
        print("交易系统启动完成")
        return True
        
    def stop(self):
        """停止系统"""
        print("停止交易系统...")
        
        # 停止策略
        for strategy in self.strategies:
            strategy.stop()
            
        # 断开数据源
        self.data_manager.disconnect()
        
        # 停止事件引擎
        self.event_engine.stop()
        
        print("交易系统已停止")
        
    def run(self):
        """运行系统"""
        try:
            if self.start():
                print("系统运行中，按 Ctrl+C 停止...")
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            print("\n收到停止信号")
        finally:
            self.stop()

if __name__ == "__main__":
    # 创建并运行主控制器
    controller = MainController()
    controller.run()
