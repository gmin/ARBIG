"""
策略执行引擎
负责策略的生命周期管理和执行调度
"""

import asyncio
import threading
import time
import requests
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

        # 🔧 订阅品种管理 - 默认订阅主要品种
        self.subscribed_symbols: set = {"au2512"}  # 默认订阅黄金主力合约

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


            logger.info(f"🔧 策略引擎实例ID: {id(self)}, 订阅品种集合ID: {id(self.subscribed_symbols)}")

            # 初始化数据工具
            if symbol not in self.bar_generators:
                logger.info(f"[策略服务-引擎] 🔧 创建K线生成器: {symbol}")
                self.bar_generators[symbol] = BarGenerator(
                    on_bar_callback=self._on_bar,
                    window=0  # 只生成1分钟K线
                )
                logger.info(f"[策略服务-引擎] ✅ K线生成器创建完成: {symbol}")
            else:
                logger.info(f"[策略服务-引擎] 🔧 K线生成器已存在: {symbol}")
            
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
            logger.info(f"🔧 正在启动策略: {strategy_name}")
            strategy.start()

            logger.info(f"🔧 策略启动后状态: {strategy.status}")
            logger.info(f"🔧 状态值: {strategy.status.value}")
            logger.info(f"🔧 RUNNING状态值: {StrategyStatus.RUNNING.value}")
            logger.info(f"🔧 值比较结果: {strategy.status.value == StrategyStatus.RUNNING.value}")

            if strategy.status.value == StrategyStatus.RUNNING.value:
                try:
                    if strategy_name not in self.active_strategies:
                        self.active_strategies.append(strategy_name)
                        logger.info(f"🔧 策略添加到启动列表: {strategy_name}")
                    logger.info(f"🔧 当前启动策略列表: {self.active_strategies}")
                    logger.info(f"策略启动成功: {strategy_name}")
                    return True
                except Exception as e:
                    logger.error(f"🔧 添加策略到启动列表异常: {e}")
                    return False
            else:
                logger.error(f"🔧 策略启动失败: {strategy_name}, 状态: {strategy.status}")
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
        启动策略引擎 - 带重试机制

        Returns:
            是否启动成功
        """
        try:
            if self.running:
                logger.warning("策略引擎已在运行")
                return True

            # 🔧 等待交易服务就绪 - 重试机制
            logger.info("等待交易服务就绪...")
            max_retries = 30  # 最多等待30秒
            retry_interval = 1  # 每秒重试一次

            for attempt in range(max_retries):
                if self.signal_sender.health_check():
                    logger.info(f"交易服务连接成功 (尝试 {attempt + 1}/{max_retries})")
                    break
                else:
                    if attempt < max_retries - 1:
                        logger.info(f"等待交易服务... ({attempt + 1}/{max_retries})")
                        time.sleep(retry_interval)
                    else:
                        logger.error("等待交易服务超时，引擎启动失败")
                        return False

            self.running = True

            # 启动数据处理线程
            logger.info("🔧 创建数据处理线程...")
            self.data_thread = threading.Thread(target=self._data_processing_loop)
            self.data_thread.daemon = True

            logger.info("🔧 启动数据处理线程...")
            self.data_thread.start()

            # 验证线程是否启动
            if self.data_thread.is_alive():
                logger.info("🔧 数据处理线程启动成功")
            else:
                logger.error("🔧 数据处理线程启动失败")

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
        logger.info("🔧 数据处理线程启动")

        loop_count = 0
        while self.running:
            try:
                loop_count += 1
                if loop_count % 10 == 1:  # 每10秒输出一次状态
                    logger.info(f"🔧 数据处理循环运行中... (第{loop_count}次)")
                    logger.info(f"🔧 当前启动策略数量: {len(self.active_strategies)}")
                    logger.info(f"🔧 启动策略列表: {self.active_strategies}")

                # 🎯 在调度层控制交易时间 - 最优架构
                if self._is_trading_time():
                    # 只在交易时间获取市场数据
                    logger.info(f"🔧 交易时间内，调用_fetch_market_data, 启动策略: {len(self.active_strategies)}")
                    self._fetch_market_data()
                else:
                    # 非交易时间，跳过数据获取，节省资源
                    if loop_count % 60 == 1:  # 每分钟提醒一次
                        logger.debug(f"🔧 非交易时间，跳过数据获取")

                # 休眠1秒
                threading.Event().wait(1.0)

            except Exception as e:
                logger.error(f"数据处理循环异常: {e}")
                threading.Event().wait(5.0)  # 出错后等待5秒

        logger.info("🔧 数据处理线程结束")
    
    def _fetch_market_data(self) -> None:
        """获取实时行情数据"""
        try:
            # 🔧 检查是否有启动的策略
            if not self.active_strategies:
                logger.info("[策略服务-引擎] 🔧 没有启动的策略，跳过行情分发")
                return

            # 🔧 固定获取主要品种行情
            symbols_to_fetch = ["au2512"]  # 主要品种
            logger.info(f"[策略服务-引擎] 🔧 开始获取行情数据，品种: {symbols_to_fetch}, 启动策略: {len(self.active_strategies)}个")

            # 🔧 从交易服务获取实时tick数据
            for symbol in symbols_to_fetch:
                logger.debug(f"🔧 正在获取 {symbol} 的tick数据...")

                response = requests.get(
                    f"{self.trading_service_url}/real_trading/tick/{symbol}",
                    timeout=1.0
                )

                if response.status_code == 200:
                    tick_data = response.json()
                    logger.debug(f"🔧 获取到 {symbol} 响应: success={tick_data.get('success')}")

                    if tick_data.get("success") and tick_data.get("data"):
                        # 🔧 创建TickData对象并分发给策略
                        tick_info = tick_data["data"]
                        logger.info(f"[策略服务-引擎] 📈 收到tick数据: {symbol} 价格={tick_info.get('last_price')}")

                        tick = self._create_tick_data(tick_info)

                        # 存储最新tick数据
                        self.tick_data[symbol] = tick

                        # 🎯 发送tick数据给所有策略（用于实时风控）
                        for strategy_name in self.active_strategies:
                            strategy = self.strategies[strategy_name]
                            if strategy.symbol == symbol:
                                logger.debug(f"[策略服务-引擎] 🔧 发送tick给策略: {strategy_name}")
                                strategy.on_tick(tick)

                        # 🔧 启用1分钟K线生成 - 调度层已控制交易时间
                        if symbol in self.bar_generators:
                            logger.info(f"[策略服务-引擎] 🔧 更新K线生成器: {symbol}")
                            self.bar_generators[symbol].update_tick(tick)
                        else:
                            logger.warning(f"[策略服务-引擎] ⚠️ 没有找到K线生成器: {symbol}")
                            logger.info(f"[策略服务-引擎] 🔧 当前K线生成器: {list(self.bar_generators.keys())}")
                    else:
                        logger.warning(f"🔧 {symbol} tick数据无效: {tick_data}")

                else:
                    logger.warning(f"🔧 获取 {symbol} tick数据失败: {response.status_code}")

        except Exception as e:
            logger.error(f"🔧 行情数据获取异常: {e}")

    def _create_tick_data(self, tick_info: dict) -> TickData:
        """创建TickData对象"""
        try:
            from core.types import TickData
            from vnpy.trader.constant import Exchange

            # 🔧 创建TickData对象
            tick = TickData(
                symbol=tick_info.get("symbol", ""),
                exchange=Exchange.SHFE,
                datetime=datetime.fromisoformat(tick_info.get("datetime", datetime.now().isoformat())),
                name=tick_info.get("name", ""),
                volume=int(tick_info.get("volume", 0)),
                open_interest=int(tick_info.get("open_interest", 0)),
                last_price=float(tick_info.get("last_price", 0.0)),
                last_volume=int(tick_info.get("last_volume", 0)),
                limit_up=float(tick_info.get("limit_up", 0.0)),
                limit_down=float(tick_info.get("limit_down", 0.0)),
                open_price=float(tick_info.get("open_price", 0.0)),
                high_price=float(tick_info.get("high_price", 0.0)),
                low_price=float(tick_info.get("low_price", 0.0)),
                pre_close=float(tick_info.get("pre_close", 0.0)),
                bid_price_1=float(tick_info.get("bid_price_1", 0.0)),
                ask_price_1=float(tick_info.get("ask_price_1", 0.0)),
                bid_volume_1=int(tick_info.get("bid_volume_1", 0)),
                ask_volume_1=int(tick_info.get("ask_volume_1", 0)),
                gateway_name="CTP"
            )

            return tick

        except Exception as e:
            logger.error(f"创建TickData失败: {e}")
            raise


    
    def _on_bar(self, bar: BarData) -> None:
        """处理Bar数据"""
        try:
            symbol = bar.symbol
            logger.info(f"[策略服务-引擎] 📊 生成bar数据: {symbol} 时间={bar.datetime} 收盘价={bar.close_price}")

            # 更新数组管理器
            if symbol in self.array_managers:
                self.array_managers[symbol].update_bar(bar)

            # 分发给相关策略
            logger.info(f"[策略服务-引擎] 🔧 分发bar数据给 {len(self.active_strategies)} 个策略")
            for strategy_name in self.active_strategies:
                strategy = self.strategies[strategy_name]
                if strategy.symbol == symbol:
                    logger.debug(f"[策略服务-引擎] 🔧 发送bar给策略: {strategy_name}")
                    strategy.on_bar(bar)
                    
        except Exception as e:
            logger.error(f"Bar数据处理异常: {e}")

    def _is_trading_time(self) -> bool:
        """
        检查是否在交易时间

        Returns:
            bool: True表示在交易时间内
        """
        from datetime import datetime, time

        now = datetime.now()
        current_time = now.time()

        # 日盘交易时间: 9:00-10:15, 10:30-11:30, 13:30-15:00
        day_session_1a = time(9, 0) <= current_time <= time(10, 15)
        day_session_1b = time(10, 30) <= current_time <= time(11, 30)
        day_session_2 = time(13, 30) <= current_time <= time(15, 0)

        # 夜盘交易时间: 21:00-02:30 (跨日)
        night_session = current_time >= time(21, 0) or current_time <= time(2, 30)

        is_trading = day_session_1a or day_session_1b or day_session_2 or night_session

        if not is_trading:
            logger.debug(f"[策略服务-引擎] ⏰ 非交易时间: {current_time.strftime('%H:%M:%S')}")

        return is_trading
    
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
