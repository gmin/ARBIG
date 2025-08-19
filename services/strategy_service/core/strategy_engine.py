"""
策略执行引擎
负责策略的生命周期管理和执行调度
"""

import asyncio
import threading
from typing import Dict, Any, Optional, List, Type
from datetime import datetime, timedelta
import json
import sys
import os
import importlib
import importlib.util
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData, OrderData, TradeData
from utils.logger import get_logger
from .cta_template import ARBIGCtaTemplate, StrategyStatus
from .signal_sender import SignalSender
from .data_tools import BarGenerator, ArrayManager
from .performance import StrategyPerformance, TradeRecord

logger = get_logger(__name__)

class StrategyEngine:
    """
    策略执行引擎
    
    负责：
    1. 策略的加载、启动、停止
    2. 市场数据的分发
    3. 策略信号的处理
    4. 策略状态的监控
    """
    
    def __init__(self, trading_service_url: str = "http://localhost:8001"):
        """
        初始化策略引擎
        
        Args:
            trading_service_url: 交易服务URL
        """
        self.trading_service_url = trading_service_url
        self.signal_sender = SignalSender(trading_service_url)
        
        # 策略管理
        self.strategies: Dict[str, ARBIGCtaTemplate] = {}
        self.strategy_configs: Dict[str, Dict[str, Any]] = {}
        self.active_strategies: List[str] = []
        
        # 性能统计
        self.performance_stats: Dict[str, StrategyPerformance] = {}
        
        # 策略类注册表
        self.strategy_classes: Dict[str, Type[ARBIGCtaTemplate]] = {}
        self.strategy_templates: Dict[str, Dict[str, Any]] = {}
        
        # 加载所有可用的策略
        self._load_available_strategies()
        
        # 数据管理
        self.tick_data: Dict[str, TickData] = {}  # symbol -> latest tick
        self.bar_generators: Dict[str, BarGenerator] = {}  # symbol -> bar generator
        self.array_managers: Dict[str, ArrayManager] = {}  # symbol -> array manager
        
        # 运行状态
        self.running = False
        self.data_thread: Optional[threading.Thread] = None
        
        # 统计信息
        self.total_signals = 0
        self.successful_signals = 0
        self.failed_signals = 0
        
        logger.info("策略执行引擎初始化完成")
    
    def _load_available_strategies(self):
        """加载所有可用的策略类"""
        try:
            # 策略文件目录
            strategies_dir = Path(__file__).parent.parent / "strategies"
            
            if not strategies_dir.exists():
                logger.warning(f"策略目录不存在: {strategies_dir}")
                return
                
            # 遍历策略文件
            for strategy_file in strategies_dir.glob("*.py"):
                if strategy_file.name.startswith("__"):
                    continue
                    
                try:
                    self._load_strategy_module(strategy_file)
                except Exception as e:
                    logger.error(f"加载策略文件失败 {strategy_file.name}: {e}")
                    
            logger.info(f"共加载 {len(self.strategy_classes)} 个策略类")
            
        except Exception as e:
            logger.error(f"加载策略失败: {e}")
    
    def _load_strategy_module(self, strategy_file: Path):
        """加载单个策略模块"""
        module_name = strategy_file.stem

        try:
            # 确保策略目录在Python路径中
            strategies_dir = str(strategy_file.parent)
            if strategies_dir not in sys.path:
                sys.path.insert(0, strategies_dir)

            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, strategy_file)
            if spec is None or spec.loader is None:
                logger.error(f"无法创建模块规格: {strategy_file}")
                return

            module = importlib.util.module_from_spec(spec)

            # 在模块执行前，确保所有必要的模块都可用
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

        except Exception as e:
            logger.error(f"加载策略模块失败 {module_name}: {e}")
            return
        
        # 查找策略类和模板
        strategy_class = None
        strategy_template = None
        
        # 查找继承自ARBIGCtaTemplate的类
        logger.info(f"检查模块 {module_name} 中的类...")  # 临时改为info级别

        for attr_name in dir(module):
            if attr_name.startswith('_'):
                continue

            attr = getattr(module, attr_name)

            # 检查是否是类
            if isinstance(attr, type):
                logger.info(f"  找到类: {attr_name} -> {attr}")
                logger.info(f"  基类: {attr.__bases__}")

                # 检查是否是策略类
                try:
                    # 检查基类名称和模块路径，避免导入路径问题
                    base_class_names = [base.__name__ for base in attr.__bases__]
                    base_class_modules = [getattr(base, '__module__', '') for base in attr.__bases__]
                    logger.info(f"  基类名称: {base_class_names}")
                    logger.info(f"  基类模块: {base_class_modules}")

                    # 检查是否继承自ARBIGCtaTemplate（通过名称和模块路径）
                    is_strategy_class = False
                    for base_name, base_module in zip(base_class_names, base_class_modules):
                        if (base_name == 'ARBIGCtaTemplate' and
                            'cta_template' in base_module and
                            attr.__name__ != 'ARBIGCtaTemplate'):
                            is_strategy_class = True
                            break

                    if is_strategy_class:
                        strategy_class = attr
                        logger.info(f"  ✅ 找到策略类: {attr_name}")
                    else:
                        logger.info(f"  ❌ 不是策略类: {attr_name}")
                except Exception as e:
                    logger.info(f"  ❌ 类型检查失败: {attr_name} - {e}")

            # 检查是否是策略模板
            elif attr_name == "STRATEGY_TEMPLATE" and isinstance(attr, dict):
                strategy_template = attr
                logger.debug(f"  ✅ 找到策略模板: {attr_name}")
        
        # 注册策略类
        if strategy_class:
            class_name = strategy_class.__name__
            self.strategy_classes[class_name] = strategy_class
            
            if strategy_template:
                self.strategy_templates[class_name] = strategy_template
                
            logger.info(f"加载策略类: {class_name} from {module_name}")
        else:
            logger.warning(f"在 {module_name} 中未找到有效的策略类")
    
    def get_available_strategies(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用的策略类型"""
        result = {}
        
        for class_name, strategy_class in self.strategy_classes.items():
            template = self.strategy_templates.get(class_name, {})
            
            result[class_name] = {
                "class_name": class_name,
                "description": template.get("description", f"{class_name} 策略"),
                "file_name": template.get("file_name", "unknown.py"),
                "parameters": template.get("parameters", {}),
                "module": strategy_class.__module__
            }
            
        return result
    
    def register_strategy_by_type(
        self,
        strategy_type: str,
        strategy_name: str,
        symbol: str,
        setting: Dict[str, Any]
    ) -> bool:
        """
        根据策略类型注册策略
        
        Args:
            strategy_type: 策略类型名称
            strategy_name: 策略实例名称
            symbol: 交易合约
            setting: 策略参数
            
        Returns:
            是否注册成功
        """
        if strategy_type not in self.strategy_classes:
            logger.error(f"未找到策略类型: {strategy_type}")
            return False
            
        strategy_class = self.strategy_classes[strategy_type]
        return self.register_strategy(strategy_class, strategy_name, symbol, setting)
    
    def register_strategy(
        self, 
        strategy_class: Type[ARBIGCtaTemplate], 
        strategy_name: str, 
        symbol: str, 
        setting: Dict[str, Any]
    ) -> bool:
        """
        注册策略
        
        Args:
            strategy_class: 策略类
            strategy_name: 策略名称
            symbol: 交易合约
            setting: 策略参数
            
        Returns:
            是否注册成功
        """
        try:
            if strategy_name in self.strategies:
                logger.warning(f"策略 {strategy_name} 已存在")
                return False
            
            # 创建策略实例 (vnpy风格)
            strategy = strategy_class(
                strategy_name=strategy_name,
                symbol=symbol,
                setting=setting,
                signal_sender=self.signal_sender
            )
            
            # 注册策略
            self.strategies[strategy_name] = strategy
            self.strategy_configs[strategy_name] = {
                "class": strategy_class.__name__,
                "symbol": symbol,
                "setting": setting.copy()
            }
            
            # 初始化数据工具
            if symbol not in self.bar_generators:
                self.bar_generators[symbol] = BarGenerator(
                    on_bar_callback=lambda bar: self._on_bar(bar),
                    window=0  # 只生成1分钟K线
                )
            
            if symbol not in self.array_managers:
                self.array_managers[symbol] = ArrayManager(size=200)
            
            # 初始化性能统计
            self.performance_stats[strategy_name] = StrategyPerformance(strategy_name)
            
            logger.info(f"策略注册成功: {strategy_name} - {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"策略注册失败 {strategy_name}: {e}")
            return False
    
    def start_strategy(self, strategy_name: str) -> bool:
        """
        启动策略
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            是否启动成功
        """
        try:
            if strategy_name not in self.strategies:
                logger.error(f"策略 {strategy_name} 不存在")
                return False
            
            strategy = self.strategies[strategy_name]
            
            if strategy.status == StrategyStatus.RUNNING:
                logger.warning(f"策略 {strategy_name} 已在运行")
                return True
            
            # 启动策略
            strategy.start()
            
            if strategy.status == StrategyStatus.RUNNING:
                if strategy_name not in self.active_strategies:
                    self.active_strategies.append(strategy_name)
                logger.info(f"策略启动成功: {strategy_name}")
                return True
            else:
                logger.error(f"策略启动失败: {strategy_name}")
                return False
                
        except Exception as e:
            logger.error(f"策略启动异常 {strategy_name}: {e}")
            return False
    
    def stop_strategy(self, strategy_name: str) -> bool:
        """
        停止策略
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            是否停止成功
        """
        try:
            if strategy_name not in self.strategies:
                logger.error(f"策略 {strategy_name} 不存在")
                return False
            
            strategy = self.strategies[strategy_name]
            strategy.stop()
            
            if strategy_name in self.active_strategies:
                self.active_strategies.remove(strategy_name)
            
            logger.info(f"策略停止成功: {strategy_name}")
            return True
            
        except Exception as e:
            logger.error(f"策略停止异常 {strategy_name}: {e}")
            return False
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """
        移除策略
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            是否移除成功
        """
        try:
            if strategy_name not in self.strategies:
                logger.error(f"策略 {strategy_name} 不存在")
                return False
            
            # 先停止策略
            self.stop_strategy(strategy_name)
            
            # 移除策略
            del self.strategies[strategy_name]
            del self.strategy_configs[strategy_name]
            
            logger.info(f"策略移除成功: {strategy_name}")
            return True
            
        except Exception as e:
            logger.error(f"策略移除异常 {strategy_name}: {e}")
            return False
    
    def update_strategy_setting(self, strategy_name: str, setting: Dict[str, Any]) -> bool:
        """
        更新策略参数
        
        Args:
            strategy_name: 策略名称
            setting: 新参数
            
        Returns:
            是否更新成功
        """
        try:
            if strategy_name not in self.strategies:
                logger.error(f"策略 {strategy_name} 不存在")
                return False
            
            strategy = self.strategies[strategy_name]
            strategy.update_setting(setting)
            
            # 更新配置
            self.strategy_configs[strategy_name]["setting"].update(setting)
            
            logger.info(f"策略参数更新成功: {strategy_name}")
            return True
            
        except Exception as e:
            logger.error(f"策略参数更新异常 {strategy_name}: {e}")
            return False
    
    def start_engine(self) -> bool:
        """
        启动策略引擎
        
        Returns:
            是否启动成功
        """
        try:
            if self.running:
                logger.warning("策略引擎已在运行")
                return True
            
            # 检查交易服务连接
            if not self.signal_sender.health_check():
                logger.error("无法连接到交易服务，引擎启动失败")
                return False
            
            self.running = True
            
            # 启动数据处理线程
            self.data_thread = threading.Thread(target=self._data_processing_loop)
            self.data_thread.daemon = True
            self.data_thread.start()
            
            logger.info("策略执行引擎启动成功")
            return True
            
        except Exception as e:
            logger.error(f"策略引擎启动异常: {e}")
            return False
    
    def stop_engine(self) -> None:
        """停止策略引擎"""
        try:
            self.running = False
            
            # 停止所有策略
            for strategy_name in list(self.active_strategies):
                self.stop_strategy(strategy_name)
            
            # 等待数据线程结束
            if self.data_thread and self.data_thread.is_alive():
                self.data_thread.join(timeout=5.0)
            
            logger.info("策略执行引擎停止成功")
            
        except Exception as e:
            logger.error(f"策略引擎停止异常: {e}")
    
    def _data_processing_loop(self) -> None:
        """数据处理循环"""
        logger.info("数据处理线程启动")
        
        while self.running:
            try:
                # 模拟获取市场数据
                # 在实际实现中，这里应该从交易服务获取实时数据
                self._fetch_market_data()
                
                # 休眠1秒
                threading.Event().wait(1.0)
                
            except Exception as e:
                logger.error(f"数据处理循环异常: {e}")
                threading.Event().wait(5.0)  # 出错后等待5秒
        
        logger.info("数据处理线程结束")
    
    def _fetch_market_data(self) -> None:
        """获取市场数据（模拟实现）"""
        # 这里应该从交易服务获取实时Tick数据
        # 暂时跳过，等待实际数据源集成
        pass
    
    def _on_tick(self, tick: TickData) -> None:
        """处理Tick数据"""
        try:
            symbol = tick.symbol
            self.tick_data[symbol] = tick
            
            # 更新K线生成器
            if symbol in self.bar_generators:
                self.bar_generators[symbol].update_tick(tick)
            
            # 分发给相关策略
            for strategy_name in self.active_strategies:
                strategy = self.strategies[strategy_name]
                if strategy.symbol == symbol:
                    strategy.on_tick(tick)
                    
        except Exception as e:
            logger.error(f"Tick数据处理异常: {e}")
    
    def _on_bar(self, bar: BarData) -> None:
        """处理Bar数据"""
        try:
            symbol = bar.symbol
            
            # 更新数组管理器
            if symbol in self.array_managers:
                self.array_managers[symbol].update_bar(bar)
            
            # 分发给相关策略
            for strategy_name in self.active_strategies:
                strategy = self.strategies[strategy_name]
                if strategy.symbol == symbol:
                    strategy.on_bar(bar)
                    
        except Exception as e:
            logger.error(f"Bar数据处理异常: {e}")
    
    def get_strategy_status(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """
        获取策略状态
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            策略状态信息
        """
        if strategy_name not in self.strategies:
            return None
        
        strategy = self.strategies[strategy_name]
        return strategy.get_status_info()
    
    def get_all_strategies_status(self) -> Dict[str, Any]:
        """获取所有策略状态"""
        result = {}
        
        for strategy_name, strategy in self.strategies.items():
            result[strategy_name] = strategy.get_status_info()
        
        return result
    
    def get_strategy_performance(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """获取策略性能统计"""
        if strategy_name not in self.performance_stats:
            return None
        return self.performance_stats[strategy_name].get_summary()
    
    def get_all_strategies_performance(self) -> Dict[str, Any]:
        """获取所有策略性能统计"""
        result = {}
        for strategy_name, performance in self.performance_stats.items():
            result[strategy_name] = performance.get_summary()
        return result
    
    def update_strategy_trade(self, strategy_name: str, trade_data: Dict[str, Any]):
        """更新策略交易记录"""
        if strategy_name not in self.performance_stats:
            return
        
        # 创建交易记录
        trade_record = TradeRecord(
            timestamp=datetime.now(),
            symbol=trade_data.get("symbol", ""),
            direction=trade_data.get("direction", ""),
            volume=trade_data.get("volume", 0),
            price=trade_data.get("price", 0.0),
            pnl=trade_data.get("pnl", 0.0),
            commission=trade_data.get("commission", 0.0),
            order_id=trade_data.get("order_id", "")
        )
        
        # 添加到性能统计
        self.performance_stats[strategy_name].add_trade(trade_record)
        
        logger.info(f"策略 {strategy_name} 交易记录已更新: {trade_record.direction} {trade_record.volume}@{trade_record.price}")
    
    def update_strategy_position(self, strategy_name: str, position: int):
        """更新策略持仓"""
        if strategy_name not in self.performance_stats:
            return
        
        self.performance_stats[strategy_name].update_position(position)
        logger.debug(f"策略 {strategy_name} 持仓更新: {position}")
    
    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            "running": self.running,
            "total_strategies": len(self.strategies),
            "active_strategies": len(self.active_strategies),
            "active_strategy_names": self.active_strategies.copy(),
            "total_signals": self.total_signals,
            "successful_signals": self.successful_signals,
            "failed_signals": self.failed_signals,
            "success_rate": (self.successful_signals / max(self.total_signals, 1)) * 100,
            "trading_service_status": self.signal_sender.health_check()
        }
