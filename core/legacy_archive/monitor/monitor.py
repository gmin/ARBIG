"""
监控模块
负责系统监控和日志记录
"""

from ..utils.logger import get_logger

logger = get_logger(__name__)

class Monitor:
    """
    监控类
    负责系统监控和日志记录
    """
    
    def __init__(self):
        """
        初始化监控器
        """
        self.trade_log = []  # 交易日志
        self.position_log = []  # 持仓日志
        self.pnl_log = []  # 盈亏日志
        
    def log_trade(self, trade_info):
        """
        记录交易
        
        Args:
            trade_info: 交易信息字典
        """
        self.trade_log.append(trade_info)
        logger.info(f"记录交易: {trade_info}")
        
    def log_position(self, position_info):
        """
        记录持仓
        
        Args:
            position_info: 持仓信息字典
        """
        self.position_log.append(position_info)
        logger.info(f"记录持仓: {position_info}")
        
    def log_pnl(self, pnl_info):
        """
        记录盈亏
        
        Args:
            pnl_info: 盈亏信息字典
        """
        self.pnl_log.append(pnl_info)
        logger.info(f"记录盈亏: {pnl_info}")
        
    def get_trade_summary(self):
        """
        获取交易汇总
        
        Returns:
            dict: 交易汇总信息
        """
        return {
            'total_trades': len(self.trade_log),
            'total_positions': len(self.position_log),
            'total_pnl': sum(log.get('pnl', 0) for log in self.pnl_log)
        }
        
    def get_position_summary(self):
        """
        获取持仓汇总
        
        Returns:
            dict: 持仓汇总信息
        """
        if not self.position_log:
            return {}
            
        latest_position = self.position_log[-1]
        return {
            'hk_position': latest_position.get('hk', 0),
            'sh_position': latest_position.get('sh', 0)
        }
        
    def get_pnl_summary(self):
        """
        获取盈亏汇总
        
        Returns:
            dict: 盈亏汇总信息
        """
        if not self.pnl_log:
            return {}
            
        return {
            'total_pnl': sum(log.get('pnl', 0) for log in self.pnl_log),
            'daily_pnl': sum(log.get('pnl', 0) for log in self.pnl_log[-1:])
        }
