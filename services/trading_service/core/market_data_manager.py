"""
交易服务中的行情数据管理器
负责行情数据的接收、处理和分发
"""

from typing import Dict, Optional, Any
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)

class MarketDataManager:
    """行情数据管理器"""
    
    def __init__(self, ctp_integration=None):
        """初始化行情数据管理器（轻量级HTTP API转换层）"""
        self.ctp_integration = ctp_integration

        logger.info("行情数据管理器初始化完成（轻量级API转换层）")
        
    def set_ctp_integration(self, ctp_integration):
        """设置CTP集成实例"""
        self.ctp_integration = ctp_integration
        logger.info("✅ CTP集成实例已设置")





    
    def get_latest_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取最新行情数据（直接从CTP获取）"""
        if not self.ctp_integration:
            logger.warning("CTP集成未设置")
            return None

        try:
            ctp_tick = self.ctp_integration.get_latest_tick(symbol)
            if ctp_tick:
                # 添加数据源标识
                ctp_tick['data_source'] = 'CTP_REAL'
                ctp_tick['server_time'] = datetime.now().isoformat()
                return ctp_tick
            else:
                logger.debug(f"CTP中未找到合约 {symbol} 的行情数据")
                return None
        except Exception as e:
            logger.error(f"从CTP获取行情失败: {e}")
            return None
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """获取最新价格"""
        tick_data = self.get_latest_tick(symbol)
        if tick_data:
            return float(tick_data.get('last_price', 0))
        return None
    


# 全局实例
market_data_manager = MarketDataManager()

def get_market_data_manager() -> MarketDataManager:
    """获取行情数据管理器实例"""
    return market_data_manager
