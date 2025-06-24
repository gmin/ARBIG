"""
主控制器
整合事件引擎、数据管理器和策略，提供统一的启动和配置接口
"""

import time
import yaml
import sys
from typing import Dict, Any, Optional
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
    
    def __init__(self, config_path: str = "config.yaml", strategy_name: str = None):
        """
        初始化主控制器
        
        Args:
            config_path: 配置文件路径
            strategy_name: 指定要运行的策略名称，如果为None则提供选择菜单
        """
        self.config = self._load_config(config_path)
        self.strategy_name = strategy_name
        
        # 初始化事件引擎
        persist_path = self.config.get('event_persist_path', 'events.jsonl')
        self.event_engine = EventEngine(persist_path=persist_path)
        
        # 初始化数据管理器
        self.data_manager = DataManager(self.config.get('data', {}))
        
        # 当前运行的策略
        self.current_strategy: Optional[StrategyBase] = None
        
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
        # 只转发给当前运行的策略
        if self.current_strategy and self.current_strategy.active:
            self.current_strategy.on_tick(event)
        
    def _on_bar(self, event):
        """处理K线事件"""
        # 只转发给当前运行的策略
        if self.current_strategy and self.current_strategy.active:
            self.current_strategy.on_bar(event)
        
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
        
    def _show_strategy_menu(self) -> str:
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
        
        while True:
            try:
                choice = input("\n请选择要运行的策略 (输入数字): ").strip()
                if choice == '0':
                    return None
                    
                choice_num = int(choice)
                if 1 <= choice_num <= len(strategies_config):
                    selected_strategy = strategies_config[choice_num - 1]
                    return selected_strategy.get('name')
                else:
                    print("无效的选择，请重新输入")
            except ValueError:
                print("请输入有效的数字")
            except KeyboardInterrupt:
                print("\n用户取消选择")
                return None
                
    def _create_strategy(self, strategy_config: Dict[str, Any]) -> Optional[StrategyBase]:
        """创建策略实例"""
        strategy_name = strategy_config.get('name')
        strategy_type = strategy_config.get('type')
        config = strategy_config.get('config', {})
        
        try:
            if strategy_type == 'spread_arbitrage':
                return SpreadArbitrageStrategy(
                    name=strategy_name,
                    event_engine=self.event_engine,
                    config=config
                )
            elif strategy_type == 'shfe_quant':
                return SHFEQuantStrategy(
                    name=strategy_name,
                    event_engine=self.event_engine,
                    config=config
                )
            else:
                print(f"未知的策略类型: {strategy_type}")
                return None
        except Exception as e:
            print(f"创建策略 {strategy_name} 失败: {e}")
            return None
            
    def load_strategy(self, strategy_name: str = None) -> bool:
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
        
    def run(self):
        """运行系统"""
        try:
            if self.start():
                print(f"系统运行中，当前策略: {self.current_strategy.name if self.current_strategy else '无'}")
                print("按 Ctrl+C 停止...")
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            print("\n收到停止信号")
        finally:
            self.stop()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ARBIG 交易系统')
    parser.add_argument('--config', '-c', default='config.yaml', help='配置文件路径')
    parser.add_argument('--strategy', '-s', help='指定要运行的策略名称')
    parser.add_argument('--list', '-l', action='store_true', help='列出所有可用策略')
    
    args = parser.parse_args()
    
    # 如果只是列出策略
    if args.list:
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            strategies = config.get('strategies', [])
            if strategies:
                print("可用策略列表:")
                for strategy in strategies:
                    print(f"  - {strategy.get('name')} ({strategy.get('type')})")
            else:
                print("配置文件中没有找到策略")
        except Exception as e:
            print(f"读取配置文件失败: {e}")
        return
    
    # 创建并运行主控制器
    controller = MainController(config_path=args.config, strategy_name=args.strategy)
    controller.run()

if __name__ == "__main__":
    main()
