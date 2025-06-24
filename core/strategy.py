"""
策略模块
负责生成交易信号和计算交易仓位
"""

from ..utils.logger import get_logger

logger = get_logger(__name__)

class ArbitrageStrategy:
    """
    套利策略类
    负责生成交易信号和计算交易仓位
    """
    
    def __init__(self, config):
        """
        初始化策略
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.spread_threshold = config.get('spread_threshold', 0.5)
        self.max_position = config.get('max_position', 1000)
        
    def generate_signal(self, spread):
        """
        生成交易信号
        
        Args:
            spread: 基差值 (SHFE价格 - MT5价格)
            
        Returns:
            str: 交易信号，可能的值：
                - 'BUY_MT5_SELL_SHFE': 买MT5(低价)、卖SHFE(高价) - 当SHFE价格 > MT5价格
                - 'BUY_SHFE_SELL_MT5': 买SHFE(低价)、卖MT5(高价) - 当SHFE价格 < MT5价格
                - None: 无信号
        """
        if spread is None:
            return None
            
        if spread > self.spread_threshold:
            # 修正：SHFE价格 > MT5价格，应该在低价MT5买入，高价SHFE卖出
            logger.info(f"生成信号: 买MT5、卖SHFE (基差: {spread:.2f}, SHFE价格高于MT5)")
            return 'BUY_MT5_SELL_SHFE'
        elif spread < -self.spread_threshold:
            # 修正：SHFE价格 < MT5价格，应该在低价SHFE买入，高价MT5卖出
            logger.info(f"生成信号: 买SHFE、卖MT5 (基差: {spread:.2f}, SHFE价格低于MT5)")
            return 'BUY_SHFE_SELL_MT5'
            
        return None
        
    def calculate_position(self, signal, current_position=0):
        """
        计算交易仓位
        
        Args:
            signal: 交易信号
            current_position: 当前持仓
            
        Returns:
            float: 建议交易数量（克）
        """
        if signal is None:
            return 0
            
        # 计算可用仓位
        available_position = self.max_position - abs(current_position)
        
        # 根据信号确定交易方向
        if signal == 'BUY_MT5_SELL_SHFE':
            position = min(available_position, 100)  # 示例：每次最多交易100克
        else:  # BUY_SHFE_SELL_MT5
            position = min(available_position, 100)
            
        logger.info(f"计算仓位: {position}克")
        return position
