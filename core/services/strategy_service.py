"""
策略管理服务
负责策略的启动、停止、监控和管理
"""

import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from core.event_engine import EventEngine
from core.constants import *
from utils.logger import get_logger

logger = get_logger(__name__)

class StrategyService:
    """策略管理服务"""
    
    def __init__(self, event_engine: EventEngine, config_manager):
        self.event_engine = event_engine
        self.config_manager = config_manager
        
        # 策略实例管理
        self.strategies: Dict[str, Any] = {}
        self.strategy_status: Dict[str, str] = {}
        self.strategy_stats: Dict[str, Dict] = {}
        
        # 服务状态
        self.running = False
        self._lock = threading.Lock()
        
        # 注册事件处理
        self._register_event_handlers()
        
    def _register_event_handlers(self):
        """注册事件处理函数"""
        self.event_engine.register(SIGNAL_EVENT, self._on_strategy_signal)
        
    def start(self) -> bool:
        """启动策略服务"""
        try:
            with self._lock:
                if self.running:
                    logger.warning("策略服务已在运行")
                    return True
                
                logger.info("启动策略管理服务...")
                
                # 加载策略配置
                self._load_strategy_configs()
                
                self.running = True
                logger.info("✓ 策略管理服务启动成功")
                return True
                
        except Exception as e:
            logger.error(f"策略服务启动失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止策略服务"""
        try:
            with self._lock:
                if not self.running:
                    return True
                
                logger.info("停止策略管理服务...")
                
                # 停止所有运行中的策略
                for strategy_name in list(self.strategies.keys()):
                    self.stop_strategy(strategy_name)
                
                self.running = False
                logger.info("✓ 策略管理服务已停止")
                return True
                
        except Exception as e:
            logger.error(f"策略服务停止失败: {e}")
            return False
    
    def _load_strategy_configs(self):
        """加载策略配置"""
        try:
            strategies_config = self.config_manager.get_config('strategies')
            if not strategies_config:
                logger.warning("未找到策略配置")
                return
            
            for strategy_name, config in strategies_config.items():
                if config.get('enabled', False):
                    self.strategy_status[strategy_name] = 'STOPPED'
                    self.strategy_stats[strategy_name] = {
                        'start_time': None,
                        'total_signals': 0,
                        'total_trades': 0,
                        'pnl': 0.0,
                        'last_signal_time': None
                    }
                    logger.info(f"加载策略配置: {strategy_name}")
                    
        except Exception as e:
            logger.error(f"加载策略配置失败: {e}")
    
    def start_strategy(self, strategy_name: str) -> bool:
        """启动指定策略"""
        try:
            with self._lock:
                if strategy_name in self.strategies:
                    logger.warning(f"策略 {strategy_name} 已在运行")
                    return True
                
                # 动态导入策略类
                strategy_instance = self._create_strategy_instance(strategy_name)
                if not strategy_instance:
                    return False
                
                # 启动策略
                strategy_instance.start()
                
                # 记录策略实例和状态
                self.strategies[strategy_name] = strategy_instance
                self.strategy_status[strategy_name] = 'RUNNING'
                self.strategy_stats[strategy_name]['start_time'] = datetime.now()
                
                logger.info(f"✓ 策略 {strategy_name} 启动成功")
                return True
                
        except Exception as e:
            logger.error(f"启动策略 {strategy_name} 失败: {e}")
            return False
    
    def stop_strategy(self, strategy_name: str) -> bool:
        """停止指定策略"""
        try:
            with self._lock:
                if strategy_name not in self.strategies:
                    logger.warning(f"策略 {strategy_name} 未在运行")
                    return True
                
                # 停止策略
                strategy_instance = self.strategies[strategy_name]
                strategy_instance.stop()
                
                # 清理策略实例和状态
                del self.strategies[strategy_name]
                self.strategy_status[strategy_name] = 'STOPPED'
                
                logger.info(f"✓ 策略 {strategy_name} 已停止")
                return True
                
        except Exception as e:
            logger.error(f"停止策略 {strategy_name} 失败: {e}")
            return False
    
    def _create_strategy_instance(self, strategy_name: str):
        """创建策略实例"""
        try:
            # 获取策略配置
            strategy_config = self.config_manager.get_config(f'strategies.{strategy_name}')
            if not strategy_config:
                logger.error(f"未找到策略 {strategy_name} 的配置")
                return None
            
            # 根据策略名称动态导入
            if strategy_name == 'shfe_quant':
                from strategies.shfe_quant import SHFEQuantStrategy
                return SHFEQuantStrategy(strategy_name, self.event_engine, strategy_config)
            else:
                logger.error(f"未知的策略类型: {strategy_name}")
                return None
                
        except Exception as e:
            logger.error(f"创建策略实例失败: {e}")
            return None
    
    def get_strategy_list(self) -> List[Dict]:
        """获取策略列表"""
        strategies = []
        for name, status in self.strategy_status.items():
            stats = self.strategy_stats.get(name, {})
            strategies.append({
                'name': name,
                'status': status,
                'pnl': stats.get('pnl', 0.0),
                'position': 0,  # TODO: 从实际持仓获取
                'description': f'{name} 策略',
                'start_time': stats.get('start_time'),
                'last_signal': stats.get('last_signal_time'),
                'total_trades': stats.get('total_trades', 0),
                'win_rate': 0.0  # TODO: 计算胜率
            })
        return strategies
    
    def get_strategy_status(self, strategy_name: str) -> Optional[Dict]:
        """获取指定策略状态"""
        if strategy_name not in self.strategy_status:
            return None
        
        stats = self.strategy_stats.get(strategy_name, {})
        return {
            'name': strategy_name,
            'status': self.strategy_status[strategy_name],
            'pnl': stats.get('pnl', 0.0),
            'position': 0,  # TODO: 从实际持仓获取
            'start_time': stats.get('start_time'),
            'total_signals': stats.get('total_signals', 0),
            'total_trades': stats.get('total_trades', 0)
        }
    
    def _on_strategy_signal(self, event):
        """处理策略信号事件"""
        try:
            strategy_name = event.data.get('strategy_name')
            signal_data = event.data.get('data')
            
            if strategy_name in self.strategy_stats:
                self.strategy_stats[strategy_name]['total_signals'] += 1
                self.strategy_stats[strategy_name]['last_signal_time'] = datetime.now()
            
            logger.info(f"收到策略信号: {strategy_name} - {signal_data}")
            
        except Exception as e:
            logger.error(f"处理策略信号失败: {e}")
    
    def is_running(self) -> bool:
        """检查服务是否运行中"""
        return self.running
