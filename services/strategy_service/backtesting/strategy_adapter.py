"""
策略适配器
将ARBIG策略适配到vnpy回测引擎
"""

import sys
import os
from typing import Dict, Any, Type

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

try:
    # 使用检测到的正确导入路径
    from vnpy_ctastrategy.template import CtaTemplate
    from vnpy.trader.object import TickData, BarData, OrderData, TradeData
    from vnpy.trader.constant import Direction, Offset, Status

    print("✅ vnpy策略模板导入成功")

except ImportError as e:
    print(f"⚠️ vnpy策略模板导入失败: {e}")
    CtaTemplate = None

from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from utils.logger import get_logger

logger = get_logger(__name__)


class StrategyAdapter:
    """策略适配器工厂"""
    
    @staticmethod
    def adapt_strategy(arbig_strategy_class: Type[ARBIGCtaTemplate]) -> Type[CtaTemplate]:
        """
        将ARBIG策略适配为vnpy策略
        
        Args:
            arbig_strategy_class: ARBIG策略类
            
        Returns:
            适配后的vnpy策略类
        """
        if CtaTemplate is None:
            raise ImportError("vnpy_ctastrategy未安装")
        
        class AdaptedStrategy(CtaTemplate):
            """适配后的策略类"""
            
            # 从原策略复制参数
            parameters = getattr(arbig_strategy_class, 'parameters', [])
            variables = getattr(arbig_strategy_class, 'variables', [])
            
            def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
                """初始化适配策略"""
                super().__init__(cta_engine, strategy_name, vt_symbol, setting)
                
                # 创建原始策略实例
                self.original_strategy = arbig_strategy_class(
                    strategy_name=strategy_name,
                    symbol=vt_symbol.split('.')[0],  # 去掉交易所后缀
                    setting=setting,
                    signal_sender=None  # 回测时不需要信号发送器
                )
                
                # 同步参数
                self._sync_parameters(setting)
                
                logger.info(f"策略适配完成: {arbig_strategy_class.__name__} -> {self.__class__.__name__}")
            
            def _sync_parameters(self, setting: Dict[str, Any]):
                """同步参数设置"""
                for key, value in setting.items():
                    if hasattr(self.original_strategy, key):
                        setattr(self.original_strategy, key, value)
                        setattr(self, key, value)
            
            def on_init(self):
                """策略初始化"""
                self.write_log("适配策略初始化")
                if hasattr(self.original_strategy, 'on_init'):
                    self.original_strategy.on_init()
            
            def on_start(self):
                """策略启动"""
                self.write_log("适配策略启动")
                if hasattr(self.original_strategy, 'on_start'):
                    self.original_strategy.on_start()
            
            def on_stop(self):
                """策略停止"""
                self.write_log("适配策略停止")
                if hasattr(self.original_strategy, 'on_stop'):
                    self.original_strategy.on_stop()
            
            def on_tick(self, tick: TickData):
                """处理Tick数据"""
                try:
                    # 转换为ARBIG格式
                    arbig_tick = self._convert_tick_to_arbig(tick)
                    
                    # 调用原策略的tick处理
                    if hasattr(self.original_strategy, 'on_tick_impl'):
                        self.original_strategy.on_tick_impl(arbig_tick)
                    elif hasattr(self.original_strategy, 'on_tick'):
                        self.original_strategy.on_tick(arbig_tick)
                    
                    # 同步持仓状态
                    self._sync_position()
                    
                except Exception as e:
                    self.write_log(f"Tick处理异常: {e}")
            
            def on_bar(self, bar: BarData):
                """处理Bar数据"""
                try:
                    # 转换为ARBIG格式
                    arbig_bar = self._convert_bar_to_arbig(bar)
                    
                    # 调用原策略的bar处理
                    if hasattr(self.original_strategy, 'on_bar_impl'):
                        self.original_strategy.on_bar_impl(arbig_bar)
                    elif hasattr(self.original_strategy, 'on_bar'):
                        self.original_strategy.on_bar(arbig_bar)
                    
                    # 同步持仓状态
                    self._sync_position()
                    
                except Exception as e:
                    self.write_log(f"Bar处理异常: {e}")
            
            def on_order(self, order: OrderData):
                """处理订单回报"""
                # 可以添加订单处理逻辑
                pass
            
            def on_trade(self, trade: TradeData):
                """处理成交回报"""
                # 可以添加成交处理逻辑
                pass
            
            def _convert_tick_to_arbig(self, vnpy_tick: TickData):
                """将vnpy的TickData转换为ARBIG格式"""
                # 这里需要根据ARBIG的TickData格式进行转换
                # 暂时返回vnpy格式，后续可以完善
                return vnpy_tick
            
            def _convert_bar_to_arbig(self, vnpy_bar: BarData):
                """将vnpy的BarData转换为ARBIG格式"""
                # 这里需要根据ARBIG的BarData格式进行转换
                # 暂时返回vnpy格式，后续可以完善
                return vnpy_bar
            
            def _sync_position(self):
                """同步持仓状态"""
                # 将原策略的交易信号转换为vnpy交易指令
                if hasattr(self.original_strategy, 'pos'):
                    target_pos = self.original_strategy.pos
                    current_pos = self.pos
                    
                    if target_pos != current_pos:
                        # 计算需要调整的仓位
                        diff = target_pos - current_pos
                        
                        if diff > 0:
                            # 需要买入
                            self.buy(self.original_strategy.entry_price or self.get_last_price(), abs(diff))
                        elif diff < 0:
                            # 需要卖出
                            self.sell(self.original_strategy.entry_price or self.get_last_price(), abs(diff))
            
            def get_last_price(self):
                """获取最新价格"""
                # 从tick数据获取最新价格
                if hasattr(self, 'last_tick') and self.last_tick:
                    return self.last_tick.last_price
                return 0
        
        # 设置适配后的类名
        AdaptedStrategy.__name__ = f"Adapted{arbig_strategy_class.__name__}"
        AdaptedStrategy.__qualname__ = f"Adapted{arbig_strategy_class.__name__}"
        
        return AdaptedStrategy


def create_vnpy_compatible_strategy(strategy_class: Type[ARBIGCtaTemplate], 
                                   strategy_name: str = None) -> Type[CtaTemplate]:
    """
    创建vnpy兼容的策略类
    
    Args:
        strategy_class: ARBIG策略类
        strategy_name: 策略名称
        
    Returns:
        vnpy兼容的策略类
    """
    try:
        adapted_class = StrategyAdapter.adapt_strategy(strategy_class)
        
        if strategy_name:
            adapted_class.__name__ = strategy_name
            adapted_class.__qualname__ = strategy_name
        
        logger.info(f"策略适配成功: {strategy_class.__name__}")
        return adapted_class
        
    except Exception as e:
        logger.error(f"策略适配失败: {e}")
        raise


# 预定义的策略适配
def get_adapted_strategies():
    """获取所有适配后的策略"""
    adapted_strategies = {}

    try:
        # 修复导入路径 - 使用相对导入
        import sys
        import os
        import glob
        import importlib.util

        # 确保能找到策略文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        strategies_dir = os.path.join(current_dir, '..', 'strategies')
        if strategies_dir not in sys.path:
            sys.path.insert(0, strategies_dir)

        # 策略文件映射 - 定义文件名到策略类名和显示名的映射
        strategy_mappings = {
            "LargeOrderFollowingStrategy.py": {
                "class_name": "LargeOrderFollowingStrategy",
                "display_name": "LargeOrderFollowing",
                "description": "大单跟踪策略"
            },
            "VWAPDeviationReversionStrategy.py": {
                "class_name": "VWAPDeviationReversionStrategy",
                "display_name": "VWAPDeviationReversion",
                "description": "VWAP偏离回归策略"
            },
            "DoubleMaStrategy.py": {
                "class_name": "DoubleMaStrategy",
                "display_name": "DoubleMa",
                "description": "双均线策略"
            },
            "TestStrategy.py": {
                "class_name": "TestStrategy",
                "display_name": "Test",
                "description": "测试策略"
            },
            "AdvancedSHFEStrategy.py": {
                "class_name": "AdvancedSHFEStrategy",
                "display_name": "AdvancedSHFE",
                "description": "高级SHFE策略"
            },
            "SimpleSHFEStrategy.py": {
                "class_name": "SimpleSHFEStrategy",
                "display_name": "SimpleSHFE",
                "description": "简单SHFE策略"
            },
            "SHFEQuantStrategy.py": {
                "class_name": "SHFEQuantStrategy",
                "display_name": "SHFEQuant",
                "description": "SHFE量化策略"
            }
        }

        # 自动加载所有策略
        for filename, mapping in strategy_mappings.items():
            try:
                module_name = filename[:-3]  # 去掉.py后缀
                class_name = mapping["class_name"]
                display_name = mapping["display_name"]
                description = mapping["description"]

                # 动态导入模块
                module = __import__(module_name)

                # 获取策略类
                if hasattr(module, class_name):
                    strategy_class = getattr(module, class_name)

                    # 适配策略
                    adapted_strategies[display_name] = create_vnpy_compatible_strategy(
                        strategy_class, f"Adapted{display_name}"
                    )
                    logger.info(f"✅ {description}适配成功")
                else:
                    logger.warning(f"模块 {module_name} 中未找到类 {class_name}")

            except ImportError as e:
                logger.warning(f"{mapping['description']}导入失败: {e}")
            except Exception as e:
                logger.error(f"{mapping['description']}适配失败: {e}")

        logger.info(f"成功适配 {len(adapted_strategies)} 个策略")

    except Exception as e:
        logger.error(f"策略适配过程出错: {e}")

    return adapted_strategies


if __name__ == "__main__":
    # 测试策略适配
    adapted_strategies = get_adapted_strategies()
    for name, strategy_class in adapted_strategies.items():
        print(f"✓ 适配策略: {name} -> {strategy_class.__name__}")
