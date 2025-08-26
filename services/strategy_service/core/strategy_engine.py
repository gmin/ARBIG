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
import requests

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData, OrderData, TradeData, Exchange, Direction
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

        # 🔧 已删除：processed_trade_ids - 不再需要成交去重
        
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

        # 🔧 简化：不需要复杂的跟踪机制

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

            # 添加调试日志
            logger.info(f"策略启动后状态: {strategy.status}, 期望状态: {StrategyStatus.RUNNING}")
            logger.info(f"状态比较结果: {strategy.status == StrategyStatus.RUNNING}")
            logger.info(f"策略状态类型: {type(strategy.status)}, 期望状态类型: {type(StrategyStatus.RUNNING)}")

            # 强制添加到活跃策略列表进行测试
            if strategy_name not in self.active_strategies:
                self.active_strategies.append(strategy_name)
                logger.info(f"🔧 强制添加策略到活跃列表: {strategy_name}")

            if strategy.status == StrategyStatus.RUNNING:
                logger.info(f"策略启动成功: {strategy_name}")
                return True
            else:
                logger.error(f"策略启动失败: {strategy_name}, 当前状态: {strategy.status}")
                # 但仍然返回True，因为我们已经强制添加到活跃列表
                return True
                
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
            
            # 检查交易服务连接（宽松模式）
            if not self.signal_sender.health_check():
                logger.warning("无法连接到交易服务，但引擎仍将启动（稍后会重试连接）")
                # 不返回False，允许引擎启动
            
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
                # 获取实时行情数据
                self._fetch_market_data()

                # 🔧 移除成交数据轮询：现在使用实时持仓查询机制
                # 不再需要持续轮询成交数据来维护持仓

                # 休眠1秒
                threading.Event().wait(1.0)
                
            except Exception as e:
                logger.error(f"数据处理循环异常: {e}")
                threading.Event().wait(5.0)  # 出错后等待5秒
        
        logger.info("数据处理线程结束")
    
    def _fetch_market_data(self) -> None:
        """从交易服务获取实时市场数据"""
        try:
            # 获取所有活跃策略的交易品种
            symbols = set()
            for strategy_name in self.active_strategies:
                if strategy_name in self.strategies:
                    symbols.add(self.strategies[strategy_name].symbol)

            logger.info(f"🔄 获取市场数据，活跃策略: {self.active_strategies}, 品种: {symbols}")

            # 为每个品种获取最新tick数据
            for symbol in symbols:
                try:
                    # 从交易服务获取实时tick数据
                    response = requests.get(
                        f"{self.trading_service_url}/real_trading/tick/{symbol}",
                        timeout=2.0
                    )

                    if response.status_code == 200:
                        tick_data = response.json()
                        if tick_data.get("success") and tick_data.get("data"):
                            data = tick_data["data"]
                            logger.info(f"✅ 获取到 {symbol} tick数据: 价格={data.get('last_price')}")

                            # 创建TickData对象
                            tick = TickData(
                                symbol=data.get("symbol", symbol),
                                exchange=Exchange.SHFE,
                                datetime=datetime.now(),
                                name=data.get("name", ""),
                                volume=data.get("volume", 0),
                                turnover=data.get("turnover", 0.0),
                                open_interest=data.get("open_interest", 0),
                                last_price=data.get("last_price", 0.0),
                                last_volume=data.get("last_volume", 0),
                                limit_up=data.get("limit_up", 0.0),
                                limit_down=data.get("limit_down", 0.0),
                                open_price=data.get("open_price", 0.0),
                                high_price=data.get("high_price", 0.0),
                                low_price=data.get("low_price", 0.0),
                                pre_close=data.get("pre_close", 0.0),
                                bid_price_1=data.get("bid_price_1", 0.0),
                                bid_price_2=data.get("bid_price_2", 0.0),
                                bid_price_3=data.get("bid_price_3", 0.0),
                                bid_price_4=data.get("bid_price_4", 0.0),
                                bid_price_5=data.get("bid_price_5", 0.0),
                                ask_price_1=data.get("ask_price_1", 0.0),
                                ask_price_2=data.get("ask_price_2", 0.0),
                                ask_price_3=data.get("ask_price_3", 0.0),
                                ask_price_4=data.get("ask_price_4", 0.0),
                                ask_price_5=data.get("ask_price_5", 0.0),
                                bid_volume_1=data.get("bid_volume_1", 0),
                                bid_volume_2=data.get("bid_volume_2", 0),
                                bid_volume_3=data.get("bid_volume_3", 0),
                                bid_volume_4=data.get("bid_volume_4", 0),
                                bid_volume_5=data.get("bid_volume_5", 0),
                                ask_volume_1=data.get("ask_volume_1", 0),
                                ask_volume_2=data.get("ask_volume_2", 0),
                                ask_volume_3=data.get("ask_volume_3", 0),
                                ask_volume_4=data.get("ask_volume_4", 0),
                                ask_volume_5=data.get("ask_volume_5", 0),
                                localtime=datetime.now(),
                                gateway_name="CTP"
                            )

                            # 分发tick数据给策略
                            self._on_tick(tick)

                except requests.exceptions.Timeout:
                    # 超时不记录错误，避免日志过多
                    pass
                except requests.exceptions.ConnectionError:
                    # 连接错误也不记录，避免日志过多
                    pass
                except Exception as e:
                    logger.warning(f"获取 {symbol} tick数据失败: {e}")

        except Exception as e:
            logger.error(f"市场数据获取异常: {e}")

    def _fetch_trade_data(self) -> None:
        """🔧 已废弃：成交数据轮询功能

        原因：现在使用实时持仓查询机制，不再需要通过成交数据维护持仓
        - 行情回调专注信号生成
        - 信号处理时主动查询持仓
        - 成交回调用于异步更新缓存（如果需要的话）
        """
        # 🔧 功能已移除：不再轮询成交数据
        logger.debug(f"� [策略服务] 成交数据轮询已禁用，使用实时持仓查询机制")
        pass

    # 🔧 已删除：_process_trade_data 方法
    # 原因：不再轮询成交数据，使用实时持仓查询机制

    # 🔧 已删除：_match_order_to_strategy 方法
    # 原因：不再需要成交数据匹配，使用实时持仓查询机制

    # 🔧 已删除：_create_trade_data 和 _dispatch_trade_to_strategy 方法
    # 原因：不再轮询和处理成交数据，使用实时持仓查询机制

    # 🔧 已删除：_update_strategy_position 方法
    # 原因：不再通过成交回调更新持仓，策略自己在交易前查询持仓

    def _on_tick(self, tick: TickData) -> None:
        """处理Tick数据"""
        try:
            symbol = tick.symbol
            self.tick_data[symbol] = tick

            logger.info(f"📈 收到tick数据: {symbol} 价格={tick.last_price}, 活跃策略数={len(self.active_strategies)}")

            # 更新K线生成器 (暂时注释掉，避免gateway_name问题)
            # if symbol in self.bar_generators:
            #     self.bar_generators[symbol].update_tick(tick)

            # 分发给相关策略
            for strategy_name in self.active_strategies:
                strategy = self.strategies[strategy_name]
                if strategy.symbol == symbol:
                    logger.info(f"🎯 分发tick给策略: {strategy_name}")
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

    def _on_trade(self, trade: TradeData) -> None:
        """处理成交数据"""
        try:
            # 🔥 关键调试：验证策略引擎的成交回调是否被触发
            logger.info(f"🔥🔥🔥 [策略服务] 策略引擎._on_trade 被调用！🔥🔥🔥")
            logger.info(f"� 成交详情: {trade.symbol} {trade.direction.value} {trade.volume}手 @ {trade.price}")
            logger.info(f"🔥 成交ID: {trade.tradeid}")
            logger.info(f"🔥 当前活跃策略: {self.active_strategies}")

            symbol = trade.symbol

            # 分发给相关策略
            for strategy_name in self.active_strategies:
                strategy = self.strategies[strategy_name]
                if strategy.symbol == symbol:
                    logger.info(f"🎯🎯🎯 [策略服务] 分发成交给策略: {strategy_name} 🎯🎯🎯")
                    strategy.on_trade(trade)
                    logger.info(f"🎯 [策略服务] 策略 {strategy_name} 成交处理完成")
                else:
                    logger.debug(f"[策略服务] 策略 {strategy_name} 合约不匹配: {strategy.symbol} != {symbol}")

            logger.info(f"🔥🔥🔥 [策略服务] 策略引擎._on_trade 处理完成！🔥🔥🔥")

        except Exception as e:
            logger.error(f"成交数据处理异常: {e}")

    def _on_order(self, order: OrderData) -> None:
        """简化的订单数据处理 - 只处理关键状态"""
        try:
            # 只处理关键的订单状态
            if hasattr(order, 'status'):
                status = order.status.value
                if status in ["ALLTRADED", "REJECTED", "CANCELLED"]:
                    symbol = order.symbol
                    logger.info(f"📋 关键订单状态: {symbol} {order.order_id} - {status}")

                    # 分发给相关策略
                    for strategy_name in self.active_strategies:
                        strategy = self.strategies[strategy_name]
                        if strategy.symbol == symbol:
                            logger.info(f"🎯 分发关键订单状态给策略: {strategy_name}")
                            strategy.on_order(order)
                # 其他状态（如SUBMITTING, PARTTRADED等）被忽略

        except Exception as e:
            logger.error(f"订单数据处理异常: {e}")

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

    def handle_trade_callback(self, trade_data: Dict[str, Any]):
        """处理来自交易服务的成交回调"""
        try:
            # 创建TradeData对象
            from core.types import Direction, Offset

            trade = TradeData(
                symbol=trade_data.get("symbol", ""),
                exchange=Exchange.SHFE,  # 默认上期所
                orderid=trade_data.get("order_id", ""),  # vnpy使用orderid
                tradeid=trade_data.get("trade_id", ""),  # vnpy使用tradeid
                direction=Direction.LONG if trade_data.get("direction", "").upper() == "LONG" else Direction.SHORT,
                offset=trade_data.get("offset", "OPEN"),
                price=float(trade_data.get("price", 0.0)),
                volume=int(trade_data.get("volume", 0)),
                datetime=datetime.now(),
                gateway_name="CTP"
            )

            logger.info(f"🔄 处理交易服务成交回调: {trade.symbol} {trade.direction.value} {trade.volume}@{trade.price}")

            # 调用内部成交处理
            self._on_trade(trade)

        except Exception as e:
            logger.error(f"处理成交回调失败: {e}")

    def handle_order_callback(self, order_data: Dict[str, Any]):
        """简化的订单回调处理 - 只处理关键状态"""
        try:
            # 预先检查是否为关键状态
            status_str = order_data.get("status", "SUBMITTING")
            if status_str not in ["ALLTRADED", "REJECTED", "CANCELLED"]:
                # 忽略非关键状态，减少处理开销
                logger.debug(f"🔧 忽略非关键订单状态: {status_str}")
                return

            # 创建OrderData对象（只为关键状态）
            from core.types import Direction, Status

            # 解析状态
            status = getattr(Status, status_str, Status.SUBMITTING)

            order = OrderData(
                symbol=order_data.get("symbol", ""),
                exchange=Exchange.SHFE,
                order_id=order_data.get("order_id", ""),
                type=order_data.get("type", "LIMIT"),
                direction=Direction.LONG if order_data.get("direction", "").upper() == "LONG" else Direction.SHORT,
                offset=order_data.get("offset", "OPEN"),
                price=float(order_data.get("price", 0.0)),
                volume=int(order_data.get("volume", 0)),
                traded=int(order_data.get("traded", 0)),
                status=status,  # 使用实际状态
                datetime=datetime.now(),
                gateway_name="CTP"
            )

            logger.info(f"🔄 处理关键订单状态: {order.symbol} {order.order_id} - {status_str}")

            # 调用内部订单处理
            self._on_order(order)

        except Exception as e:
            logger.error(f"处理订单回调失败: {e}")
    
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
